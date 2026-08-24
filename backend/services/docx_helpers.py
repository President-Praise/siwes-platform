from docx.enum.section import WD_SECTION_START
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Pt, Inches, RGBColor


NAVY = RGBColor(0x00, 0x33, 0x66)
BLACK = RGBColor(0x00, 0x00, 0x00)
BODY_FONT = "Times New Roman"
BODY_SIZE = Pt(12)
LINE_SPACING = 1.5


def set_page_margins(section, *, top=1.0, bottom=1.0, left=1.25, right=1.0):
    section.top_margin = Inches(top)
    section.bottom_margin = Inches(bottom)
    section.left_margin = Inches(left)
    section.right_margin = Inches(right)


def _set_footer_page_format(section, fmt: str, start: int | None = None):
    sectPr = section._sectPr
    for existing in sectPr.findall(qn("w:pgNumType")):
        sectPr.remove(existing)
    pg = OxmlElement("w:pgNumType")
    pg.set(qn("w:fmt"), fmt)
    if start is not None:
        pg.set(qn("w:start"), str(start))
    sectPr.append(pg)


def add_page_number_footer(section, fmt: str = "decimal", start: int | None = None, suppress: bool = False):
    _set_footer_page_format(section, fmt, start)
    section.footer.is_linked_to_previous = False
    section.header.is_linked_to_previous = False
    footer = section.footer
    p = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for r in list(p.runs):
        r.text = ""
    if suppress:
        return
    run = p.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE   \\* MERGEFORMAT"
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_begin)
    run._r.append(instr)
    run._r.append(fld_sep)
    run._r.append(fld_end)
    run.font.name = BODY_FONT
    run.font.size = Pt(11)


def new_section(doc, start_type=WD_SECTION_START.NEW_PAGE):
    section = doc.add_section(start_type)
    set_page_margins(section)
    return section


def add_page_break(doc):
    p = doc.add_paragraph()
    run = p.add_run()
    br = OxmlElement("w:br")
    br.set(qn("w:type"), "page")
    run._r.append(br)
    return p


def style_run(run, *, font=BODY_FONT, size=BODY_SIZE, bold=False, italic=False, color=BLACK, all_caps=False):
    run.font.name = font
    run.font.size = size
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), font)
    rFonts.set(qn("w:hAnsi"), font)
    rFonts.set(qn("w:cs"), font)
    if all_caps:
        caps = OxmlElement("w:caps")
        caps.set(qn("w:val"), "1")
        rPr.append(caps)


def add_paragraph(doc_or_cell, text: str, *, align=WD_ALIGN_PARAGRAPH.JUSTIFY, bold=False, italic=False,
                   size=BODY_SIZE, color=BLACK, line_spacing=LINE_SPACING, space_after=Pt(6), space_before=Pt(0),
                   keep_with_next=False):
    p = doc_or_cell.add_paragraph()
    p.alignment = align
    pf = p.paragraph_format
    pf.line_spacing = line_spacing
    pf.space_after = space_after
    pf.space_before = space_before
    pf.keep_with_next = keep_with_next
    run = p.add_run(text)
    style_run(run, size=size, bold=bold, italic=italic, color=color)
    return p


def add_centered(doc, text, **kwargs):
    return add_paragraph(doc, text, align=WD_ALIGN_PARAGRAPH.CENTER, **kwargs)


def add_chapter_heading(doc, chapter_word: str, chapter_title: str):
    add_page_break(doc) if False else None
    p1 = doc.add_paragraph()
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p1.paragraph_format.space_before = Pt(0)
    p1.paragraph_format.space_after = Pt(6)
    p1.paragraph_format.keep_with_next = True
    r1 = p1.add_run(chapter_word.upper())
    style_run(r1, size=Pt(16), bold=True)

    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.paragraph_format.space_after = Pt(18)
    p2.paragraph_format.keep_with_next = True
    r2 = p2.add_run(chapter_title.upper())
    style_run(r2, size=Pt(16), bold=True)


def add_section_heading(doc, number: str, title: str, *, level: int = 1):
    sizes = {1: Pt(13), 2: Pt(12), 3: Pt(12)}
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.keep_with_next = True
    full = f"{number} {title.upper()}"
    r = p.add_run(full)
    style_run(r, size=sizes.get(level, Pt(12)), bold=True)
    return p


def add_bullet(doc, text: str):
    p = doc.add_paragraph(style="List Bullet")
    pf = p.paragraph_format
    pf.line_spacing = 1.15
    pf.space_after = Pt(4)
    for r in list(p.runs):
        r.text = ""
    run = p.add_run(text)
    style_run(run, size=BODY_SIZE)
    return p


def add_numbered_roman(doc, items: list[str]):
    romans = ["i.", "ii.", "iii.", "iv.", "v.", "vi.", "vii.", "viii.", "ix.", "x."]
    for idx, text in enumerate(items):
        marker = romans[idx] if idx < len(romans) else f"{idx + 1}."
        add_paragraph(doc, f"{marker} {text}", align=WD_ALIGN_PARAGRAPH.JUSTIFY, line_spacing=1.5)


def insert_toc_field(doc, *, heading_levels="1-3"):
    p = doc.add_paragraph()
    run = p.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    fld_begin.set(qn("w:dirty"), "true")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = f' TOC \\o "{heading_levels}" \\h \\z \\u '
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    fld_text = OxmlElement("w:t")
    fld_text.text = "Right-click and select 'Update Field' to populate the Table of Contents."
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_begin)
    run._r.append(instr)
    run._r.append(fld_sep)
    placeholder_run = p.add_run("Right-click and select 'Update Field' to populate the Table of Contents.")
    style_run(placeholder_run, italic=True, size=Pt(11))
    run._r.append(fld_end)
    return p
