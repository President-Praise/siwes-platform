"""Convert FastAPI form data + uploaded files into the payload dict
consumed by report_generator / ppt_generator (same shape as sample_student.json).

Conventions for multi-row textareas:
- skills_acquired, recommendations: one item per line, joined with '; ' into a string.
- tools_used: one item per line → list[str].
- weekly_activities: "week_num | summary" per line → list[{week, summary}].
- challenges: "problem | solution" per line → list[{problem, solution}].
- problems_solved: "title | narrative" per line → list[{title, narrative}].
- references: "type | authors | year | title | publisher | edition | url" → list[dict].
- images: dynamic list — parallel form arrays image_file[], image_chapter[],
  image_description[]. Sequence auto-assigned per chapter in submission order.
"""
import io
import re
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError

MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB
MAX_DIMENSION = 1600  # px on the longer edge — keeps .docx under control
_ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "GIF"}
_EXT_FOR_FORMAT = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp", "GIF": ".gif"}


def _sanitize_filename(name: str) -> str:
    # Strip any path components a browser/client might have included before
    # the regex cleans the rest. Result is never empty.
    base = Path(name or "").name
    cleaned = re.sub(r"[^a-zA-Z0-9._-]", "_", base)
    return cleaned or "file"


def _split_pipe(line: str) -> list[str]:
    return [seg.strip() for seg in line.split("|")]


def _parse_lines(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [ln.strip() for ln in raw.splitlines() if ln.strip()]


def _parse_tools(raw: str | None) -> list[str]:
    return _parse_lines(raw)


def _parse_weekly(raw: str | None) -> list[dict]:
    out = []
    for ln in _parse_lines(raw):
        parts = _split_pipe(ln)
        if len(parts) < 2:
            continue
        try:
            week = int(parts[0])
        except ValueError:
            continue
        out.append({"week": week, "summary": parts[1]})
    return out


def _parse_pairs(raw: str | None, keys: tuple[str, str]) -> list[dict]:
    out = []
    for ln in _parse_lines(raw):
        parts = _split_pipe(ln)
        if len(parts) < 2:
            continue
        out.append({keys[0]: parts[0], keys[1]: parts[1]})
    return out


def _parse_references(raw: str | None) -> list[dict]:
    out = []
    for ln in _parse_lines(raw):
        parts = _split_pipe(ln) + [""] * 7
        ref: dict[str, Any] = {
            "type": parts[0] or "Book",
            "authors": parts[1],
            "title": parts[3],
            "publisher": parts[4],
            "edition": parts[5],
            "url": parts[6],
        }
        try:
            ref["year"] = int(parts[2]) if parts[2] else ""
        except ValueError:
            ref["year"] = parts[2]
        out.append(ref)
    return out


def _join_lines_semicolon(raw: str | None) -> str:
    items = _parse_lines(raw)
    return "; ".join(items)


def save_upload(upload, dest_dir: Path, filename: str) -> str | None:
    """Save an UploadFile to dest_dir/filename. Returns the relative path
    from project_root (e.g. 'backend/uploads/7/img_1.jpg'), or None if no file.

    Validates by content (not just extension): only JPEG/PNG/WEBP/GIF, max 8 MB,
    and proportionally downscales anything over 1600px on the long edge so the
    .docx doesn't balloon. Raises HTTPException(400) on bad input — silently
    skipping would let students think their picture was uploaded when it wasn't."""
    if upload is None or not getattr(upload, "filename", ""):
        return None
    raw = upload.file.read()
    if not raw:
        return None

    display_name = _sanitize_filename(upload.filename)

    if len(raw) > MAX_UPLOAD_BYTES:
        mb = len(raw) / (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=f"'{display_name}' is too large ({mb:.1f} MB). Please upload an image under 8 MB.",
        )

    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(
            status_code=400,
            detail=f"'{display_name}' is not a valid image. Please upload a JPEG, PNG, WEBP, or GIF file.",
        )

    fmt = (img.format or "").upper()
    if fmt not in _ALLOWED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"'{display_name}' has an unsupported image type ({fmt or 'unknown'}). Please upload a JPEG, PNG, WEBP, or GIF.",
        )

    dest_dir.mkdir(parents=True, exist_ok=True)
    out_path = dest_dir / f"{filename}{_EXT_FOR_FORMAT[fmt]}"

    if max(img.size) > MAX_DIMENSION:
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION))
        save_kwargs: dict[str, Any] = {}
        if fmt == "JPEG":
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            save_kwargs = {"quality": 85, "optimize": True}
        img.save(out_path, format=fmt, **save_kwargs)
    else:
        # Small enough — write the original bytes to preserve exact fidelity
        # (and animation, in the case of GIF/WEBP).
        with open(out_path, "wb") as f:
            f.write(raw)

    project_root = dest_dir.parents[2]
    return str(out_path.relative_to(project_root))


def build_payload(
    form: dict,
    files: dict,
    *,
    order_id: int,
    project_root: Path,
    image_uploads: list | None = None,
    image_chapters: list[str] | None = None,
    image_descriptions: list[str] | None = None,
) -> dict:
    uploads_dir = project_root / "backend" / "uploads" / str(order_id)

    company_logo_path = save_upload(files.get("company_logo"), uploads_dir, "company_logo")

    # Sequence is assigned per-chapter in the order the student submitted them.
    images: list[dict] = []
    seq_by_chapter: dict[int, int] = {}
    uploads = image_uploads or []
    chapters = image_chapters or []
    descriptions = image_descriptions or []
    for idx, upload in enumerate(uploads):
        rel_path = save_upload(upload, uploads_dir, f"image_{idx + 1}")
        if not rel_path:
            continue
        try:
            chapter = int((chapters[idx] if idx < len(chapters) else "2") or 2)
        except ValueError:
            chapter = 2
        seq_by_chapter[chapter] = seq_by_chapter.get(chapter, 0) + 1
        images.append({
            "url_or_path": rel_path,
            "chapter": chapter,
            "sequence": seq_by_chapter[chapter],
            "description": (descriptions[idx] if idx < len(descriptions) else "").strip(),
        })

    return {
        "student": {
            "name": form.get("student_name", "").strip(),
            "name_for_cover": form.get("student_name_for_cover", "").strip() or None,
            "student_id": form.get("student_id", "").strip(),
            "matric_no": form.get("student_matric_no", "").strip(),
            "department": form.get("student_department", "").strip(),
            "college": form.get("student_college", "").strip(),
            "degree": form.get("student_degree", "").strip(),
            "degree_short": form.get("student_degree_short", "").strip(),
            "email": form.get("student_email", "").strip(),
        },
        "internship": {
            "company_name": form.get("company_name", "").strip(),
            "company_address": form.get("company_address", "").strip(),
            "company_logo_url": company_logo_path,
            "department_at_company": form.get("department_at_company", "").strip(),
            "industry_supervisor_name": form.get("industry_supervisor_name", "").strip(),
            "academic_supervisor_name": form.get("academic_supervisor_name", "").strip(),
            "start_date": form.get("start_date", "").strip(),
            "end_date": form.get("end_date", "").strip(),
            "duration": form.get("duration", "").strip(),
        },
        "content": {
            "company_history": form.get("company_history", "").strip(),
            "tools_used": _parse_tools(form.get("tools_used")),
            "weekly_activities": _parse_weekly(form.get("weekly_activities")),
            "challenges": _parse_pairs(form.get("challenges"), ("problem", "solution")),
            "images": images,
            "problems_solved": _parse_pairs(form.get("problems_solved"), ("title", "narrative")),
            "skills_acquired": _join_lines_semicolon(form.get("skills_acquired")),
            "recommendations": (form.get("recommendations") or "").strip(),
            "references": _parse_references(form.get("references")),
        },
        "submission": {
            "siwes_officer_name": form.get("siwes_officer_name", "").strip(),
            "hod_name": form.get("hod_name", "").strip(),
            "submission_date": form.get("submission_date", "").strip(),
        },
        "order": {
            "package": form.get("package", "basic"),
            "amount": int(form.get("amount", "0") or 0),
            "express": form.get("express") in ("on", "true", "1", "yes"),
        },
    }
