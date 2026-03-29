"""
PDF generation service for ClinicOS.
Generates Individual Visit Sign Sheet (printable patient record).
Uses fpdf2 (pure Python, pip install fpdf2).
All text is ASCII/latin-1 safe so Helvetica built-in font works.

Layout matches clinic's paper sign sheet:
  # | Date | Service | W | D | Signature (blank line) | CC | Note
No insurance block — keeps the sheet clean for patient signing.
"""
from __future__ import annotations
from datetime import datetime, timezone


def _today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _fmt_dt(iso, fmt="%m/%d/%Y %H:%M"):
    if not iso:
        return "-"
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return dt.strftime(fmt)
    except Exception:
        return str(iso)[:16]


def _money(val):
    if val is None:
        return "-"
    try:
        return "$%.2f" % float(val)
    except Exception:
        return "-"


def generate_sign_sheet(patient, visits, policies):
    """Generate individual sign sheet PDF. Returns raw PDF bytes."""
    try:
        from fpdf import FPDF
    except ImportError:
        raise RuntimeError("fpdf2 not installed. Run: pip install fpdf2")

    pdf = FPDF(orientation="P", unit="mm", format="Letter")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ---- Title ----
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "Individual Visit Sign Sheet", ln=True, align="C")
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(0, 4, "Printed: " + _today(), ln=True, align="C")
    pdf.ln(4)

    # ---- Patient Info (compact bordered block, no insurance) ----
    first = str(patient.get("first_name") or "")
    last  = str(patient.get("last_name") or "")
    full  = str(patient.get("full_name") or (first + " " + last).strip())
    dob   = str(patient.get("date_of_birth") or "-")
    mrn   = str(patient.get("mrn") or "-")
    ph    = str(patient.get("phone") or "-")

    # Pull primary insurance copay for header summary
    copay_label = "-"
    carrier_label = ""
    if policies:
        pri = next((p for p in policies if str(p.get("priority") or "").lower() == "primary"), policies[0])
        copay_label   = _money(pri.get("copay_amount"))
        carrier_label = str(pri.get("carrier_name") or "")

    pdf.set_fill_color(235, 235, 235)
    pdf.set_draw_color(140, 140, 140)

    # Name row — full width, bold
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "  " + full, border=1, fill=True, ln=True)

    # Detail row
    col = 63.3  # 190 / 3
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(col, 6, "  MRN: " + mrn,   border="LRB")
    pdf.cell(col, 6, "  DOB: " + dob,   border="RB")
    pdf.cell(col, 6, "  Phone: " + ph,  border="RB", ln=True)

    # Insurance summary row
    ins_text = "  Insurance: " + (carrier_label if carrier_label else "-")
    pdf.cell(col * 2, 6, ins_text,                border="LRB")
    pdf.cell(col,     6, "  Co-Pay: " + copay_label, border="RB", ln=True)

    pdf.ln(6)

    # ---- Visit Table ----
    # Columns (mm, total 190):
    #   #=8  Date=26  Service=30  W=8  D=8  Signature=56  CC=20  Note=34
    W       = [8, 26, 30, 8, 8, 56, 20, 34]
    HEADERS = ["#", "Date", "Service", "W", "D", "Signature", "CC", "Note"]

    pdf.set_fill_color(190, 210, 190)
    pdf.set_draw_color(100, 130, 100)
    pdf.set_font("Helvetica", "B", 8.5)
    for i, h in enumerate(HEADERS):
        pdf.cell(W[i], 7, h, border=1, fill=True, align="C")
    pdf.ln()

    ROW_H = 9   # tall enough to write a real signature

    # Insurance copay amount to pre-fill expected copay on unchecked-out rows
    ins_copay_amount = None
    if policies:
        pri = next((p for p in policies if str(p.get("priority") or "").lower() == "primary"), policies[0])
        ins_copay_amount = pri.get("copay_amount")

    # Expand visits: one row per treatment (or one row per visit if no treatments)
    rows = []
    for v in visits:
        status   = str(v.get("status") or "")
        date_str = _fmt_dt(v.get("check_in_time"), "%m/%d/%y")
        w_val    = "v" if (status == "checked_out" and v.get("wd_verified")) else ""
        if status == "checked_out":
            cc_val = _money(v.get("copay_collected"))
        elif ins_copay_amount:
            cc_val = _money(ins_copay_amount)  # expected copay from insurance
        else:
            cc_val = ""

        treatments = v.get("treatments") or []
        if treatments:
            for ti, t in enumerate(treatments):
                mod = str(t.get("modality") or "-")
                dur = t.get("duration_minutes")
                svc_cell = (mod + " (" + str(dur) + "m)")[:20] if dur else mod[:20]
                # CC only on first treatment row of the visit; W only on last
                rows.append({
                    "date": date_str,
                    "svc": svc_cell,
                    "w": w_val if ti == len(treatments) - 1 else "",
                    "cc": cc_val if ti == 0 else "",
                    "visit": v,
                })
        else:
            # No explicit treatments — show service_type from ServiceStart
            svc_type = str(v.get("service_type") or "-")[:20]
            rows.append({"date": date_str, "svc": svc_type, "w": w_val, "cc": cc_val, "visit": v})

    alt = False
    for idx, row in enumerate(rows, 1):
        if alt:
            pdf.set_fill_color(246, 252, 246)
        else:
            pdf.set_fill_color(255, 255, 255)
        alt = not alt

        pdf.set_draw_color(150, 150, 150)
        pdf.set_font("Helvetica", "", 8)
        cells  = [str(idx), row["date"], row["svc"], row["w"], "", "", row["cc"], ""]
        aligns = ["C", "C", "L", "C", "C", "L", "C", "L"]
        for i, cell in enumerate(cells):
            pdf.cell(W[i], ROW_H, cell, border=1, fill=True, align=aligns[i])
        pdf.ln()

    # ---- Totals row ----
    checked_out = [v for v in visits if v.get("status") == "checked_out"]
    total_copay = sum(float(v.get("copay_collected") or 0) for v in checked_out)
    pdf.set_fill_color(210, 228, 210)
    pdf.set_draw_color(100, 130, 100)
    pdf.set_font("Helvetica", "B", 8)
    label_w = sum(W[:5])   # #, Date, Service, W, D
    total_label = "Total: %d visits | %d checked out" % (len(visits), len(checked_out))
    pdf.cell(label_w, 6, total_label, border=1, fill=True)
    pdf.cell(W[5],    6, "",          border=1, fill=True)
    pdf.cell(W[6],    6, _money(total_copay) if total_copay else "-", border=1, fill=True, align="C")
    pdf.cell(W[7],    6, "",          border=1, fill=True)
    pdf.ln(5)

    # ---- Empty rows for upcoming / future visits ----
    pdf.set_font("Helvetica", "", 8)
    pdf.set_draw_color(180, 180, 180)
    next_idx = len(rows) + 1
    for extra_idx in range(next_idx, next_idx + 4):
        pdf.set_fill_color(255, 255, 255)
        erow = [str(extra_idx), "", "", "", "", "", "", ""]
        for i, cell in enumerate(erow):
            pdf.cell(W[i], ROW_H, cell, border=1, fill=False,
                     align="C" if i in (0, 3, 4, 6) else "L")
        pdf.ln()

    pdf.ln(8)

    # ---- Footer ----
    pdf.set_font("Helvetica", "I", 7.5)
    pdf.set_draw_color(0, 0, 0)
    pdf.cell(0, 4, "Generated by ClinicOS. Please verify information with patient before signing.", ln=True, align="C")

    return bytes(pdf.output())
