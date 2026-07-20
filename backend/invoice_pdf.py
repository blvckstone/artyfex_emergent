"""GST-compliant tax-invoice PDF generator for ArtyFex.

Generates a single-page A4 invoice matching Indian GST rules:
  - Supplier + Recipient boxes (name / address / GSTIN)
  - Invoice # + Date + Order # + Payment method
  - Line-item table: description, HSN, qty, unit rate, taxable value, CGST/SGST or IGST split
  - Total in words (roman)
  - Bank / signatory placeholder

Usage:
    from invoice_pdf import build_invoice_pdf
    pdf_bytes = build_invoice_pdf(order_doc, business_settings_doc)

The generator is defensive: any missing field falls back to a sensible default,
so it can be called for historical orders that pre-date the GST fields.
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
)

# --- palette (subtle black/gold to match the brand) -------------------------
INK = colors.HexColor("#050505")
GOLD = colors.HexColor("#C9A15A")
LINE = colors.HexColor("#DDDDDD")
LABEL = colors.HexColor("#666666")

# --- number → words (Indian numbering system) -------------------------------
_ONES = [
    "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
    "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen",
    "Sixteen", "Seventeen", "Eighteen", "Nineteen",
]
_TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _two_digit(n: int) -> str:
    if n < 20:
        return _ONES[n]
    return (_TENS[n // 10] + (" " + _ONES[n % 10] if n % 10 else "")).strip()


def _three_digit(n: int) -> str:
    if n < 100:
        return _two_digit(n)
    return f"{_ONES[n // 100]} Hundred" + (" " + _two_digit(n % 100) if n % 100 else "")


def rupees_in_words(rupees: int) -> str:
    """Ex: 12,345 → 'Twelve Thousand Three Hundred Forty Five'.
    Positive integers only; caller is responsible for paise handling."""
    n = int(rupees)
    if n == 0:
        return "Zero"
    parts: List[str] = []
    crore = n // 10_000_000
    n %= 10_000_000
    lakh = n // 100_000
    n %= 100_000
    thousand = n // 1000
    n %= 1000
    if crore:
        parts.append(_two_digit(crore) + " Crore")
    if lakh:
        parts.append(_two_digit(lakh) + " Lakh")
    if thousand:
        parts.append(_two_digit(thousand) + " Thousand")
    if n:
        parts.append(_three_digit(n))
    return " ".join(parts)


def _inr(amount: Any) -> str:
    try:
        v = int(round(float(amount or 0)))
    except Exception:
        v = 0
    # Indian comma grouping
    s = str(abs(v))
    if len(s) > 3:
        head = s[:-3]
        tail = s[-3:]
        parts = []
        while len(head) > 2:
            parts.append(head[-2:])
            head = head[:-2]
        if head:
            parts.append(head)
        s = ",".join(reversed(parts)) + "," + tail
    return ("-" if v < 0 else "") + "\u20B9" + " " + s


def _draw_footer(canvas: Canvas, doc):
    """Small footer with page numbers + generated-at timestamp."""
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(LABEL)
    canvas.drawRightString(A4[0] - 15 * mm, 12 * mm, f"Page {doc.page}")
    canvas.drawString(15 * mm, 12 * mm, f"Generated {datetime.now().strftime('%d %b %Y, %H:%M')}  ·  ArtyFex Atelier")
    canvas.restoreState()


def build_invoice_pdf(order: Dict[str, Any], business: Dict[str, Any]) -> bytes:
    """Return the invoice as raw PDF bytes.

    order    : Order document from Mongo (see backend/server.py Order model).
    business : Settings doc — see backend defaults below.
    """
    buf = io.BytesIO()

    doc = BaseDocTemplate(
        buf, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=20 * mm,
        title=f"ArtyFex Invoice · {order.get('order_number','')}",
        author=business.get("legal_name", "ArtyFex Atelier"),
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates(PageTemplate(id="tp", frames=frame, onPage=_draw_footer))

    styles = getSampleStyleSheet()
    label_st = ParagraphStyle("lbl",  parent=styles["Normal"], fontSize=6.5, textColor=LABEL, spaceAfter=1, leading=8, tracking=1)
    value_st = ParagraphStyle("val",  parent=styles["Normal"], fontSize=9, textColor=INK, leading=12)
    small_st = ParagraphStyle("sm",   parent=styles["Normal"], fontSize=7.5, textColor=INK, leading=10)
    h_st     = ParagraphStyle("h",    parent=styles["Normal"], fontSize=18, textColor=INK, leading=22, spaceAfter=2)
    sub_st   = ParagraphStyle("sub",  parent=styles["Normal"], fontSize=8, textColor=GOLD, leading=10, tracking=2)

    story: List[Any] = []

    # -------- Header row: brand wordmark + Invoice metadata --------
    biz_name = business.get("legal_name") or "ArtyFex Atelier"
    biz_addr = business.get("address") or "Mumbai, Maharashtra, India"
    biz_gstin = business.get("gstin") or "—"
    biz_pan = business.get("pan") or "—"
    biz_state = business.get("state") or "Maharashtra"

    inv_no = order.get("invoice_number") or f"INV-{order.get('order_number', '') }"
    inv_date_iso = order.get("invoice_date") or order.get("created_at") or datetime.now().isoformat()
    try:
        inv_date = datetime.fromisoformat(inv_date_iso.replace("Z", "+00:00")).strftime("%d %b %Y")
    except Exception:
        inv_date = str(inv_date_iso)[:10]

    header = Table(
        [[
            Paragraph(f"<font color='#050505'>{biz_name}</font>", h_st),
            Paragraph("TAX INVOICE", sub_st),
        ], [
            Paragraph(f"{biz_addr}<br/>GSTIN: <b>{biz_gstin}</b> · PAN: {biz_pan} · State: {biz_state}", small_st),
            Paragraph(
                f"<font color='#666'>Invoice No</font><br/><b>{inv_no}</b><br/><br/>"
                f"<font color='#666'>Date</font><br/><b>{inv_date}</b><br/><br/>"
                f"<font color='#666'>Order No</font><br/><b>{order.get('order_number','')}</b>",
                small_st,
            ),
        ]],
        colWidths=[doc.width * 0.6, doc.width * 0.4],
    )
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 1), (-1, 1), 0.6, GOLD),
    ]))
    story.append(header)
    story.append(Spacer(1, 6 * mm))

    # -------- Billed To / Ship To --------
    cust = order.get("customer") or {}
    addr_lines = []
    if cust.get("line1"): addr_lines.append(cust["line1"])
    if cust.get("line2"): addr_lines.append(cust["line2"])
    if cust.get("address") and not cust.get("line1"): addr_lines.append(cust["address"])
    city_state = ", ".join([x for x in [cust.get("city"), cust.get("state"), cust.get("pincode")] if x])
    if city_state: addr_lines.append(city_state)
    if cust.get("country"): addr_lines.append(cust["country"])
    if cust.get("phone"): addr_lines.append(f"Phone: {cust['phone']}")
    if cust.get("email"): addr_lines.append(f"Email: {cust['email']}")

    cust_state = cust.get("state") or ""
    is_intra_state = cust_state.strip().lower() == biz_state.strip().lower()

    bill_ship = Table([[
        Paragraph("BILLED TO / SHIP TO", label_st),
    ], [
        Paragraph(f"<b>{cust.get('name','')}</b><br/>" + "<br/>".join(addr_lines), value_st),
    ]], colWidths=[doc.width])
    bill_ship.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.4, LINE),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F7F5EF")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(bill_ship)
    story.append(Spacer(1, 6 * mm))

    # -------- Line items --------
    items = order.get("items") or []
    header_cells = ["#", "Description", "HSN", "Qty", "Unit ₹", "Taxable ₹"]
    if is_intra_state:
        header_cells += ["CGST", "SGST", "Line Total ₹"]
    else:
        header_cells += ["IGST", "", "Line Total ₹"]

    rows: List[List[Any]] = [header_cells]

    # We use gst_lines from the order (server-computed) so numbers match the receipt EXACTLY.
    gst_lines = {
        (gl.get("product_id"), gl.get("variant_key")): gl
        for gl in (order.get("gst_lines") or [])
        if gl.get("product_id")
    }
    for idx, it in enumerate(items, start=1):
        gl = gst_lines.get((it.get("product_id"), it.get("variant_key"))) or {}
        qty = int(it.get("quantity") or 1)
        unit_price = int(it.get("price_inr") or 0)
        taxable = int(gl.get("taxable_inr") or (unit_price * qty))
        cgst = int(gl.get("cgst_inr") or 0)
        sgst = int(gl.get("sgst_inr") or 0)
        igst = int(gl.get("igst_inr") or 0)
        line_total = taxable + cgst + sgst + igst

        desc = it.get("product_name") or ""
        details_bits = []
        if it.get("variant_label"): details_bits.append(it["variant_label"])
        if it.get("size"): details_bits.append(f"Size: {it['size']}")
        for k, v in (it.get("selected_options_labels") or {}).items():
            details_bits.append(f"{k}: {v}")
        if details_bits:
            desc += f"<br/><font size=7 color='#666'>" + " · ".join(details_bits) + "</font>"
        if it.get("product_sku"):
            desc += f"<br/><font size=7 color='#666'>SKU: {it['product_sku']}</font>"

        row = [
            str(idx),
            Paragraph(desc, small_st),
            it.get("product_hsn_code") or "—",
            str(qty),
            _inr(unit_price),
            _inr(taxable),
        ]
        if is_intra_state:
            row += [_inr(cgst), _inr(sgst), _inr(line_total)]
        else:
            row += [_inr(igst), "", _inr(line_total)]
        rows.append(row)

    lt = Table(rows, colWidths=[
        10 * mm, 55 * mm, 15 * mm, 10 * mm, 18 * mm, 20 * mm, 18 * mm, 18 * mm, 26 * mm,
    ], repeatRows=1)
    lt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7.5),
        ("ALIGN", (0, 0), (-1, 0), "LEFT"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 1), (0, -1), "CENTER"),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(lt)
    story.append(Spacer(1, 4 * mm))

    # -------- Totals block --------
    subtotal = int(order.get("subtotal_inr") or 0)
    shipping = int(order.get("shipping_inr") or 0)
    discount = int(order.get("discount_inr") or 0)
    cgst_total = int(order.get("cgst_inr") or 0)
    sgst_total = int(order.get("sgst_inr") or 0)
    igst_total = int(order.get("igst_inr") or 0)
    gst_total = int(order.get("gst_total_inr") or 0)
    grand_total = int(order.get("total_inr") or 0)

    totals_rows = [
        ["Subtotal (Taxable)", _inr(subtotal)],
    ]
    if discount:
        totals_rows.append(["Discount", "− " + _inr(discount)])
    if shipping:
        totals_rows.append(["Shipping", _inr(shipping)])
    if is_intra_state:
        totals_rows.append(["CGST", _inr(cgst_total)])
        totals_rows.append(["SGST", _inr(sgst_total)])
    else:
        totals_rows.append(["IGST", _inr(igst_total)])
    if not (cgst_total or sgst_total or igst_total) and gst_total:
        totals_rows.append(["GST", _inr(gst_total)])
    totals_rows.append(["Grand Total (INR)", _inr(grand_total)])

    tt = Table(totals_rows, colWidths=[45 * mm, 35 * mm], hAlign="RIGHT")
    tt.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONT", (0, 0), (-1, -2), "Helvetica", 9),
        ("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 11),
        ("TEXTCOLOR", (0, -1), (-1, -1), INK),
        ("LINEABOVE", (0, -1), (-1, -1), 0.6, GOLD),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(tt)
    story.append(Spacer(1, 4 * mm))

    # In-words
    story.append(Paragraph(
        f"<font color='#666'>Amount in words:</font> <b>Rupees {rupees_in_words(grand_total)} Only</b>",
        small_st,
    ))
    story.append(Spacer(1, 6 * mm))

    # -------- Notes / T&C / Signatory --------
    payment_bits = []
    if order.get("payment_method"): payment_bits.append(f"Payment: <b>{order['payment_method'].upper()}</b>")
    if order.get("razorpay_payment_id"): payment_bits.append(f"Txn ID: {order['razorpay_payment_id']}")
    if order.get("razorpay_order_id"): payment_bits.append(f"Razorpay Order: {order['razorpay_order_id']}")

    treatment_note = ""
    if order.get("gst_treatment") == "exclusive":
        treatment_note = "GST is charged in addition to the listed price (exclusive treatment)."
    elif order.get("gst_treatment") == "inclusive":
        treatment_note = "Listed prices are inclusive of GST (inclusive treatment)."

    notes = Paragraph(
        (
            "<b>Notes:</b><br/>"
            + (treatment_note + "<br/>" if treatment_note else "")
            + ("<br/>".join(payment_bits) + "<br/>" if payment_bits else "")
            + "This is a system-generated tax invoice under section 31 of the CGST Act, 2017 and does not require a physical signature."
        ),
        small_st,
    )

    sig_cell = Paragraph(
        f"<br/><br/><b>For {biz_name}</b><br/><br/><br/>"
        f"<font color='#666'>Authorised Signatory</font>",
        small_st,
    )

    fb = Table([[notes, sig_cell]], colWidths=[doc.width * 0.65, doc.width * 0.35])
    fb.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(fb)

    doc.build(story)
    return buf.getvalue()
