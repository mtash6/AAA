"""
PDF Report Generator Engine
Produces executive-ready financial reports with two-pass page numbering,
financial alignment standards, KPI summary metrics, and corporate styling.
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, 
    Paragraph, 
    Spacer, 
    Table, 
    TableStyle, 
    HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from services.exceptions import TEAMAIException, ValidationException

logger = logging.getLogger("TEAM_AI.PDFReportGenerator")


# ============================================================================
# 1. DATA SCHEMA & CONTRACT
# ============================================================================

class ExecutiveFinancialData(BaseModel):
    gross_income: float = Field(0.0, ge=0.0, description="Total gross revenue in USD")
    total_expenses: float = Field(0.0, ge=0.0, description="Total operating expenses in USD")
    net_profit: float = Field(0.0, description="Calculated net profit in USD")
    vat_liability: float = Field(0.0, ge=0.0, description="14% VAT liability")
    corporate_tax_liability: float = Field(0.0, ge=0.0, description="Corporate income tax liability")
    total_tax_due: float = Field(0.0, ge=0.0, description="Combined tax obligations")
    company_name: str = Field("AAA ADVANCE AMERICAN AGENCY", description="Entity name")
    generated_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%B %d, %Y")
    )


# ============================================================================
# 2. TWO-PASS CANVAS FOR Dynamic "PAGE X OF Y"
# ============================================================================

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas recorder to dynamically calculate total page counts
    and inject running headers/footers across multi-page documents.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor('#718096'))

        # Running Header
        self.drawString(54, 11 * inch - 36, "AAA ADVANCE AMERICAN AGENCY — EXECUTIVE FINANCIAL REPORT")
        self.setStrokeColor(colors.HexColor('#E2E8F0'))
        self.setLineWidth(0.75)
        self.line(54, 11 * inch - 42, 8.5 * inch - 54, 11 * inch - 42)

        # Running Footer
        self.setFont("Helvetica", 8)
        self.drawString(54, 36, "CONFIDENTIAL & PROPRIETARY — FOR MANAGEMENT USE ONLY")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * inch - 54, 36, page_str)
        self.line(54, 48, 8.5 * inch - 54, 48)

        self.restoreState()


# ============================================================================
# 3. PDF REPORT GENERATOR SERVICE
# ============================================================================

class PDFReportGenerator:
    """
    High-performance ReportLab PDF generation service.
    """

    @classmethod
    def generate_executive_financial_pdf(cls, data: Dict[str, Any], filepath: str) -> str:
        """
        Generates an executive-ready financial PDF report.
        """
        # 1. Validate Input Data
        try:
            payload = ExecutiveFinancialData(**data)
        except Exception as ve:
            logger.error(f"Payload validation failed for PDF generation: {ve}")
            raise ValidationException(f"Invalid financial report data: {str(ve)}")

        # 2. Safe Directory Creation (Fixes crash on relative filepaths)
        target_dir = os.path.dirname(filepath)
        if target_dir:
            os.makedirs(target_dir, exist_ok=True)

        try:
            # Document Setup with standard margins
            doc = SimpleDocTemplate(
                filepath,
                pagesize=letter,
                leftMargin=54,
                rightMargin=54,
                topMargin=54,
                bottomMargin=54
            )

            story = []
            styles = getSampleStyleSheet()

            # Custom Style Definitions
            title_style = ParagraphStyle(
                'DocTitle',
                parent=styles['Heading1'],
                fontName='Helvetica-Bold',
                fontSize=20,
                leading=24,
                textColor=colors.HexColor('#1A365D'),
                spaceAfter=4
            )

            subtitle_style = ParagraphStyle(
                'DocSubtitle',
                parent=styles['Normal'],
                fontName='Helvetica',
                fontSize=10,
                leading=12,
                textColor=colors.HexColor('#4A5568'),
                spaceAfter=15
            )

            card_label_style = ParagraphStyle(
                'CardLabel',
                fontName='Helvetica-Bold',
                fontSize=9,
                leading=10,
                textColor=colors.HexColor('#718096'),
                alignment=1 # Center
            )

            card_val_style = ParagraphStyle(
                'CardValue',
                fontName='Helvetica-Bold',
                fontSize=14,
                leading=16,
                textColor=colors.HexColor('#1A365D'),
                alignment=1 # Center
            )

            cell_left = ParagraphStyle(
                'CellLeft',
                fontName='Helvetica',
                fontSize=10,
                leading=12,
                textColor=colors.HexColor('#2D3748')
            )

            cell_right = ParagraphStyle(
                'CellRight',
                fontName='Helvetica',
                fontSize=10,
                leading=12,
                textColor=colors.HexColor('#2D3748'),
                alignment=2 # Right align
            )

            cell_right_bold = ParagraphStyle(
                'CellRightBold',
                parent=cell_right,
                fontName='Helvetica-Bold',
                textColor=colors.HexColor('#1A365D')
            )

            # ----------------------------------------------------------------
            # HEADER SECTION
            # ----------------------------------------------------------------
            story.append(Paragraph(payload.company_name, title_style))
            story.append(Paragraph(f"Executive Financial Performance Statement | Date: {payload.generated_at}", subtitle_style))
            story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2B6CB0'), spaceAfter=15))

            # ----------------------------------------------------------------
            # KPI SUMMARY CARDS
            # ----------------------------------------------------------------
            kpi_data = [
                [
                    Paragraph("GROSS REVENUE", card_label_style),
                    Paragraph("NET PROFIT", card_label_style),
                    Paragraph("TOTAL TAX DUE", card_label_style)
                ],
                [
                    Paragraph(f"${payload.gross_income:,.2f}", card_val_style),
                    Paragraph(f"${payload.net_profit:,.2f}", card_val_style),
                    Paragraph(f"${payload.total_tax_due:,.2f}", card_val_style)
                ]
            ]
            kpi_table = Table(kpi_data, colWidths=[168, 168, 168])
            kpi_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F7FAFC')),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
                ('INNERGRID', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(kpi_table)
            story.append(Spacer(1, 20))

            # ----------------------------------------------------------------
            # DETAILED FINANCIAL AUDIT TABLE
            # ----------------------------------------------------------------
            table_rows = [
                [
                    Paragraph("<b>Financial Indicator</b>", cell_left), 
                    Paragraph("<b>Amount ($USD)</b>", cell_right_bold)
                ],
                [Paragraph("Gross Revenue", cell_left), Paragraph(f"${payload.gross_income:,.2f}", cell_right)],
                [Paragraph("Total Expenses", cell_left), Paragraph(f"${payload.total_expenses:,.2f}", cell_right)],
                [Paragraph("<b>Net Operating Profit</b>", cell_left), Paragraph(f"<b>${payload.net_profit:,.2f}</b>", cell_right_bold)],
                [Paragraph("VAT Liability (14%)", cell_left), Paragraph(f"${payload.vat_liability:,.2f}", cell_right)],
                [Paragraph("Corporate Tax Liability", cell_left), Paragraph(f"${payload.corporate_tax_liability:,.2f}", cell_right)],
                [Paragraph("<b>Total Tax Obligation</b>", cell_left), Paragraph(f"<b>${payload.total_tax_due:,.2f}</b>", cell_right_bold)]
            ]

            fin_table = Table(table_rows, colWidths=[304, 200])
            fin_table.setStyle(TableStyle([
                # Header Styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2B6CB0')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                # Alternate Row Colors
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F7FAFC')]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E0')),
                ('PADDING', (0, 0), (-1, -1), 8),
                # Highlight Key Rows (Net Profit & Total Tax)
                ('LINEBELOW', (0, 3), (1, 3), 1.5, colors.HexColor('#2B6CB0')),
                ('LINEBELOW', (0, 6), (1, 6), 1.5, colors.HexColor('#2B6CB0')),
            ]))

            story.append(fin_table)

            # 3. Build Document using Two-Pass Canvas
            doc.build(story, canvasmaker=NumberedCanvas)
            logger.info(f"Successfully compiled PDF report: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"PDF compilation failed for {filepath}: {str(e)}", exc_info=True)
            raise TEAMAIException(f"PDF Generation Error: {str(e)}")
