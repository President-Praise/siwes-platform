from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt


NAVY = RGBColor(0x1E, 0x3A, 0x5F)
NAVY_DARK = RGBColor(0x15, 0x29, 0x3F)
GOLD = RGBColor(0xC9, 0xA8, 0x4C)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GREY = RGBColor(0xF8, 0xF9, 0xFA)
CAPTION_GREY = RGBColor(0x80, 0x80, 0x88)
BODY_TEXT = NAVY
BODY_FONT = "Times New Roman"

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

HEADER_H = Inches(1.1)
STRIPE_W = Inches(0.15)
FOOTER_LINE_Y = Inches(7.05)
FOOTER_LINE_H = Inches(0.02)
FOOTER_BAR_Y = Inches(7.07)
FOOTER_BAR_H = Inches(0.43)

# Content placement: just past the gold stripe, below the header, above the footer
BODY_LEFT = Inches(0.5)
BODY_TOP = Inches(1.3)
BODY_WIDTH = Inches(12.4)
BODY_HEIGHT = Inches(5.6)


def new_presentation():
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    return prs


def add_blank_slide(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def set_run(run, *, font=BODY_FONT, size=16, bold=False, italic=False, color=BODY_TEXT):
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color


def _add_rect(slide, *, x, y, w, h, fill):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.fill.background()
    return shape


def paint_full_navy(slide):
    """Title / thank-you slides: full navy background, no chrome."""
    _add_rect(slide, x=0, y=0, w=SLIDE_W, h=SLIDE_H, fill=NAVY)


def add_content_chrome(slide, *, page_num, total, student_name, section_number=None, title=None):
    """Standard slide chrome:
    - navy header bar (1.1" tall) with optional title (white) and section number (gold, top-right)
    - gold left stripe (0.15" wide, full height) over the header
    - thin gold separator line + navy footer bar with student name (left) and page number (right)
    """
    _add_rect(slide, x=0, y=0, w=SLIDE_W, h=HEADER_H, fill=NAVY)

    if title:
        title_box = slide.shapes.add_textbox(
            Inches(0.6), 0, SLIDE_W - Inches(2.4), HEADER_H
        )
        tf = title_box.text_frame
        tf.margin_left = 0
        tf.margin_right = 0
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT
        run = p.add_run()
        run.text = title.upper()
        set_run(run, size=28, bold=True, color=WHITE)

    if section_number is not None:
        sn_box = slide.shapes.add_textbox(
            SLIDE_W - Inches(1.8), 0, Inches(1.4), HEADER_H
        )
        tf = sn_box.text_frame
        tf.margin_left = 0
        tf.margin_right = 0
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.RIGHT
        run = p.add_run()
        run.text = f"{section_number:02d}"
        set_run(run, size=22, bold=True, color=GOLD)

    # Gold stripe drawn last so it sits on top of the header
    _add_rect(slide, x=0, y=0, w=STRIPE_W, h=SLIDE_H, fill=GOLD)

    # Footer: gold separator + navy bar
    _add_rect(slide, x=0, y=FOOTER_LINE_Y, w=SLIDE_W, h=FOOTER_LINE_H, fill=GOLD)
    _add_rect(slide, x=0, y=FOOTER_BAR_Y, w=SLIDE_W, h=FOOTER_BAR_H, fill=NAVY)

    name_box = slide.shapes.add_textbox(
        Inches(0.45), FOOTER_BAR_Y, Inches(8.5), FOOTER_BAR_H
    )
    tf = name_box.text_frame
    tf.margin_left = 0
    tf.margin_right = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    run = p.add_run()
    run.text = student_name
    set_run(run, size=10, color=WHITE)

    page_box = slide.shapes.add_textbox(
        SLIDE_W - Inches(2.0), FOOTER_BAR_Y, Inches(1.5), FOOTER_BAR_H
    )
    tf = page_box.text_frame
    tf.margin_left = 0
    tf.margin_right = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.RIGHT
    run = p.add_run()
    run.text = f"{page_num} / {total}"
    set_run(run, size=10, color=WHITE)


def add_text(slide, text, *, left, top, width, height, size=16, bold=False, italic=False,
             color=BODY_TEXT, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, line_spacing=1.2):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    paragraphs = (text or "").split("\n\n") if text else [""]
    for i, para_text in enumerate(paragraphs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(6)
        p.line_spacing = line_spacing
        run = p.add_run()
        run.text = para_text
        set_run(run, size=size, bold=bold, italic=italic, color=color)
    return box


def add_bullets(slide, items, *, left, top, width, height, size=16, color=BODY_TEXT,
                indent_level=0):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.space_after = Pt(6)
        p.line_spacing = 1.2
        if indent_level > 0:
            p.level = indent_level
        marker = p.add_run()
        marker.text = "●  "
        set_run(marker, size=size, bold=True, color=GOLD)
        body = p.add_run()
        body.text = str(item)
        set_run(body, size=size, color=color)
    return box


def add_image(slide, image_path, *, left, top, width=None, height=None):
    p = Path(str(image_path))
    if not p.exists():
        return None
    try:
        kwargs = {}
        if width is not None:
            kwargs["width"] = width
        if height is not None:
            kwargs["height"] = height
        return slide.shapes.add_picture(str(p), left, top, **kwargs)
    except Exception:
        return None


def add_accent_line(slide, *, left, top, width, height=Inches(0.05), color=GOLD):
    return _add_rect(slide, x=left, y=top, w=width, h=height, fill=color)
