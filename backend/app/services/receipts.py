from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors


def build_receipt_pdf(organization, receipt, payment, fee, student) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=22 * mm, leftMargin=22 * mm, topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()
    story = [Paragraph(organization.name, styles["Title"]), Paragraph("Payment receipt", styles["Heading2"]), Spacer(1, 8 * mm)]
    rows = [["Receipt number", receipt.receipt_number], ["Payment date", str(payment.payment_date)], ["Student", f"{student.first_name} {student.last_name}"], ["Billing period", fee.billing_period], ["Fee amount", str(fee.amount_due)], ["Amount paid", str(payment.amount)], ["Payment method", payment.payment_method], ["Reference", payment.transaction_reference or "-"], ["Remaining balance", str(fee.amount_due - payment.amount)]]
    table = Table(rows, colWidths=[55 * mm, 105 * mm])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1eee7")), ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d8d2c6")), ("PADDING", (0, 0), (-1, -1), 8), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold")]))
    story.extend([table, Spacer(1, 14 * mm), Paragraph("Thank you", styles["Normal"])])
    document.build(story)
    return buffer.getvalue()


def generate_receipt_number(db, organization_id, max_retries: int = 5) -> str:
    from datetime import datetime, timezone
    from sqlalchemy import func, select
    from app.models import OrganizationReceiptCounter, Receipt

    current_year = datetime.now(timezone.utc).year
    for attempt in range(max_retries):
        try:
            counter = db.scalar(
                select(OrganizationReceiptCounter)
                .where(
                    OrganizationReceiptCounter.organization_id == organization_id,
                    OrganizationReceiptCounter.year == current_year,
                )
                .with_for_update()
            )
            if counter is None:
                existing_count = db.scalar(
                    select(func.count())
                    .select_from(Receipt)
                    .where(Receipt.organization_id == organization_id)
                ) or 0
                counter = OrganizationReceiptCounter(
                    organization_id=organization_id,
                    year=current_year,
                    last_number=existing_count + 1,
                )
                db.add(counter)
                db.flush()
                next_val = counter.last_number
            else:
                counter.last_number += 1
                db.flush()
                next_val = counter.last_number

            return f"TUIRO-{current_year}-{next_val:06d}"
        except Exception:
            if attempt == max_retries - 1:
                raise