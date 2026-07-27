import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


class PDFReportGenerator:
    @staticmethod
    def generate_executive_financial_pdf(data: dict, filepath: str) -> str:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor('#1a365d'))
        story.append(Paragraph("TRIPLE A ENTERPRISE MANAGEMENT SYSTEM", title_style))
        story.append(Paragraph("Executive Financial Performance Report", styles['Heading2']))
        story.append(Spacer(1, 15))

        table_data = [
            ["Financial Indicator", "Amount ($USD)"],
            ["Gross Revenue", f"${data.get('gross_income', 0):,.2f}"],
            ["Total Expenses", f"${data.get('total_expenses', 0):,.2f}"],
            ["Net Profit", f"${data.get('net_profit', 0):,.2f}"],
            ["VAT Liability (14%)", f"${data.get('vat_liability', 0):,.2f}"],
            ["Corporate Tax Liability", f"${data.get('corporate_tax_liability', 0):,.2f}"],
            ["Total Tax Due", f"${data.get('total_tax_due', 0):,.2f}"]
        ]

        t = Table(table_data, colWidths=[250, 200])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#2b6cb0')),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafc')]),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(t)
        doc.build(story)
        return filepath