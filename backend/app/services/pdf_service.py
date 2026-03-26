"""
PDF generation service for ClinicOS.
Generates Individual Visit Sign Sheet (printable patient record).
Uses fpdf2 (pure Python, pip install fpdf2).
All text is ASCII/latin-1 safe so Helvetica built-in font works.
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


def _fmt_date(iso):
    return _fmt_dt(iso, "%m/%d/%Y")


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
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    # ---- Header ----
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 8, "Individual Visit Sign Sheet", ln=True, align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, "Printed: " + _today(), ln=True, align="C")
    pdf.ln(3)

    # ---- Patient Info ----
    first = str(patient.get("first_name") or "")
    last  = str(patient.get("last_name") or "")
    full  = str(patient.get("full_name") or (first + " " + last).strip())
    dob   = str(patient.get("date_of_birth") or "-")
    mrn   = str(patient.get("mrn") or "-")
    ph    = str(patient.get("phone") or "-")

    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Patient Information", ln=True, fill=True)
    pdf.set_font("Helvetica", "", 9)
    col = 95
    pdf.cell(col, 5, "Name:  " + full, border=0)
    pdf.cell(col, 5, "MRN:   " + mrn, border=0, ln=True)
    pdf.cell(col, 5, "DOB:   " + dob, border=0)
    pdf.cell(col, 5, "Phone: " + ph, border=0, ln=True)
    pdf.ln(2)

    # ---- Insurance ----
    if policies:
        pdf.set_fill_color(230, 230, 230)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, "Insurance Information", ln=True, fill=True)
        for pol in policies[:2]:
            priority = str(pol.get("priority") or "primary").capitalize()
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(0, 5, "  " + priority + " Insurance", ln=True)
            pdf.set_font("Helvetica", "", 9)
            carrier  = str(pol.get("carrier_name") or "-")
            member   = str(pol.get("member_id") or "-")
            group    = str(pol.get("group_number") or "-")
            plan_t   = str(pol.get("plan_type") or "-")
            copay    = _money(pol.get("copay_amount"))
            ded      = _money(pol.get("deductible"))
            vis_auth = pol.get("visits_authorized")
            vis_used = pol.get("visits_used") or 0
            elig     = str(pol.get("eligibility_status") or "-")
            vis_str  = str(vis_used) + "/" + (str(vis_auth) if vis_auth else "?")
            pdf.cell(col, 4.5, "  Carrier:    " + carrier)
            pdf.cell(col, 4.5, "Plan Type:   " + plan_t, ln=True)
            pdf.cell(col, 4.5, "  Member ID:  " + member)
            pdf.cell(col, 4.5, "Group No:    " + group, ln=True)
            pdf.cell(col, 4.5, "  Copay:      " + copay)
            pdf.cell(col, 4.5, "Deductible:  " + ded, ln=True)
            pdf.cell(col, 4.5, "  Visits:     " + vis_str)
            pdf.cell(col, 4.5, "Eligibility: " + elig, ln=True)
            pdf.ln(1)
        pdf.ln(1)

    # ---- Visit Table ----
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Visit Records", ln=True, fill=True)
    pdf.ln(1)

    # col widths mm: Date | Service | Staff | CC | WD | Signed | Check-Out
    W = [28, 22, 38, 22, 12, 16, 35]
    HEADERS = ["Date", "Service", "Staff / Provider", "Copay CC", "WD", "Signed", "Check-Out"]
    pdf.set_fill_color(210, 220, 210)
    pdf.set_font("Helvetica", "B", 8)
    for i, h in enumerate(HEADERS):
        pdf.cell(W[i], 6, h, border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    alt = False
    for v in visits:
        status   = str(v.get("status") or "")
        date_str = _fmt_date(v.get("check_in_time"))
        svc      = str(v.get("service_type") or "-")[:12]
        staff    = str(v.get("staff_name") or v.get("staff_id") or "-")[:20]
        if status == "checked_out":
            cc       = _money(v.get("copay_collected"))
            wd       = "Yes" if v.get("wd_verified") else ""
            signed   = "Yes" if v.get("patient_signed") else ""
            checkout = _fmt_dt(v.get("check_out_time"), "%m/%d %H:%M")
        else:
            cc = wd = signed = ""
            checkout = ("(" + status + ")")[:14]

        if alt:
            pdf.set_fill_color(248, 252, 248)
        else:
            pdf.set_fill_color(255, 255, 255)
        alt = not alt

        row = [date_str, svc, staff, cc, wd, signed, checkout]
        for i, cell in enumerate(row):
            pdf.cell(W[i], 5.5, str(cell), border=1, fill=True,
                     align="C" if i in (3, 4, 5) else "L")
        pdf.ln()

    # ---- Totals ----
    checked_out = [v for v in visits if v.get("status") == "checked_out"]
    total_copay = sum(float(v.get("copay_collected") or 0) for v in checked_out)
    pdf.set_fill_color(210, 225, 210)
    pdf.set_font("Helvetica", "B", 8)
    label = "Total Visits: %d  |  Checked Out: %d" % (len(visits), len(checked_out))
    pdf.cell(sum(W[:3]), 5.5, label, border=1, fill=True)
    pdf.cell(W[3], 5.5, _money(total_copay) if total_copay else "-", border=1, fill=True, align="C")
    pdf.cell(W[4] + W[5] + W[6], 5.5, "", border=1, fill=True)
    pdf.ln(8)

    # ---- Signature ----
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(95, 5, "Patient Signature: ______________________________")
    pdf.cell(0, 5, "Date: _______________", ln=True)
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 7.5)
    pdf.cell(0, 4,
             "Generated by ClinicOS. Please verify with the patient before signing.",
             ln=True, align="C")

    return bytes(pdf.output())
