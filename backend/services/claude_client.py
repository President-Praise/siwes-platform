import contextvars
import json
import os
import re
import time
from pathlib import Path
from typing import Iterable

from anthropic import Anthropic, APIError, APIStatusError
from dotenv import load_dotenv
from tenacity import (
    RetryCallState,
    Retrying,
    retry,
    retry_if_exception,
    retry_if_exception_type,
    stop_after_attempt,
)

load_dotenv()

_client: Anthropic | None = None

# Optional per-call context for tying retry telemetry back to a specific
# order. generation.py sets this around each report run; claude_client reads
# it inside the retry hook so retry events show up in that order's logs.
# Falls back to stdout if unset.
current_order_id: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "current_order_id", default=None
)

_RETRY_STATUS_CODES = {429, 500, 502, 503}
_MAX_ATTEMPTS = 4
_MIN_WAIT = 2.0
_MAX_WAIT = 60.0
_EXP_MULTIPLIER = 2.0


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set in environment")
        _client = Anthropic(api_key=api_key)
    return _client


def _model() -> str:
    return os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")


class _Retryable(Exception):
    """Marker exception: a Claude response we should retry. Carries the
    originating status code and Retry-After header (if any) so the wait
    strategy can honor server-suggested backoff."""

    def __init__(
        self,
        status: int | None,
        retry_after: int | None = None,
        original: Exception | None = None,
    ):
        self.status = status
        self.retry_after = retry_after
        self.original = original
        super().__init__(f"retryable status={status} retry_after={retry_after}")


def _parse_retry_after(exc: APIStatusError) -> int | None:
    """Extract a positive integer seconds value from the Retry-After header,
    if the SDK exposed the response on this exception."""
    try:
        ra = exc.response.headers.get("retry-after")
        if not ra:
            return None
        n = int(ra)
        return n if n > 0 else None
    except (AttributeError, ValueError, TypeError):
        return None


def _wait(retry_state: RetryCallState) -> float:
    """Honor Retry-After when present; otherwise exponential 2 → 60s."""
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    if isinstance(exc, _Retryable) and exc.retry_after is not None:
        return min(_MAX_WAIT, max(0.0, float(exc.retry_after)))
    attempt = retry_state.attempt_number  # 1-indexed
    return min(_MAX_WAIT, _MIN_WAIT * (_EXP_MULTIPLIER ** (attempt - 1)))


def _log_retry(retry_state: RetryCallState) -> None:
    """Mirror each retry to stdout and (if a caller set current_order_id) to
    that order's generation_logs row, so rate-limiting shows up per-order."""
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    next_sleep = 0.0
    if retry_state.next_action is not None:
        next_sleep = float(getattr(retry_state.next_action, "sleep", 0.0) or 0.0)
    if isinstance(exc, _Retryable):
        desc = f"http_{exc.status}" if exc.status is not None else "connection_error"
    elif isinstance(exc, json.JSONDecodeError):
        desc = "json_parse_error"
    else:
        desc = type(exc).__name__ if exc else "unknown"
    msg = f"claude_retry {desc} wait={next_sleep:.1f}s attempt={retry_state.attempt_number}"
    print(f"[claude] {msg}")
    oid = current_order_id.get()
    if oid is not None:
        try:
            from backend.api import generation_logs

            generation_logs.log(oid, "warning", msg)
        except Exception:
            pass


@retry(
    retry=retry_if_exception(lambda e: isinstance(e, _Retryable)),
    wait=_wait,
    stop=stop_after_attempt(_MAX_ATTEMPTS),
    before_sleep=_log_retry,
    reraise=True,
)
def _http_call_claude(system: str, user: str, max_tokens: int, temperature: float) -> str:
    client = _get_client()
    try:
        resp = client.messages.create(
            model=_model(),
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
    except APIStatusError as e:
        if e.status_code in _RETRY_STATUS_CODES:
            raise _Retryable(e.status_code, _parse_retry_after(e), original=e) from e
        raise
    except APIError as e:
        # Connection-level error with no status — transient, retryable.
        raise _Retryable(None, None, original=e) from e
    parts: Iterable = resp.content
    text = "".join(p.text for p in parts if getattr(p, "type", None) == "text").strip()
    if getattr(resp, "stop_reason", None) == "max_tokens":
        raise RuntimeError(
            f"Claude response truncated (stop_reason=max_tokens) at max_tokens={max_tokens}. "
            "Bump the budget for this call or reduce the requested content."
        )
    return text


def call_claude(
    system: str,
    user: str,
    *,
    max_tokens: int = 8000,
    temperature: float = 0.4,
    max_retries: int = 3,  # kept for signature compat; tenacity policy is fixed
) -> str:
    try:
        return _http_call_claude(system, user, max_tokens, temperature)
    except _Retryable as exc:
        orig = exc.original or exc
        label = f"HTTP {exc.status}" if exc.status is not None else "connection error"
        raise RuntimeError(
            f"Claude unavailable after {_MAX_ATTEMPTS} attempts: {label}"
        ) from orig


def _extract_json(text: str) -> str:
    """Best-effort: strip code fences, locate the outermost {...} or [...]."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```\s*$", "", text)
    first_obj = text.find("{")
    first_arr = text.find("[")
    candidates = [i for i in (first_obj, first_arr) if i != -1]
    if not candidates:
        return text
    start = min(candidates)
    last_obj = text.rfind("}")
    last_arr = text.rfind("]")
    end = max(last_obj, last_arr)
    if end <= start:
        return text
    return text[start:end + 1]


def _save_failed_response(raw: str, err: Exception) -> Path:
    debug_dir = Path("/tmp")
    debug_dir.mkdir(parents=True, exist_ok=True)
    path = debug_dir / f"claude_json_debug_{int(time.time() * 1000)}.txt"
    try:
        path.write_text(f"# JSONDecodeError: {err}\n# raw response below\n\n{raw}", encoding="utf-8")
    except Exception:
        pass
    return path


def call_claude_json(system: str, user: str, *, max_tokens: int = 4000) -> dict | list:
    strict_system = (
        system + "\nReturn ONLY valid JSON. No prose, no markdown fences. "
        "Escape all double quotes inside string values as \\\". "
        "Do not include line breaks inside string values — use spaces instead."
    )

    # Outer retry covers JSON parse failures only — HTTP transients are
    # already absorbed by call_claude's inner retry. Each iteration re-asks
    # Claude for the JSON, so flaky model output gets another shot.
    last_raw = ""
    try:
        for attempt in Retrying(
            retry=retry_if_exception_type(json.JSONDecodeError),
            wait=_wait,
            stop=stop_after_attempt(_MAX_ATTEMPTS),
            before_sleep=_log_retry,
            reraise=True,
        ):
            with attempt:
                last_raw = call_claude(
                    strict_system, user, max_tokens=max_tokens, temperature=0.2
                )
                return json.loads(_extract_json(last_raw))
    except json.JSONDecodeError as exc:
        debug_path = _save_failed_response(last_raw, exc) if last_raw else None
        raise RuntimeError(
            f"Claude JSON parse failed after {_MAX_ATTEMPTS} attempts: {exc} "
            f"(saved raw response to {debug_path})"
        ) from exc

    # Unreachable: Retrying with reraise=True either returns from inside or
    # propagates the last exception.
    raise RuntimeError("call_claude_json: retry loop exited without result")
