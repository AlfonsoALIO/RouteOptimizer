#!/usr/bin/env python3
"""Build RouteOptimizer executive summary PDF."""

from pathlib import Path

from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT = Path("/Users/R2/Apps/RouteOptimizer/output/pdf/RouteOptimizer-Executive-Summary.pdf")
TMP = Path("/Users/R2/Apps/RouteOptimizer/tmp/pdfs")

INK = HexColor("#1A2332")
MUTED = HexColor("#5A6577")
RULE = HexColor("#D0D5DD")
ACCENT = HexColor("#0F6B5C")
BAND = HexColor("#F3F5F7")
WHITE = white


class HRule(Flowable):
    def __init__(self, width, color=RULE, thickness=0.6):
        super().__init__()
        self.width = width
        self.color = color
        self.thickness = thickness
        self.height = 8

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, 4, self.width, 4)


class AccentBar(Flowable):
    def __init__(self, width, color=ACCENT, height=3):
        super().__init__()
        self.width = width
        self.color = color
        self.height = height

    def draw(self):
        self.canv.setFillColor(self.color)
        self.canv.rect(0, 0, self.width, self.height, fill=1, stroke=0)


def styles():
    base = getSampleStyleSheet()
    s = {}
    s["kicker"] = ParagraphStyle(
        "kicker",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=9,
        textColor=ACCENT,
        tracking=1.2,
        spaceAfter=6,
    )
    s["title"] = ParagraphStyle(
        "title",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=INK,
        spaceAfter=4,
    )
    s["subtitle"] = ParagraphStyle(
        "subtitle",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        textColor=MUTED,
        spaceAfter=8,
    )
    s["section"] = ParagraphStyle(
        "section",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        textColor=INK,
        spaceBefore=8,
        spaceAfter=4,
    )
    s["body"] = ParagraphStyle(
        "body",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=INK,
        alignment=TA_JUSTIFY,
        spaceAfter=4,
    )
    s["body_left"] = ParagraphStyle(
        "body_left",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=INK,
        alignment=TA_LEFT,
        spaceAfter=3,
    )
    s["epic_title"] = ParagraphStyle(
        "epic_title",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=INK,
    )
    s["epic_body"] = ParagraphStyle(
        "epic_body",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=MUTED,
    )
    s["meta"] = ParagraphStyle(
        "meta",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=MUTED,
    )
    s["footer"] = ParagraphStyle(
        "footer",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=8,
        textColor=MUTED,
        alignment=TA_CENTER,
    )
    s["cell"] = ParagraphStyle(
        "cell",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=INK,
    )
    s["cell_head"] = ParagraphStyle(
        "cell_head",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=10,
        textColor=INK,
    )
    return s


def epic_row(num, title, body, s):
    return [
        Paragraph(f"{num}", s["epic_title"]),
        [
            Paragraph(title, s["epic_title"]),
            Spacer(1, 2),
            Paragraph(body, s["epic_body"]),
        ],
    ]


def build():
    s = styles()
    page_w, page_h = letter
    margin = 0.7 * inch
    content_w = page_w - 2 * margin

    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=letter,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        title="RouteOptimizer Executive Summary",
        author="RouteOptimizer",
    )

    story = []

    story.append(Paragraph("ROUTEOPTIMIZER", s["kicker"]))
    story.append(Paragraph("Executive Summary", s["title"]))
    story.append(
        Paragraph(
            "Fleet and route optimization for mining operations - "
            "from research prototype to downloadable software mines can run on their own data.",
            s["subtitle"],
        )
    )
    story.append(AccentBar(content_w))
    story.append(Spacer(1, 6))

    story.append(Paragraph("Opportunity", s["section"]))
    story.append(
        Paragraph(
            "RouteOptimizer is an A-star dispatch simulator and a mixed-integer linear "
            "program (MILP) for haul-fleet planning. Today both solvers lock the route "
            "before they optimize: the interactive path uses a hard-coded toy mine, and "
            "the batch path solves each arc alone. Neither can send a truck a different "
            "way when the shift changes, and two known solver defects can drop a better "
            "route. The planned work turns this into software a mining company can "
            "install, feed with its own haul data, and run on its own machines - with "
            "no commercial solver license and no need to send production data off site.",
            s["body"],
        )
    )

    story.append(Paragraph("What we will build", s["section"]))
    story.append(
        Paragraph(
            "Six epics. Epics 1 and 2 stand alone. Epic 3 needs both. Epic 4 needs Epic 3. "
            "Epic 5 needs Epics 1 and 2 only. Epic 6 ships on Epics 1, 2, and 5 and does "
            "not wait on alternate arcs or replanning.",
            s["body_left"],
        )
    )

    epics = [
        (
            "01",
            "Keep the better route",
            "Fix today's solvers: keep a cheaper waiting assignment, tell two arrival "
            "times of the same fleet apart, and read real arc endpoints in the linear model.",
        ),
        (
            "02",
            "Run both solvers on a mine you specify",
            "One scenario schema feeds the dispatcher and the batch job. Load from the "
            "toy mine, the fleet form, or haul history. Incomplete data is rejected by name.",
        ),
        (
            "03",
            "Send trucks on different arcs",
            "Search considers more than one assignment of a truck class. Cost is travel "
            "time in minutes. A truck stays on its arc until that time is used up.",
        ),
        (
            "04",
            "Replan from where the trucks are",
            "Plan the next k segments from the current fleet, including trucks still in "
            "transit. Replan when a shovel stops, a queue fills, or demand changes.",
        ),
        (
            "05",
            "Produce one shift plan across the mine",
            "Replace per-arc LPs with one flow over the whole mine. Conserve trucks, "
            "respect queue capacity and fleet size, and take tons and shift length from Parameters.",
        ),
        (
            "06",
            "Download and run it at your mine",
            "License, documented scenario file format, pip package and CLI, time-limited "
            "solves, Docker image, and a Hugging Face repository with samples and install links.",
        ),
    ]

    rows = [epic_row(n, t, b, s) for n, t, b in epics]
    table = Table(rows, colWidths=[0.45 * inch, content_w - 0.45 * inch])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (0, -1), 8),
                ("RIGHTPADDING", (1, 0), (1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, 0), (-1, -2), 0.4, RULE),
                ("BACKGROUND", (0, 0), (-1, 0), BAND),
                ("BACKGROUND", (0, 2), (-1, 2), BAND),
                ("BACKGROUND", (0, 4), (-1, 4), BAND),
            ]
        )
    )
    story.append(table)

    story.append(Paragraph("Delivery model", s["section"]))
    story.append(
        Paragraph(
            "This is optimization software, not a trained machine-learning model. "
            "Each mine supplies its scenario and the solvers build a plan locally. "
            "Distribution is a pip package and a Docker image; Hugging Face is the "
            "front door (README, samples, install links), not a place to host weights. "
            "Haul history and tonnage targets stay on the mine's machines.",
            s["body"],
        )
    )

    story.append(Paragraph("Units and inputs", s["section"]))
    unit_data = [
        [
            Paragraph("Input", s["cell_head"]),
            Paragraph("Unit", s["cell_head"]),
            Paragraph("Source", s["cell_head"]),
        ],
        [
            Paragraph("Demand and truck capacity", s["cell"]),
            Paragraph("Tons", s["cell"]),
            Paragraph("Scenario / Parameters", s["cell"]),
        ],
        [
            Paragraph("Shift length", s["cell"]),
            Paragraph("Hours", s["cell"]),
            Paragraph("Scenario / Parameters", s["cell"]),
        ],
        [
            Paragraph("Arc travel time", s["cell"]),
            Paragraph("Minutes", s["cell"]),
            Paragraph("Scenario arcs / haul history", s["cell"]),
        ],
        [
            Paragraph("Locations, arcs, fleet size", s["cell"]),
            Paragraph("Named entities / trucks", s["cell"]),
            Paragraph("Form, fixture, or haul export", s["cell"]),
        ],
    ]
    unit_table = Table(
        unit_data, colWidths=[2.35 * inch, 1.1 * inch, content_w - 3.45 * inch]
    )
    unit_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BAND),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("GRID", (0, 0), (-1, -1), 0.4, RULE),
            ]
        )
    )
    story.append(unit_table)

    story.append(Paragraph("Decisions still required", s["section"]))
    story.append(
        Paragraph(
            "License choice and confirmation of rights with the original authors "
            "(credited in the README). An anonymized sample from real haul history "
            "publishes only with the data owner's approval; until then the toy mine "
            "is the only public sample. Converters for specific fleet-management "
            "systems (MineStar, Wenco, and others) are out of scope for this backlog; "
            "mines convert into the documented scenario format.",
            s["body"],
        )
    )

    def footer(canvas, doc_):
        canvas.saveState()
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.4)
        y = 0.35 * inch
        canvas.line(margin, y + 14, page_w - margin, y + 14)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(
            margin,
            y + 4,
            "Source: _bmad-output/planning-artifacts/epics.md  |  "
            "15 core + 6 distribution stories  |  Confidential planning draft",
        )
        canvas.drawRightString(page_w - margin, y + 4, f"{doc_.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    build()
