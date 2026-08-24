"""SIWES PPTX generator — school-config-aware.

Accepts a school_config dict to drive the logo on title and thank-you slides.
Falls back to no logo if missing.
"""

import os
from pathlib import Path

from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

from . import stub_content
from .pptx_helpers import (
    BODY_HEIGHT, BODY_LEFT, BODY_TOP, BODY_WIDTH, BODY_TEXT, CAPTION_GREY,
    GOLD, LIGHT_GREY, NAVY, SLIDE_H, SLIDE_W, WHITE,
    add_accent_line, add_blank_slide, add_bullets, add_content_chrome, add_image,
    add_text, new_presentation, paint_full_navy, set_run,
)
from .references import render_references


def _resolve_path(p, project_root):
    if not p:
        return None
    return Path(p) if os.path.isabs(p) else project_root / p


def _resolve_school_logo(school_config: dict | None, project_root: Path) -> Path | None:
    if not school_config:
        return None
    logo = school_config.get("logo_path")
    return _resolve_path(logo, project_root) if logo else None


# ---- title and thank-you slides (full navy, no chrome) ----

def _title_slide(prs, payload, school_config, project_root):
    slide = add_blank_slide(prs)
    paint_full_navy(slide)
    student = payload["student"]
    intern = payload["internship"]

    school_logo = _resolve_school_logo(school_config, project_root)
    if school_logo and school_logo.exists():
        add_image(slide, school_logo, left=Inches(5.67), top=Inches(0.5), width=Inches(2.0))

    add_text(slide, "SIWES TECHNICAL REPORT",
             left=Inches(0.5), top=Inches(2.85), width=Inches(12.33), height=Inches(0.8),
             size=36, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    add_text(slide, "UNDERTAKEN AT",
             left=Inches(0.5), top=Inches(3.75), width=Inches(12.33), height=Inches(0.45),
             size=16, color=WHITE, align=PP_ALIGN.CENTER)
    add_text(slide, intern["company_name"].upper(),
             left=Inches(0.5), top=Inches(4.2), width=Inches(12.33), height=Inches(0.7),
             size=26, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

    add_accent_line(slide, left=Inches(5.67), top=Inches(5.05), width=Inches(2.0),
                    height=Inches(0.04), color=GOLD)

    name = student.get("name_for_cover") or student["name"].upper()
    add_text(slide, name,
             left=Inches(0.5), top=Inches(5.25), width=Inches(12.33), height=Inches(0.5),
             size=20, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    add_text(slide, f"({student['matric_no']})",
             left=Inches(0.5), top=Inches(5.75), width=Inches(12.33), height=Inches(0.4),
             size=15, color=WHITE, align=PP_ALIGN.CENTER)

    add_text(slide, intern["duration"].upper(),
             left=Inches(0.5), top=Inches(6.7), width=Inches(12.33), height=Inches(0.45),
             size=16, bold=True, color=GOLD, align=PP_ALIGN.CENTER)


def _thank_you_slide(prs, payload, school_config, project_root):
    slide = add_blank_slide(prs)
    paint_full_navy(slide)
    student = payload["student"]

    add_text(slide, "THANK YOU",
             left=Inches(0.5), top=Inches(2.4), width=Inches(12.33), height=Inches(1.4),
             size=72, bold=True, color=GOLD, align=PP_ALIGN.CENTER)
    add_accent_line(slide, left=Inches(5.67), top=Inches(4.0), width=Inches(2.0),
                    height=Inches(0.04), color=GOLD)
    add_text(slide, student.get("name", ""),
             left=Inches(0.5), top=Inches(4.3), width=Inches(12.33), height=Inches(0.5),
             size=18, color=WHITE, align=PP_ALIGN.CENTER)
    contact = student.get("email", "")
    if contact:
        add_text(slide, contact,
                 left=Inches(0.5), top=Inches(4.9), width=Inches(12.33), height=Inches(0.45),
                 size=14, italic=True, color=WHITE, align=PP_ALIGN.CENTER)

    school_logo = _resolve_school_logo(school_config, project_root)
    if school_logo and school_logo.exists():
        add_image(slide, school_logo, left=Inches(5.83), top=Inches(5.8), width=Inches(1.7))


def _outline_slide(prs, chrome):
    slide = add_blank_slide(prs)
    add_content_chrome(slide, title="Outline", **chrome)
    items = [
        "Introduction to SIWES",
        "Company Profile",
        "Supervision",
        "Tools and Equipment Used",
        "Workdone Summary",
        "Key Activities and Themes",
        "Challenges and Solutions",
        "Skills Acquired",
        "Recommendations",
        "References",
    ]
    add_bullets(slide, items, left=BODY_LEFT, top=BODY_TOP,
                width=BODY_WIDTH, height=BODY_HEIGHT, size=22)


def _intro_slide(prs, ch1, chrome):
    slide = add_blank_slide(prs)
    add_content_chrome(slide, title="Introduction to SIWES", **chrome)
    add_text(slide, ch1.get("aim_of_siwes", ""),
             left=BODY_LEFT, top=BODY_TOP, width=BODY_WIDTH, height=Inches(1.7),
             size=15)
    add_text(slide, "Objectives",
             left=BODY_LEFT, top=Inches(3.05), width=BODY_WIDTH, height=Inches(0.45),
             size=20, bold=True, color=NAVY)
    objectives = ch1.get("objectives_of_siwes", [])[:5]
    add_bullets(slide, objectives, left=BODY_LEFT, top=Inches(3.55),
                width=BODY_WIDTH, height=Inches(3.2), size=15)


def _company_profile_slide(prs, payload, ch1, project_root, chrome):
    slide = add_blank_slide(prs)
    intern = payload["internship"]
    add_content_chrome(slide, title=f"Company Profile — {intern['company_name']}", **chrome)

    has_logo = False
    company_logo = intern.get("company_logo_url")
    if company_logo:
        full = _resolve_path(company_logo, project_root)
        if full:
            has_logo = add_image(slide, full, left=Inches(9.4), top=Inches(1.5),
                                 width=Inches(3.2)) is not None

    body_w = Inches(8.4) if has_logo else BODY_WIDTH
    add_text(slide, ch1.get("company_profile", ""),
             left=BODY_LEFT, top=BODY_TOP, width=body_w, height=Inches(3.7),
             size=14)
    add_text(slide, f"Address: {intern.get('company_address', '')}",
             left=BODY_LEFT, top=Inches(5.1), width=BODY_WIDTH, height=Inches(0.45),
             size=13, italic=True, color=CAPTION_GREY)
    add_text(slide, f"Department of attachment: {intern.get('department_at_company', '')}",
             left=BODY_LEFT, top=Inches(5.55), width=BODY_WIDTH, height=Inches(0.45),
             size=13, italic=True, color=CAPTION_GREY)


def _supervisors_slide(prs, payload, chrome):
    slide = add_blank_slide(prs)
    add_content_chrome(slide, title="Supervision", **chrome)
    intern = payload["internship"]
    submission = payload["submission"]
    rows = [
        ("Industry Supervisor", intern.get("industry_supervisor_name", "")),
        ("Academic Supervisor", intern.get("academic_supervisor_name", "")),
        ("Department SIWES Officer", submission.get("siwes_officer_name", "")),
        ("Head of Department", submission.get("hod_name", "")),
    ]
    top_in = 1.8
    for role, name in rows:
        add_text(slide, role,
                 left=BODY_LEFT, top=Inches(top_in), width=Inches(5.0), height=Inches(0.5),
                 size=18, bold=True, color=NAVY)
        add_text(slide, name,
                 left=Inches(5.6), top=Inches(top_in), width=Inches(7.0), height=Inches(0.5),
                 size=18, color=BODY_TEXT)
        top_in += 1.0


def _tools_slide(prs, ch2, chrome):
    slide = add_blank_slide(prs)
    add_content_chrome(slide, title="Tools and Equipment Used", **chrome)
    col_w = Inches(4.0)
    col_h = Inches(4.9)

    def _col(items, label, left):
        add_text(slide, label,
                 left=left, top=Inches(1.4), width=col_w, height=Inches(0.45),
                 size=16, bold=True, color=NAVY)
        names = [it.get("name", "") for it in items[:6]]
        add_bullets(slide, names, left=left, top=Inches(1.95),
                    width=col_w, height=col_h, size=13)

    _col(ch2.get("hand_tools", []), "Hand Tools", Inches(0.5))
    _col(ch2.get("measuring_instruments", []), "Measuring and Testing", Inches(4.7))
    _col(ch2.get("specialised_equipment", []), "Specialised Equipment", Inches(8.9))


def _workdone_overview_slide(prs, ch2, chrome):
    slide = add_blank_slide(prs)
    add_content_chrome(slide, title="Workdone — Overview", **chrome)
    add_text(slide, ch2.get("intro", ""),
             left=BODY_LEFT, top=BODY_TOP, width=BODY_WIDTH, height=Inches(2.5),
             size=14)
    add_text(slide, "Activity Themes",
             left=BODY_LEFT, top=Inches(4.0), width=BODY_WIDTH, height=Inches(0.45),
             size=18, bold=True, color=NAVY)
    titles = [t.get("title", "") for t in ch2.get("themes", [])]
    add_bullets(slide, titles, left=BODY_LEFT, top=Inches(4.5),
                width=BODY_WIDTH, height=Inches(2.3), size=13)


def _theme_slide(prs, theme, image_entry, project_root, chrome):
    slide = add_blank_slide(prs)
    add_content_chrome(slide, title=theme.get("title", "Workdone"), **chrome)

    has_image = False
    if image_entry:
        path = image_entry.get("url_or_path", "")
        full = _resolve_path(path, project_root)
        if full:
            has_image = add_image(slide, full, left=Inches(8.1), top=Inches(1.6),
                                   width=Inches(4.6)) is not None

    paragraphs = theme.get("paragraphs", [])[:2]
    body = "\n\n".join(paragraphs) if isinstance(paragraphs, list) else str(paragraphs)
    body_w = Inches(7.3) if has_image else BODY_WIDTH
    add_text(slide, body, left=BODY_LEFT, top=BODY_TOP,
             width=body_w, height=Inches(5.4), size=14)

    if has_image and image_entry.get("description"):
        add_text(slide, image_entry["description"],
                 left=Inches(8.1), top=Inches(5.6), width=Inches(4.6), height=Inches(0.8),
                 size=11, italic=True, color=CAPTION_GREY, align=PP_ALIGN.CENTER)


def _challenges_slide(prs, ch3, chrome):
    slide = add_blank_slide(prs)
    add_content_chrome(slide, title="Challenges and Solutions", **chrome)
    rows = ch3.get("table_rows", [])[:6]
    if not rows:
        add_text(slide, "No challenges recorded.",
                 left=BODY_LEFT, top=BODY_TOP, width=BODY_WIDTH, height=Inches(1),
                 size=16)
        return

    table_left = BODY_LEFT
    table_top = BODY_TOP
    table_width = BODY_WIDTH
    table_height = Inches(5.4)

    shape = slide.shapes.add_table(
        rows=len(rows) + 1, cols=3,
        left=table_left, top=table_top, width=table_width, height=table_height,
    )
    tbl = shape.table
    tbl.columns[0].width = Inches(0.8)
    tbl.columns[1].width = Inches(5.6)
    tbl.columns[2].width = Inches(6.0)

    def _cell(cell, text, *, bold=False, fill=None, color=BODY_TEXT, size=12, align=PP_ALIGN.LEFT):
        cell.text = ""
        if fill is not None:
            cell.fill.solid()
            cell.fill.fore_color.rgb = fill
        tf = cell.text_frame
        tf.word_wrap = True
        tf.margin_left = Inches(0.1)
        tf.margin_right = Inches(0.1)
        p = tf.paragraphs[0]
        p.alignment = align
        run = p.add_run()
        run.text = text
        set_run(run, size=size, bold=bold, color=color)

    _cell(tbl.rows[0].cells[0], "S/N", bold=True, fill=NAVY, color=WHITE, size=13, align=PP_ALIGN.CENTER)
    _cell(tbl.rows[0].cells[1], "PROBLEM ENCOUNTERED", bold=True, fill=NAVY, color=WHITE, size=13)
    _cell(tbl.rows[0].cells[2], "SOLUTION APPLIED", bold=True, fill=NAVY, color=WHITE, size=13)

    for i, row in enumerate(rows, start=1):
        fill = WHITE if i % 2 == 1 else LIGHT_GREY
        _cell(tbl.rows[i].cells[0], str(i), fill=fill, size=12, align=PP_ALIGN.CENTER, bold=True, color=NAVY)
        _cell(tbl.rows[i].cells[1], row.get("problem", ""), fill=fill)
        _cell(tbl.rows[i].cells[2], row.get("solution", ""), fill=fill)

    header_h = Inches(0.5)
    add_accent_line(slide, left=table_left, top=table_top + header_h,
                    width=Inches(0.05), height=table_height - header_h, color=GOLD)


def _skills_slide(prs, payload, ch2, chrome):
    slide = add_blank_slide(prs)
    add_content_chrome(slide, title="Skills Acquired", **chrome)
    raw = payload.get("content", {}).get("skills_acquired", [])
    if isinstance(raw, str):
        skills = [s.strip().rstrip(".") for s in raw.split(";") if s.strip()]
    else:
        skills = [str(s).strip() for s in raw if str(s).strip()]
    if not skills:
        skills = [t.get("title", "").title() for t in ch2.get("themes", [])]
    skills = [s[:1].upper() + s[1:] if s else s for s in skills][:8]
    add_bullets(slide, skills,
                left=BODY_LEFT, top=BODY_TOP, width=BODY_WIDTH, height=Inches(5.4),
                size=16)


def _recommendations_slide(prs, ch4, chrome):
    slide = add_blank_slide(prs)
    add_content_chrome(slide, title="Recommendations", **chrome)
    recs = ch4.get("recommendations", [])[:8]
    add_bullets(slide, recs,
                left=BODY_LEFT, top=BODY_TOP, width=BODY_WIDTH, height=Inches(5.4),
                size=15)


def _references_slide(prs, payload, chrome):
    slide = add_blank_slide(prs)
    add_content_chrome(slide, title="References", **chrome)
    refs = render_references(payload["content"].get("references", []))[:6]
    box = slide.shapes.add_textbox(BODY_LEFT, BODY_TOP, BODY_WIDTH, Inches(5.4))
    tf = box.text_frame
    tf.word_wrap = True
    for i, r in enumerate(refs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.space_after = Pt(8)
        p.line_spacing = 1.2
        run = p.add_run()
        run.text = r
        set_run(run, size=12, color=BODY_TEXT)


def _load_content(payload):
    return {
        "ch1": stub_content.stub_chapter_one(payload),
        "ch2": stub_content.stub_chapter_two(payload),
        "ch3": stub_content.stub_chapter_three(payload),
        "ch4": stub_content.stub_chapter_four(payload),
    }


def _group_images_for_chapter(payload, chapter):
    imgs = [img for img in payload["content"].get("images", []) if int(img.get("chapter", 2)) == chapter]
    imgs.sort(key=lambda x: x.get("sequence", 0))
    return imgs


def generate_pptx(
    payload: dict,
    output_dir: str,
    *,
    project_root: Path | None = None,
    on_progress=None,
    school_config: dict | None = None,
) -> str:
    if on_progress:
        try: on_progress("designing_powerpoint")
        except Exception: pass
    project_root = project_root or Path(__file__).resolve().parents[2]
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    matric = payload["student"]["matric_no"].replace("/", "_")
    out_file = output_path / f"{matric}_report.pptx"

    content = _load_content(payload)
    ch1, ch2, ch3, ch4 = content["ch1"], content["ch2"], content["ch3"], content["ch4"]

    themes = ch2.get("themes", [])[:3]
    ch2_images = _group_images_for_chapter(payload, 2)
    total = 12 + len(themes)

    student_name = payload["student"].get("name", "")
    student_matric = payload["student"].get("matric_no", "")
    footer_name = f"{student_name} · {student_matric}" if student_matric else student_name

    def chrome_for(page_num, section_number):
        return {
            "page_num": page_num,
            "total": total,
            "student_name": footer_name,
            "section_number": section_number,
        }

    prs = new_presentation()
    _title_slide(prs, payload, school_config, project_root)

    page, section = 2, 1
    _outline_slide(prs, chrome_for(page, section)); page += 1; section += 1
    _intro_slide(prs, ch1, chrome_for(page, section)); page += 1; section += 1
    _company_profile_slide(prs, payload, ch1, project_root, chrome_for(page, section)); page += 1; section += 1
    _supervisors_slide(prs, payload, chrome_for(page, section)); page += 1; section += 1
    _tools_slide(prs, ch2, chrome_for(page, section)); page += 1; section += 1
    _workdone_overview_slide(prs, ch2, chrome_for(page, section)); page += 1; section += 1
    for i, theme in enumerate(themes):
        img = ch2_images[i] if i < len(ch2_images) else None
        _theme_slide(prs, theme, img, project_root, chrome_for(page, section))
        page += 1; section += 1
    _challenges_slide(prs, ch3, chrome_for(page, section)); page += 1; section += 1
    _skills_slide(prs, payload, ch2, chrome_for(page, section)); page += 1; section += 1
    _recommendations_slide(prs, ch4, chrome_for(page, section)); page += 1; section += 1
    _references_slide(prs, payload, chrome_for(page, section)); page += 1

    _thank_you_slide(prs, payload, school_config, project_root)

    prs.save(str(out_file))
    return str(out_file)
