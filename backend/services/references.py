def _sort_key(ref: dict) -> str:
    authors = ref.get("authors", "") or ""
    return authors.lower().lstrip(" ,.")


def format_apa(ref: dict) -> str:
    t = (ref.get("type") or "").lower()
    authors = (ref.get("authors") or "").strip().rstrip(".")
    year = ref.get("year", "")
    title = (ref.get("title") or "").strip().rstrip(".")
    publisher = (ref.get("publisher") or "").strip().rstrip(".")
    edition = (ref.get("edition") or "").strip().rstrip(".")
    url = (ref.get("url") or "").strip()
    journal = (ref.get("journal") or "").strip()
    volume = ref.get("volume", "")
    issue = ref.get("issue", "")
    pages = ref.get("pages", "")

    if t == "book":
        parts = [f"{authors} ({year}).", f"{title}."]
        if edition:
            parts.append(f"{edition}.")
        if publisher:
            parts.append(f"{publisher}.")
        return " ".join(parts)

    if t == "website":
        out = f"{authors} ({year}). {title}."
        if url:
            out += f" Retrieved from {url}"
        return out

    if t == "journal":
        loc = ""
        if journal:
            loc = f" {journal}"
            if volume:
                loc += f", {volume}"
                if issue:
                    loc += f"({issue})"
            if pages:
                loc += f", {pages}"
            loc += "."
        return f"{authors} ({year}). {title}.{loc}"

    if t == "report":
        out = f"{authors} ({year}). {title}."
        if publisher:
            out += f" {publisher}."
        return out

    parts = [f"{authors} ({year}).", f"{title}."]
    if publisher:
        parts.append(f"{publisher}.")
    if url:
        parts.append(f"Retrieved from {url}")
    return " ".join(parts)


def render_references(refs: list[dict]) -> list[str]:
    sorted_refs = sorted(refs, key=_sort_key)
    return [format_apa(r) for r in sorted_refs]
