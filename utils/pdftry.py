import io
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import uuid
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER

def generate_invoice_pdf(
    customer_name: str,
    customer_email: str,
    amount: float,
    plan_name: str,
    quantity: float | None = None,
    unit: str | None = None,
    company_name: str = "",
    company_location: str = "",
    company_email: str = "",
    phone_number: str = "",
    *,
    currency: str = "USD",
    invoice_number: str | None = None,
    issue_date: datetime | None = None,
    due_days: int = 7,
    stripe_payment_url: str | None = None,
    output_path: str | None = None,   # None => return bytes; path => write file and return path
) -> bytes | str:
    """
    Generate a single-line-item invoice as PDF.

    Returns:
      - bytes if output_path is None
      - str (file path) if output_path is provided
    """
    def money(x: float | Decimal) -> str:
        q = Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return f"{currency} {q:,.2f}"

    if invoice_number is None:
        invoice_number = f"INV-{uuid.uuid4().hex[:8].upper()}"

    if issue_date is None:
        issue_date = datetime.now()
    due_date = issue_date + timedelta(days=due_days)

    # totals
    if quantity is not None:
        line_qty = quantity
        unit_price = amount
        line_total = (Decimal(str(unit_price)) * Decimal(str(line_qty))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    else:
        line_qty = ""
        unit_price = ""
        line_total = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Build the story
    styles = getSampleStyleSheet()
    normal = styles["BodyText"]
    h3 = styles["Heading3"]
    right = styles["BodyText"].clone("right"); right.alignment = TA_RIGHT
    center = styles["BodyText"].clone("center"); center.alignment = TA_CENTER

    company_info = "<br/>".join([x for x in [company_name, company_location, company_email, phone_number] if x])
    from reportlab.platypus import Table, Paragraph, Spacer, TableStyle

    invoice_meta = [
        ["Invoice #:", invoice_number],
        ["Issue Date:", issue_date.strftime("%Y-%m-%d")],
        ["Due Date:", due_date.strftime("%Y-%m-%d")],
        ["Payment Method:", "Stripe"],
    ]
    invoice_table = Table(invoice_meta, colWidths=[30*mm, 40*mm])
    invoice_table.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ALIGN", (0,0), (-1,-1), "RIGHT"),
        ("LEFTPADDING", (0,0), (-1,-1), 2),
        ("RIGHTPADDING", (0,0), (-1,-1), 2),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))

    header = Table([[Paragraph(company_info, normal), invoice_table]], colWidths=[95*mm, 80*mm])
    header.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP")]))
    data = [
        ["Description", "Qty", "Unit", "Unit Price", "Amount"],
        [plan_name, line_qty, unit or "", money(unit_price) if unit_price != "" else "", money(line_total)],
    ]
    table = Table(data, colWidths=[70*mm, 18*mm, 25*mm, 32*mm, 32*mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f2f2f2")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.black),
        ("ALIGN", (1,1), (-1,-1), "CENTER"),
        ("ALIGN", (3,1), (4,1), "RIGHT"),
        ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#cccccc")),
        ("BOTTOMPADDING", (0,0), (-1,0), 8),
        ("TOPPADDING", (0,0), (-1,0), 8),
        ("BOTTOMPADDING", (0,1), (-1,-1), 6),
        ("TOPPADDING", (0,1), (-1,-1), 6),
    ]))
    totals = Table([["Subtotal", money(line_total)], ["Total", money(line_total)]],
                   colWidths=[125*mm, 52*mm], hAlign="RIGHT")
    totals.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,-1), "Helvetica-Bold"),
        ("ALIGN", (1,0), (1,-1), "RIGHT"),
        ("LINEABOVE", (0,0), (-1,0), 0.3, colors.HexColor("#cccccc")),
        ("LINEABOVE", (0,1), (-1,1), 0.6, colors.HexColor("#000000")),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 6),
    ]))

    story = [header, Spacer(1, 20),
             Paragraph("Bill To", h3),
             Paragraph("<br/>".join([x for x in [customer_name, customer_email] if x]), normal),
             Spacer(1, 12),
             table, Spacer(1, 12),
             totals, Spacer(1, 12)]

    if stripe_payment_url:
        story.append(Paragraph(f'Pay securely via <b>Stripe</b>: <a href="{stripe_payment_url}">{stripe_payment_url}</a>', normal))
    else:
        story.append(Paragraph("Payment via Stripe. (Add a Stripe payment link to embed a clickable button.)", normal))
    story += [Spacer(1, 8),
              Paragraph("Thank you for your business! Please include the invoice number on your payment.", center),
              Spacer(1, 16),
              Paragraph("Terms: Payment due upon receipt unless otherwise stated. Late fees may apply after the due date.",
                        getSampleStyleSheet()["Italic"])]

    if output_path:  # write to disk (legacy behavior)
        doc = SimpleDocTemplate(
            output_path, pagesize=A4,
            rightMargin=18*mm, leftMargin=18*mm, topMargin=16*mm, bottomMargin=16*mm,
            title=f"Invoice {invoice_number}", author=company_name or "Your Company"
        )
        doc.build(story)
        return output_path

    # else: build into memory and return bytes
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=18*mm, leftMargin=18*mm, topMargin=16*mm, bottomMargin=16*mm,
        title=f"Invoice {invoice_number}", author=company_name or "Your Company"
    )
    doc.build(story)
    return buffer.getvalue()

# -------- Example usage --------
if __name__ == "__main__":
    pdf_path = generate_invoice_pdf(
        customer_name="Jane Doe",
        customer_email="jane@example.com",
        amount=49.00,                 # unit price
        plan_name="Pro Plan Subscription",
        quantity=2,
        unit="months",
        company_name="Acme Inc.",
        company_location="123 Market St, Springfield",
        company_email="billing@acme.co",
        phone_number="+1 (555) 010-1234",
        currency="USD",
        stripe_payment_url="https://buy.stripe.com/test_abc123xyz",  # replace with your real link
    )
    print("Invoice saved to:", pdf_path)
