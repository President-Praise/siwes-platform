"""SIWES Word report generator — school-config-aware.

Differences from the original (single-tenant Landmark) generator:
  - Accepts a `school_config` dict to drive university name, logo path,
    submission clause, and award text. No hardcoded Landmark references.
  - Falls back to safe defaults so the function still works without config.
"""

import os
from pathlib import Path
from typing import Any

from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Pt, Inches, RGBColor

from . import stub_content
from .docx_helpers import (
    BODY_FONT, BODY_SIZE, LINE_SPACING, NAVY,
    add_bullet, add_centered, add_chapter_heading, add_numbered_roman,
    add_page_break, add_page_number_footer, add_paragraph, add_section_heading,
    insert_toc_field, new_section, set_page_margins, style_run,
)
from .references import render_references


USE_CLAUDE = os.environ.get("REPORT_USE_CLAUDE", "0") == "1"


def _default_school_config() -> dict:
    return {
        "name": "the University",
        "full_name": "THE UNIVERSITY",
        "logo_path": None,
        "submission_clause": "SUBMITTED TO THE {department}, {college}, {university_full_name}",
        "award_clause": "IN PARTIAL FULFILMENT OF THE REQUIREMENT FOR AWARD OF {degree}",
    }


def _resolved_school(school_config: dict | None) -> dict:
    cfg = _default_school_config()
    if school_config:
        cfg.update({k: v for k, v in school_config.items() if v is not None})
    return cfg


def _load_claude_content(payload: dict, school_config: dict, on_progress=None, force_stub: bool = False) -> dict:
    def _emit(stage: str):
        if on_progress:
            try: on_progress(stage)
            except Exception: pass
    if force_stub or not USE_CLAUDE:
        _emit("drafting_introduction")
        _emit("composing_workdone")
        _emit("analyzing_challenges")
        _emit("wrapping_chapter_four")
        return {
            "ch1": stub_content.stub_chapter_one(payload),
            "ch2": stub_content.stub_chapter_two(payload),
            "ch3": stub_content.stub_chapter_three(payload),
            "ch4": stub_content.stub_chapter_four(payload),
            "acknowledgement": stub_content.stub_acknowledgement(payload),
            "abstract": stub_content.stub_abstract(payload),
        }
    from . import report_prompts
    from .claude_client import call_claude, call_claude_json

    system = report_prompts.system_prompt(school_config)

    _emit("drafting_introduction")
    ch1 = call_claude_json(system, report_prompts.chapter_one_prompt(payload), max_tokens=8000)
    _emit("composing_workdone")
    ch2 = call_claude_json(system, report_prompts.chapter_two_prompt(payload), max_tokens=16000)
    _emit("analyzing_challenges")
    ch3 = call_claude_json(system, report_prompts.chapter_three_prompt(payload), max_tokens=6000)
    _emit("wrapping_chapter_four")
    ch4 = call_claude_json(system, report_prompts.chapter_four_prompt(payload), max_tokens=3000)
    _emit("writing_acknowledgement")
    ack = call_claude(system, report_prompts.acknowledgement_prompt(payload), max_tokens=800)
    summaries = {"ch2_themes": ", ".join(t.get("title", "") for t in ch2.get("themes", []))}
    abstract = call_claude(system, report_prompts.abstract_prompt(payload, summaries), max_tokens=600)
    return {"ch1": ch1, "ch2": ch2, "ch3": ch3, "ch4": ch4, "acknowledgement": ack, "abstract": abstract}


def _add_centered_logo(doc, logo_path: Path | None, width, *, space_before=Pt(0)):
    if not logo_path or not Path(logo_path).exists():
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = space_before
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run()
    try:
        run.add_picture(str(logo_path), width=width)
    except Exception:
        pass


def _resolve_logo(school_config: dict, project_root: Path) -> Path | None:
    logo = school_config.get("logo_path")
    if not logo:
        return None
    p = Path(logo)
    if not p.is_absolute():
        p = project_root / logo
    return p if p.exists() else None


def _cover_block(doc, payload, school_config, *, with_submission_clause: bool, project_root: Path):
    student = payload["student"]
    intern = payload["internship"]
    name_for_cover = student.get("name_for_cover") or student["name"].upper()
    id_block = student.get("student_id")
    matric = student["matric_no"]
    id_line = f"({id_block} / {matric})" if id_block else f"({matric})"
    department_upper = f"DEPARTMENT OF {student['department'].upper()}"
    college_upper = student.get("college", "").upper() or "COLLEGE"
    university_full_upper = school_config.get("full_name", "").upper()

    logo_path = _resolve_logo(school_config, project_root)
    _add_centered_logo(doc, logo_path, Inches(1.5))

    add_centered(doc, "A TECHNICAL REPORT", bold=True, size=Pt(14), line_spacing=1.5, space_after=Pt(8))
    add_centered(doc, "ON", bold=True, size=Pt(14), line_spacing=1.5, space_after=Pt(8))
    add_centered(doc, "STUDENT INDUSTRIAL WORK EXPERIENCE SCHEME (SIWES)", bold=True, size=Pt(14), line_spacing=1.5, space_after=Pt(8))
    add_centered(doc, "UNDERTAKEN AT", bold=True, size=Pt(14), line_spacing=1.5, space_after=Pt(8))

    company_logo = intern.get("company_logo_url")
    if company_logo:
        company_logo_path = Path(company_logo) if os.path.isabs(company_logo) else project_root / company_logo
        _add_centered_logo(doc, company_logo_path, Inches(1.8))

    add_centered(doc, intern["company_name"].upper(), bold=True, size=Pt(16), line_spacing=1.5, space_after=Pt(8))
    add_centered(doc, "BY", bold=True, size=Pt(14), line_spacing=1.5, space_after=Pt(8))
    add_centered(doc, name_for_cover, bold=True, size=Pt(14), line_spacing=1.5, space_after=Pt(8))
    add_centered(doc, id_line, bold=False, size=Pt(13), line_spacing=1.5, space_after=Pt(8))

    if with_submission_clause:
        degree = student.get("degree", "")
        degree_short = student.get("degree_short", "")
        submission_template = school_config.get(
            "submission_clause",
            "SUBMITTED TO THE {department}, {college}, {university_full_name}",
        )
        submission_block = submission_template.format(
            department=department_upper,
            college=college_upper,
            university_full_name=university_full_upper,
        ).upper()
        add_centered(doc, submission_block, bold=True, size=Pt(13), line_spacing=1.5, space_after=Pt(8))

        award_template = school_config.get(
            "award_clause",
            "IN PARTIAL FULFILMENT OF THE REQUIREMENT FOR AWARD OF {degree}",
        )
        award_block = award_template.format(
            degree=degree.upper() if degree else "",
            degree_short=degree_short.upper() if degree_short else "",
        )
        add_centered(doc, award_block, bold=True, size=Pt(13), line_spacing=1.5, space_after=Pt(8))
    else:
        add_centered(doc, department_upper, bold=True, size=Pt(13), line_spacing=1.5, space_after=Pt(8))
        add_centered(doc, college_upper, bold=True, size=Pt(13), line_spacing=1.5, space_after=Pt(8))
        add_centered(doc, university_full_upper, bold=True, size=Pt(13), line_spacing=1.5, space_after=Pt(8))

    add_centered(doc, intern["duration"].upper(), bold=True, size=Pt(13), line_spacing=1.5, space_after=Pt(8))


def _set_section_vertical_align(section, val: str):
    sectPr = section._sectPr
    for existing in sectPr.findall(qn("w:vAlign")):
        sectPr.remove(existing)
    vAlign = OxmlElement("w:vAlign")
    vAlign.set(qn("w:val"), val)
    sectPr.append(vAlign)


def _build_title_section(doc, payload, school_config, project_root: Path):
    section = doc.sections[0]
    set_page_margins(section)
    add_page_number_footer(section, fmt="decimal", suppress=True)
    _set_section_vertical_align(section, "center")

    _cover_block(doc, payload, school_config, with_submission_clause=False, project_root=project_root)
    add_page_break(doc)
    _cover_block(doc, payload, school_config, with_submission_clause=True, project_root=project_root)


def _build_declaration(doc, payload):
    student_name = payload["student"]["name"]
    academic_sup = payload["internship"].get("academic_supervisor_name", "[Academic Supervisor]")
    add_centered(doc, "DECLARATION", bold=True, size=Pt(14))
    add_paragraph(doc, "", line_spacing=1.0)
    body = (
        f"I, {student_name}, declare that this write-up is a technical report of my activities and "
        f"experience acquired during the SIWES period. This report is written by me under the "
        f"supervision of {academic_sup}. It has not been presented for the award of any degree in any "
        "institution. All sources of information are specifically acknowledged by means of reference."
    )
    add_paragraph(doc, body, line_spacing=2.0, space_after=Pt(36))
    _signature_row(doc, ("Signature", "Date"))


def _signature_row(doc, labels):
    table = doc.add_table(rows=2, cols=2)
    table.autofit = True
    for c in range(2):
        cell = table.rows[0].cells[c]
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run("____________________________")
        style_run(r, size=Pt(12))
    for c, label in enumerate(labels):
        cell = table.rows[1].cells[c]
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(label)
        style_run(r, size=Pt(12))


def _signature_block(doc, name, role):
    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_before = Pt(0)
    spacer.paragraph_format.space_after = Pt(24)

    table = doc.add_table(rows=2, cols=2)
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    tblPr = table._tbl.tblPr
    tblBorders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        b = OxmlElement(f"w:{edge}")
        b.set(qn("w:val"), "nil")
        tblBorders.append(b)
    tblPr.append(tblBorders)

    widths = (Inches(3.75), Inches(2.5))
    for row in table.rows:
        for cell, w in zip(row.cells, widths):
            cell.width = w
            tcPr = cell._tc.get_or_add_tcPr()
            tcBorders = OxmlElement("w:tcBorders")
            for edge in ("top", "left", "bottom", "right"):
                b = OxmlElement(f"w:{edge}")
                b.set(qn("w:val"), "nil")
                tcBorders.append(b)
            tcPr.append(tcBorders)

    def _fill(cell, text, *, bold=False):
        cell.text = ""
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(text)
        style_run(r, bold=bold, size=Pt(12))

    _fill(table.rows[0].cells[0], f"_____ {name} _____", bold=True)
    _fill(table.rows[0].cells[1], "________________________")
    _fill(table.rows[1].cells[0], role)
    _fill(table.rows[1].cells[1], "Signature and Date")


def _build_certification(doc, payload, school_config):
    student_name = payload["student"]["name"]
    academic_sup = payload["internship"].get("academic_supervisor_name", "[Academic Supervisor]")
    siwes_officer = payload["submission"].get("siwes_officer_name", "[SIWES Officer]")
    hod = payload["submission"].get("hod_name", "[Head of Department]")
    degree = payload["student"].get("degree", "the degree")
    add_centered(doc, "CERTIFICATION", bold=True, size=Pt(14))
    add_paragraph(doc, "", line_spacing=1.0)
    body = (
        f"This SIWES Report by {student_name} meets the requirements governing the award of "
        f"{degree} and is approved for its contribution to the knowledge and literary presentation."
    )
    add_paragraph(doc, body, line_spacing=2.0)
    _signature_block(doc, academic_sup, "Supervisor")
    _signature_block(doc, siwes_officer, "Department SIWES Officer")
    _signature_block(doc, hod, "Head of Department")


def _build_acknowledgement(doc, ack_text):
    add_centered(doc, "ACKNOWLEDGEMENT", bold=True, size=Pt(14))
    add_paragraph(doc, "", line_spacing=1.0)
    for para in [p.strip() for p in ack_text.split("\n\n") if p.strip()]:
        add_paragraph(doc, para, line_spacing=1.5)


def _build_abstract(doc, abstract_text):
    add_centered(doc, "ABSTRACT", bold=True, size=Pt(14))
    add_paragraph(doc, "", line_spacing=1.0)
    for para in [p.strip() for p in abstract_text.split("\n\n") if p.strip()]:
        add_paragraph(doc, para, line_spacing=1.5)


def _build_toc(doc):
    add_centered(doc, "TABLE OF CONTENTS", bold=True, size=Pt(14))
    add_paragraph(doc, "", line_spacing=1.0)
    insert_toc_field(doc, heading_levels="1-3")


def _build_lof_lot_placeholders(doc):
    add_centered(doc, "LIST OF FIGURES", bold=True, size=Pt(14))
    add_paragraph(doc, "", line_spacing=1.0)
    p = doc.add_paragraph()
    run = p.add_run()
    fld_begin = OxmlElement("w:fldChar"); fld_begin.set(qn("w:fldCharType"), "begin"); fld_begin.set(qn("w:dirty"), "true")
    instr = OxmlElement("w:instrText"); instr.set(qn("xml:space"), "preserve")
    instr.text = ' TOC \\h \\z \\c "Figure" '
    fld_sep = OxmlElement("w:fldChar"); fld_sep.set(qn("w:fldCharType"), "separate")
    fld_end = OxmlElement("w:fldChar"); fld_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_begin); run._r.append(instr); run._r.append(fld_sep)
    placeholder = p.add_run("Right-click and select 'Update Field' to populate the List of Figures.")
    style_run(placeholder, italic=True, size=Pt(11))
    run._r.append(fld_end)

    add_page_break(doc)
    add_centered(doc, "LIST OF TABLES", bold=True, size=Pt(14))
    add_paragraph(doc, "", line_spacing=1.0)
    p2 = doc.add_paragraph()
    run2 = p2.add_run()
    fld_begin2 = OxmlElement("w:fldChar"); fld_begin2.set(qn("w:fldCharType"), "begin"); fld_begin2.set(qn("w:dirty"), "true")
    instr2 = OxmlElement("w:instrText"); instr2.set(qn("xml:space"), "preserve")
    instr2.text = ' TOC \\h \\z \\c "Table" '
    fld_sep2 = OxmlElement("w:fldChar"); fld_sep2.set(qn("w:fldCharType"), "separate")
    fld_end2 = OxmlElement("w:fldChar"); fld_end2.set(qn("w:fldCharType"), "end")
    run2._r.append(fld_begin2); run2._r.append(instr2); run2._r.append(fld_sep2)
    placeholder2 = p2.add_run("Right-click and select 'Update Field' to populate the List of Tables.")
    style_run(placeholder2, italic=True, size=Pt(11))
    run2._r.append(fld_end2)


def _set_heading_style(p, level: int):
    p.style = p.part.document.styles[f"Heading {level}"]


def _add_caption(doc, label_kind: str, number: str, caption_text: str):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.style = doc.styles["Caption"]
    r1 = p.add_run(f"{label_kind} ")
    style_run(r1, bold=True, size=Pt(11))

    fld_begin = OxmlElement("w:fldChar"); fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText"); instr.set(qn("xml:space"), "preserve")
    instr.text = f' SEQ {label_kind} \\* ARABIC '
    fld_sep = OxmlElement("w:fldChar"); fld_sep.set(qn("w:fldCharType"), "separate")
    fld_text = OxmlElement("w:t"); fld_text.text = number
    fld_end = OxmlElement("w:fldChar"); fld_end.set(qn("w:fldCharType"), "end")
    seq_run = p.add_run()
    style_run(seq_run, bold=True, size=Pt(11))
    seq_run._r.append(fld_begin); seq_run._r.append(instr); seq_run._r.append(fld_sep)
    seq_run._r.append(fld_text); seq_run._r.append(fld_end)

    r2 = p.add_run(f": {caption_text}")
    style_run(r2, size=Pt(11))


def _insert_image_block(doc, image_entry: dict, *, chapter: int, sequence: int, project_root: Path):
    img_path = image_entry.get("url_or_path", "")
    desc = image_entry.get("description", "")
    full_path = project_root / img_path if not os.path.isabs(img_path) else Path(img_path)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(0)
    run = p.add_run()
    if full_path.exists():
        try:
            run.add_picture(str(full_path), width=Inches(4.5))
        except Exception:
            placeholder = p.add_run(f"[Image not loadable: {img_path}]")
            style_run(placeholder, italic=True, size=Pt(11))
    else:
        placeholder = p.add_run(f"[INSERT PHOTO: Fig {chapter}.{sequence}]")
        style_run(placeholder, italic=True, size=Pt(11))
    _add_caption(doc, "Figure", f"{chapter}.{sequence}", desc)


def _split_paragraphs(value) -> list[str]:
    if isinstance(value, list):
        return [str(p).strip() for p in value if str(p).strip()]
    text = str(value or "").strip()
    if not text:
        return []
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def _add_paragraphs(doc, value) -> None:
    for para in _split_paragraphs(value):
        add_paragraph(doc, para)


def _build_chapter_one(doc, payload, ch1):
    add_chapter_heading(doc, "CHAPTER ONE", "INTRODUCTION")
    _add_paragraphs(doc, ch1.get("intro"))

    add_section_heading(doc, "1.1", "Background of Industrial Training Fund", level=1)
    _set_heading_style(doc.paragraphs[-1], 1)
    _add_paragraphs(doc, ch1.get("background_itf"))

    add_section_heading(doc, "1.2", "Core Objectives of ITF", level=1)
    _set_heading_style(doc.paragraphs[-1], 1)
    for b in ch1.get("core_objectives_itf", []):
        add_bullet(doc, b)

    add_section_heading(doc, "1.3", "Historical Background of SIWES", level=1)
    _set_heading_style(doc.paragraphs[-1], 1)
    _add_paragraphs(doc, ch1.get("historical_background_siwes"))

    add_section_heading(doc, "1.4", "Aim of SIWES", level=1)
    _set_heading_style(doc.paragraphs[-1], 1)
    _add_paragraphs(doc, ch1.get("aim_of_siwes"))

    add_section_heading(doc, "1.5", "Objectives of SIWES", level=1)
    _set_heading_style(doc.paragraphs[-1], 1)
    add_numbered_roman(doc, ch1.get("objectives_of_siwes", []))

    add_section_heading(doc, "1.6", f"Company Profile - {payload['internship']['company_name']}", level=1)
    _set_heading_style(doc.paragraphs[-1], 1)
    _add_paragraphs(doc, ch1.get("company_profile"))

    add_section_heading(doc, "1.7", f"Brief History of {payload['internship']['company_name']}", level=1)
    _set_heading_style(doc.paragraphs[-1], 1)
    _add_paragraphs(doc, ch1.get("brief_history"))

    add_section_heading(doc, "1.8", "Organisational Structure", level=1)
    _set_heading_style(doc.paragraphs[-1], 1)
    _add_paragraphs(doc, ch1.get("organisational_structure_intro"))
    for i, dept in enumerate(ch1.get("departments", []), start=1):
        h = doc.add_paragraph()
        h.paragraph_format.space_before = Pt(8)
        h.paragraph_format.space_after = Pt(4)
        h.paragraph_format.keep_with_next = True
        r = h.add_run(f"{i}. {dept.get('name', '')}")
        style_run(r, bold=True, size=Pt(12))
        _add_paragraphs(doc, dept.get("description"))


def _build_chapter_two(doc, payload, ch2, images_by_chapter, project_root):
    add_page_break(doc)
    add_chapter_heading(doc, "CHAPTER TWO", "WORKDONE")
    _add_paragraphs(doc, ch2.get("intro"))

    add_section_heading(doc, "2.1", "Basic Tools, Instruments, and Equipment Used", level=1)
    _set_heading_style(doc.paragraphs[-1], 1)
    _add_paragraphs(doc, ch2.get("tools_intro"))

    add_section_heading(doc, "2.1.1", "Basic Hand Tools", level=2)
    _set_heading_style(doc.paragraphs[-1], 2)
    for item in ch2.get("hand_tools", []):
        _named_block(doc, item.get("name", ""), item.get("description", ""))

    add_section_heading(doc, "2.1.2", "Measuring and Testing Instruments", level=2)
    _set_heading_style(doc.paragraphs[-1], 2)
    for item in ch2.get("measuring_instruments", []):
        _named_block(doc, item.get("name", ""), item.get("description", ""))

    add_section_heading(doc, "2.1.3", "Specialised Equipment", level=2)
    _set_heading_style(doc.paragraphs[-1], 2)
    for item in ch2.get("specialised_equipment", []):
        _named_block(doc, item.get("name", ""), item.get("description", ""))

    add_section_heading(doc, "2.2", "Summary of Activities", level=1)
    _set_heading_style(doc.paragraphs[-1], 1)

    ch2_images = images_by_chapter.get(2, [])
    img_idx = 0
    for i, theme in enumerate(ch2.get("themes", []), start=1):
        add_section_heading(doc, f"2.2.{i}", theme.get("title", ""), level=2)
        _set_heading_style(doc.paragraphs[-1], 2)
        _add_paragraphs(doc, theme.get("paragraphs"))
        if img_idx < len(ch2_images):
            img = ch2_images[img_idx]
            _insert_image_block(doc, img, chapter=2, sequence=img_idx + 1, project_root=project_root)
            img_idx += 1


def _named_block(doc, name: str, description) -> None:
    h = doc.add_paragraph()
    h.paragraph_format.space_before = Pt(8)
    h.paragraph_format.space_after = Pt(2)
    h.paragraph_format.keep_with_next = True
    r = h.add_run(name)
    style_run(r, bold=True, italic=True, size=Pt(12))
    _add_paragraphs(doc, description)


def _build_chapter_three(doc, payload, ch3, images_by_chapter, project_root):
    add_page_break(doc)
    add_chapter_heading(doc, "CHAPTER THREE", "CHALLENGES ENCOUNTERED AND PROBLEMS SOLVED")

    add_section_heading(doc, "3.1", "Problems Encountered", level=1)
    _set_heading_style(doc.paragraphs[-1], 1)
    _add_paragraphs(doc, ch3.get("intro_3_1"))
    _add_caption(doc, "Table", "3.1", "Problems Encountered During SIWES and Solutions Applied")

    rows = ch3.get("table_rows", [])
    table = doc.add_table(rows=1 + len(rows), cols=3)
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    for i, label in enumerate(["S/N", "PROBLEM ENCOUNTERED", "SOLUTIONS APPLIED"]):
        hdr[i].text = ""
        p = hdr[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(label)
        style_run(r, bold=True, size=Pt(11))
        _shade_cell(hdr[i], "D9E2F3")
    for idx, row in enumerate(rows, start=1):
        cells = table.rows[idx].cells
        cells[0].text = ""
        p0 = cells[0].paragraphs[0]; p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r0 = p0.add_run(str(idx)); style_run(r0, size=Pt(11))
        for col, key in enumerate(["problem", "solution"], start=1):
            cells[col].text = ""
            p = cells[col].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            r = p.add_run(row.get(key, ""))
            style_run(r, size=Pt(11))

    add_section_heading(doc, "3.2", "Problems Solved", level=1)
    _set_heading_style(doc.paragraphs[-1], 1)
    _add_paragraphs(doc, ch3.get("intro_3_2"))
    for i, item in enumerate(ch3.get("solved_items", []), start=1):
        h = doc.add_paragraph()
        h.paragraph_format.space_before = Pt(8)
        h.paragraph_format.space_after = Pt(2)
        h.paragraph_format.keep_with_next = True
        r = h.add_run(f"{i}. {item.get('title', '')}")
        style_run(r, bold=True, size=Pt(12))
        _add_paragraphs(doc, item.get("paragraph"))

    _add_paragraphs(doc, ch3.get("closing"))

    ch3_images = images_by_chapter.get(3, [])
    for i, img in enumerate(ch3_images, start=1):
        _insert_image_block(doc, img, chapter=3, sequence=i, project_root=project_root)


def _shade_cell(cell, hex_color: str):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def _build_chapter_four(doc, payload, ch4):
    add_page_break(doc)
    add_chapter_heading(doc, "CHAPTER FOUR", "SUMMARY, CONCLUSION AND RECOMMENDATION")

    add_section_heading(doc, "4.1", "Summary", level=1)
    _set_heading_style(doc.paragraphs[-1], 1)
    _add_paragraphs(doc, ch4.get("summary"))

    add_section_heading(doc, "4.2", "Conclusion", level=1)
    _set_heading_style(doc.paragraphs[-1], 1)
    _add_paragraphs(doc, ch4.get("conclusion"))

    add_section_heading(doc, "4.3", "Recommendations", level=1)
    _set_heading_style(doc.paragraphs[-1], 1)
    add_numbered_roman(doc, ch4.get("recommendations", []))


def _build_references(doc, payload):
    add_page_break(doc)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(18)
    p.paragraph_format.keep_with_next = True
    r = p.add_run("REFERENCES")
    style_run(r, size=Pt(16), bold=True)

    rendered = render_references(payload["content"].get("references", []))
    for ref in rendered:
        para = doc.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        pf = para.paragraph_format
        pf.left_indent = Inches(0.5)
        pf.first_line_indent = Inches(-0.5)
        pf.space_after = Pt(8)
        pf.line_spacing = 1.5
        run = para.add_run(ref)
        style_run(run, size=Pt(12))


def _group_images(payload):
    by_chapter: dict[int, list] = {}
    for img in payload["content"].get("images", []):
        ch = int(img.get("chapter", 2))
        by_chapter.setdefault(ch, []).append(img)
    for ch in by_chapter:
        by_chapter[ch].sort(key=lambda x: x.get("sequence", 0))
    return by_chapter


def _enable_auto_update_fields(doc):
    settings_el = doc.settings.element
    for existing in settings_el.findall(qn("w:updateFields")):
        settings_el.remove(existing)
    upd = OxmlElement("w:updateFields")
    upd.set(qn("w:val"), "true")
    settings_el.append(upd)


def _configure_heading_styles(doc):
    for level, size in [(1, 13), (2, 12), (3, 12)]:
        style = doc.styles[f"Heading {level}"]
        font = style.font
        font.name = BODY_FONT
        font.size = Pt(size)
        font.bold = True
        font.color.rgb = RGBColor(0x00, 0x00, 0x00)
        rPr = style.element.get_or_add_rPr()
        rFonts = rPr.find(qn("w:rFonts"))
        if rFonts is None:
            rFonts = OxmlElement("w:rFonts"); rPr.append(rFonts)
        rFonts.set(qn("w:ascii"), BODY_FONT)
        rFonts.set(qn("w:hAnsi"), BODY_FONT)
        pPr = style.element.get_or_add_pPr()
        for k in pPr.findall(qn("w:keepNext")):
            pPr.remove(k)
        keep = OxmlElement("w:keepNext"); pPr.append(keep)


def generate_report(
    payload: dict,
    output_dir: str,
    *,
    project_root: Path | None = None,
    on_progress=None,
    force_stub: bool = False,
    school_config: dict | None = None,
) -> str:
    def _emit(stage: str):
        if on_progress:
            try: on_progress(stage)
            except Exception: pass
    project_root = project_root or Path(__file__).resolve().parents[2]
    school = _resolved_school(school_config)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    matric = payload["student"]["matric_no"].replace("/", "_")
    out_file = output_path / f"{matric}_report.docx"

    doc = Document()
    _configure_heading_styles(doc)

    base_style = doc.styles["Normal"]
    base_style.font.name = BODY_FONT
    base_style.font.size = BODY_SIZE
    rPr = base_style.element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts"); rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), BODY_FONT); rFonts.set(qn("w:hAnsi"), BODY_FONT)

    _build_title_section(doc, payload, school, project_root)

    prelim_section = new_section(doc, WD_SECTION_START.NEW_PAGE)
    add_page_number_footer(prelim_section, fmt="lowerRoman", start=1)
    _set_section_vertical_align(prelim_section, "top")

    content = _load_claude_content(payload, school, on_progress=on_progress, force_stub=force_stub)
    _emit("building_word_document")

    _build_declaration(doc, payload)
    add_page_break(doc)
    _build_certification(doc, payload, school)
    add_page_break(doc)
    _build_acknowledgement(doc, content["acknowledgement"])
    add_page_break(doc)
    _build_abstract(doc, content["abstract"])
    add_page_break(doc)
    _build_toc(doc)
    add_page_break(doc)
    _build_lof_lot_placeholders(doc)

    main_section = new_section(doc, WD_SECTION_START.NEW_PAGE)
    add_page_number_footer(main_section, fmt="decimal", start=1)
    _set_section_vertical_align(main_section, "top")

    images_by_chapter = _group_images(payload)

    _build_chapter_one(doc, payload, content["ch1"])
    _build_chapter_two(doc, payload, content["ch2"], images_by_chapter, project_root)
    _build_chapter_three(doc, payload, content["ch3"], images_by_chapter, project_root)
    _build_chapter_four(doc, payload, content["ch4"])
    _build_references(doc, payload)

    _enable_auto_update_fields(doc)
    doc.save(str(out_file))
    return str(out_file)
