# app/billing/emailer.py
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
import mimetypes
import smtplib
from typing import Optional
from decimal import Decimal, ROUND_HALF_UP
from html import escape as html_escape
import os, ssl, mimetypes
# Email sender information
# SMTP_HOST = os.getenv("SMTP_HOST", "smtp.sendgrid.net")
# SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
# SMTP_USER = os.getenv("SMTP_USER", "")
# SMTP_PASS = os.getenv("SMTP_PASS", "")
# FROM_NAME = os.getenv("INVOICES_FROM_NAME", "Neogenxai Billing")
# FROM_EMAIL = os.getenv("INVOICES_FROM_EMAIL", "billing@neogenxai.com")
# REPLY_TO  = os.getenv("INVOICES_REPLY_TO", "support@neogenxai.com")
SMTP_HOST = "mail.neogenxai.com"
SMTP_PORT = 465
SMTP_USER = "aprajapati@neogenxai.com"
SMTP_PASS = "aprajapati1"
FROM_NAME = "Neogenxai Pvt. Ltd."
FROM_EMAIL = "aprajapati@neogenxai.com"
REPLY_TO  = "support@neogenxai.com"



ZERO_DECIMAL = {"BIF","CLP","DJF","GNF","JPY","KMF","KRW","MGA","PYG","RWF","UGX","VND","VUV","XAF","XOF","XPF"}

def _fmt_money(amount_major: float | Decimal, currency: str) -> str:
    """Format a major-unit amount like the PDF (2dp; zero-decimal stays .00 for consistency)."""
    c = currency.upper()
    q = Decimal(str(amount_major)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{c} {q:,.2f}"

def build_invoice_html(
    *,
    customer_name: str,
    customer_email: str,
    plan_name: str,
    currency: str,
    amount: float,
    quantity: float | None = None,
    unit: str | None = None,
    invoice_number: str,
    issue_date_yyyy_mm_dd: str,
    due_date_yyyy_mm_dd: str | None = None,
    receipt_url: str | None = None,
    company_name: str = "Neogenxai Pvt. Ltd.",
    company_location: str = "Bhaktapur, Nepal",
    company_email: str = "itadmin@neogenxai.com",
    phone_number: str = "+977 9762656555",
) -> str:
    """
    HTML invoice that mirrors the PDF's fields/structure.

    Table columns:
      Description | Qty | Unit | Unit Price | Amount
    Totals:
      Subtotal, Total (no taxes/discounts, like the PDF)
    """

    if quantity is not None:
        unit_price_major = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        line_total_major = (Decimal(str(amount)) * Decimal(str(quantity))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        qty_display = f"{quantity:g}"  # compact (e.g., 2, 2.5)
        unit_display = (unit or "").strip()
        unit_price_display = _fmt_money(unit_price_major, currency)
        amount_display = _fmt_money(line_total_major, currency)
        subtotal_display = amount_display
        total_display = amount_display
    else:
        # No quantity => amount is the total; leave qty/unit/unit price blank
        line_total_major = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        qty_display = ""
        unit_display = ""
        unit_price_display = ""
        amount_display = _fmt_money(line_total_major, currency)
        subtotal_display = amount_display
        total_display = amount_display

    # Invoice meta rows (Issue/Due dates + Payment Method)
    due_row = f"""
      <tr>
        <td style="padding:6px 8px;color:#555;">Due Date:</td>
        <td style="padding:6px 8px;" align="right">{html_escape(due_date_yyyy_mm_dd or issue_date_yyyy_mm_dd)}</td>
      </tr>
    """

    # CTA
    cta_html = ""
    if receipt_url:
        cta_html = f"""
          <p style="margin:16px 0;">
            <a href="{html_escape(receipt_url)}"
               style="background:#635bff;color:#fff;padding:12px 18px;border-radius:6px;text-decoration:none;display:inline-block;">
               View Stripe Receipt
            </a>
          </p>
        """

    preheader = f"Invoice {invoice_number} · {total_display}"

    return f"""\
<!DOCTYPE html>
<html>
  <body style="margin:0;padding:0;background:#f6f9fc;font-family:Arial,Helvetica,sans-serif;">
    <span style="display:none!important;visibility:hidden;opacity:0;color:transparent;height:0;width:0;overflow:hidden;">
      {html_escape(preheader)}
    </span>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f6f9fc;padding:24px 0;">
      <tr>
        <td align="center">
          <table role="presentation" width="620" cellpadding="0" cellspacing="0"
                 style="background:#ffffff;border-radius:10px;padding:24px;box-shadow:0 2px 8px rgba(0,0,0,.05);">
            <!-- Header block: company info (left) + invoice meta (right) -->
            <tr>
              <td style="font-size:16px;line-height:1.5;color:#111;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                  <tr>
                    <td valign="top" style="width:60%;padding-right:8px;">
                      <p style="margin:0 0 4px 0;"><strong>{html_escape(company_name)}</strong></p>
                      <p style="margin:0 0 4px 0;color:#555;">{html_escape(company_location)}</p>
                      <p style="margin:0 0 4px 0;color:#555;">{html_escape(company_email)} · {html_escape(phone_number)}</p>
                    </td>
                    <td valign="top" style="width:40%;">
                      <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                             style="border-collapse:collapse;">
                        <tr>
                          <td style="padding:6px 8px;color:#555;">Invoice #:</td>
                          <td style="padding:6px 8px;" align="right">{html_escape(invoice_number)}</td>
                        </tr>
                        <tr>
                          <td style="padding:6px 8px;color:#555;">Issue Date:</td>
                          <td style="padding:6px 8px;" align="right">{html_escape(issue_date_yyyy_mm_dd)}</td>
                        </tr>
                        {due_row}
                        <tr>
                          <td style="padding:6px 8px;color:#555;">Payment Method:</td>
                          <td style="padding:6px 8px;" align="right">Stripe</td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>

                <!-- Bill To -->
                <h3 style="margin:20px 0 8px 0;">Bill To</h3>
                <p style="margin:0 0 16px 0;color:#111;">
                  {html_escape(customer_name or "Customer")}<br/>
                  {html_escape(customer_email or "")}
                </p>

                <!-- Line Items table -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                       style="border:1px solid #eee;border-radius:8px;overflow:hidden;">
                  <tr style="background:#f2f2f2;">
                    <th align="left"  style="padding:10px 12px;font-weight:600;">Description</th>
                    <th align="center" style="padding:10px 12px;font-weight:600;">Qty</th>
                    <th align="center" style="padding:10px 12px;font-weight:600;">Unit</th>
                    <th align="right" style="padding:10px 12px;font-weight:600;">Unit Price</th>
                    <th align="right" style="padding:10px 12px;font-weight:600;">Amount</th>
                  </tr>
                  <tr>
                    <td style="padding:10px 12px;border-top:1px solid #eee;">{html_escape(plan_name)}</td>
                    <td align="center" style="padding:10px 12px;border-top:1px solid #eee;">{html_escape(qty_display)}</td>
                    <td align="center" style="padding:10px 12px;border-top:1px solid #eee;">{html_escape(unit_display)}</td>
                    <td align="right" style="padding:10px 12px;border-top:1px solid #eee;">{html_escape(unit_price_display)}</td>
                    <td align="right" style="padding:10px 12px;border-top:1px solid #eee;">{html_escape(amount_display)}</td>
                  </tr>
                </table>

                <!-- Totals -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:12px;">
                  <tr>
                    <td style="width:50%"></td>
                    <td style="width:50%">
                      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
                        <tr>
                          <td style="padding:8px 12px;font-weight:600;">Subtotal</td>
                          <td align="right" style="padding:8px 12px;font-weight:600;">{html_escape(subtotal_display)}</td>
                        </tr>
                        <tr>
                          <td style="padding:8px 12px;border-top:1px solid #111;font-weight:700;">Total</td>
                          <td align="right" style="padding:8px 12px;border-top:1px solid #111;font-weight:700;">{html_escape(total_display)}</td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>

                <!-- Stripe receipt link (optional) -->
                {cta_html}

                <!-- Footer notes (terms) -->
                <p style="margin:16px 0 0 0;color:#666;font-size:14px;text-align:center;">
                  Thank you for your business! Please include the invoice number on your payment.
                </p>
                <p style="margin:8px 0 0 0;color:#777;font-size:12px;text-align:center;">
                  Terms: Payment due upon receipt unless otherwise stated. Late fees may apply after the due date.
                </p>
              </td>
            </tr>
          </table>

          <p style="color:#9aa0a6;font-size:12px;margin:12px 0 0 0;">
            You’re receiving this because you made a purchase from {html_escape(company_name)}.
          </p>
        </td>
      </tr>
    </table>
  </body>
</html>
"""
# ---- replace your send_invoice_email with this version ----
def send_invoice_email(
    *,
    to_email: str,
    subject: str,
    html_body: str,
    pdf_path: Optional[str] = None,            # existing behavior
    pdf_bytes: Optional[bytes] = None,         # NEW: in-memory PDF
    pdf_filename: str = "invoice.pdf",         # NEW: filename when using bytes
    from_name: Optional[str] = None,
    from_email: Optional[str] = None,
    reply_to: Optional[str] = None,
) -> None:
    sender_name = from_name or FROM_NAME
    sender_email = from_email or FROM_EMAIL
    reply_to_email = reply_to or REPLY_TO

    # Keep domain alignment if the SMTP provider enforces it
    if SMTP_USER and sender_email.split("@")[-1].lower() != SMTP_USER.split("@")[-1].lower():
        sender_email = SMTP_USER

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((sender_name, sender_email))
    msg["To"] = to_email
    if reply_to_email:
        msg["Reply-To"] = reply_to_email
    msg["Message-ID"] = make_msgid(domain=sender_email.split("@")[-1])

    msg.set_content("Your invoice is attached as a PDF.")
    msg.add_alternative(html_body, subtype="html")

    # --- Attach PDF (bytes preferred, file path fallback) ---
    if pdf_bytes is not None:
        msg.add_attachment(
            pdf_bytes,
            maintype="application",
            subtype="pdf",
            filename=pdf_filename,
        )
    elif pdf_path:
        ctype, encoding = mimetypes.guess_type(pdf_path)
        if ctype is None or encoding is not None:
            ctype = "application/pdf"
        maintype, subtype = ctype.split("/", 1)
        with open(pdf_path, "rb") as f:
            msg.add_attachment(
                f.read(), maintype=maintype, subtype=subtype,
                filename=os.path.basename(pdf_path),
            )

    ctx = ssl.create_default_context()

    if SMTP_PORT == 465:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx, timeout=60) as server:
            server.set_debuglevel(1)  # set 0 to silence
            server.ehlo()
            if SMTP_USER:
                server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
    elif SMTP_PORT == 587:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=60) as server:
            server.set_debuglevel(1)
            server.ehlo()
            server.starttls(context=ctx)
            server.ehlo()
            if SMTP_USER:
                server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
    else:
        raise RuntimeError(f"Unsupported SMTP_PORT {SMTP_PORT}: use 465 (SSL) or 587 (STARTTLS)")

if __name__ == "__main__":
    import argparse
    import os
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo

    # Optional: import your PDF generator
    try:
        from pdftry import generate_invoice_pdf
    except Exception:
        generate_invoice_pdf = None  # If not available, --make-pdf will be disabled.

    parser = argparse.ArgumentParser(
        description="Send a test invoice email (HTML + optional PDF attachment) via SMTP."
    )
    parser.add_argument("--to", required=True, help="Mukesh email")
    parser.add_argument("--customer-name", default="Test Customer")
    parser.add_argument("--customer-email", default="mukeshpr443@example.com")
    parser.add_argument("--plan-name", default="Pro Plan Subscription")
    parser.add_argument("--currency", default="USD")
    parser.add_argument(
        "--amount",
        type=float,
        default=49.0,
        help="Major-unit amount. If --quantity is provided, this is the UNIT PRICE; otherwise it's the TOTAL.",
    )
    parser.add_argument("--quantity", type=float, default=None, help="Optional quantity")
    parser.add_argument("--unit", default=None, help='Optional unit label, e.g. "months", "seats"')
    parser.add_argument("--invoice-number", default=None, help="Override invoice number")
    parser.add_argument("--receipt-url", default=None, help="Optional Stripe receipt URL")
    parser.add_argument("--make-pdf", action="store_true", help="Generate and attach a PDF via generate_invoice_pdf")
    parser.add_argument("--pdf-outdir", default="invoices", help="Directory to write the PDF (default: invoices)")
    parser.add_argument(
        "--subject",
        default=None,
        help="Email subject. Defaults to 'Your Invoice <#> · <TOTAL>'.",
    )

    args = parser.parse_args()

    # Company defaults (can be overriden via env if you want)
    company_name = os.getenv("INVOICE_COMPANY_NAME", "Neogenxai Pvt. Ltd.")
    company_location = os.getenv("INVOICE_COMPANY_LOCATION", "Bhaktapur, Nepal")
    company_email = os.getenv("INVOICE_COMPANY_EMAIL", "itadmin@neogenxai.com")
    phone_number = os.getenv("INVOICE_COMPANY_PHONE", "+977 9762656555")

    # Dates: mimic your webhook (Kathmandu local, due today by default)
    issue_dt_local = datetime.now(ZoneInfo("Asia/Kathmandu"))
    issue_date_str = issue_dt_local.strftime("%Y-%m-%d")
    due_date_str = issue_date_str  # due_days=0 in your PDF

    # Invoice number
    inv_number = args.invoice_number or f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Build HTML body using the same semantics as your PDF:
    # - If quantity is provided => amount is unit price, total = amount * quantity
    # - If quantity is None     => amount is total, unit price left blank
    html_body = build_invoice_html(
        customer_name=args.customer_name,
        customer_email=args.customer_email,
        plan_name=args.plan_name,
        currency=args.currency,
        amount=float(args.amount),
        quantity=args.quantity,
        unit=args.unit,
        invoice_number=inv_number,
        issue_date_yyyy_mm_dd=issue_date_str,
        due_date_yyyy_mm_dd=due_date_str,
        receipt_url=args.receipt_url,
        company_name=company_name,
        company_location=company_location,
        company_email=company_email,
        phone_number=phone_number,
    )

    # Optionally generate a PDF to attach
    pdf_path = None
    if args.make_pdf:
        if generate_invoice_pdf is None:
            raise RuntimeError(
                "generate_invoice_pdf is not importable. Ensure app/billing/invoices.py exists and is on PYTHONPATH."
            )
        os.makedirs(args.pdf_outdir, exist_ok=True)
        out_path = os.path.join(args.pdf_outdir, f"invoice_{inv_number}.pdf")
        pdf_path = generate_invoice_pdf(
            customer_name=args.customer_name,
            customer_email=args.customer_email,
            amount=float(args.amount),
            plan_name=args.plan_name,
            quantity=args.quantity,
            unit=args.unit,
            company_name=company_name,
            company_location=company_location,
            company_email=company_email,
            phone_number=phone_number,
            currency=args.currency,
            invoice_number=inv_number,
            issue_date=issue_dt_local.replace(tzinfo=None),  # your PDF expects naive
            due_days=0,
            stripe_payment_url=args.receipt_url,
            output_path=out_path,
        )
        print(f"🧾 PDF generated at: {pdf_path}")

    # Subject: mirror the PDF total in the subject line
    # Compute display total the same way as the HTML/PDF:
    from decimal import Decimal, ROUND_HALF_UP
    def _fmt_money(amount_major: float | Decimal, currency: str) -> str:
        q = Decimal(str(amount_major)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return f"{currency.upper()} {q:,.2f}"

    if args.quantity is not None:
        total_major = Decimal(str(args.amount)) * Decimal(str(args.quantity))
    else:
        total_major = Decimal(str(args.amount))
    total_display = _fmt_money(total_major, args.currency)

    subject = args.subject or f"Your Invoice {inv_number} · {total_display}"

    print("📧 Sending email...")
    send_invoice_email(
        to_email=args.to,
        subject=subject,
        html_body=html_body,
        pdf_path=pdf_path,
    )
    print(f"✅ Sent to {args.to}")
