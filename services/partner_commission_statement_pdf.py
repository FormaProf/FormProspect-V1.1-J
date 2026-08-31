from __future__ import annotations

from html import escape
from pathlib import Path

from PySide6.QtGui import QPageSize, QTextDocument
from PySide6.QtPrintSupport import QPrinter

MONTHS = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
          "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]


def _euro(cents) -> str:
    return f"{int(cents or 0)/100:,.2f} €".replace(",", " ").replace(".", ",")


def _rate(value) -> str:
    try:
        return f"{float(value or 0):g} %"
    except (TypeError, ValueError):
        return "0 %"


def _date_fr(value) -> str:
    text = str(value or "").strip()
    if len(text) >= 10 and text[4] == "-":
        return f"{text[8:10]}/{text[5:7]}/{text[:4]}"
    return text or "—"


def _safe(value) -> str:
    return escape(str(value or "—"))


def _address(invoice: dict, prefix: str) -> str:
    city_line = " ".join(
        x for x in (
            str(invoice.get(f"{prefix}_postal_code") or "").strip(),
            str(invoice.get(f"{prefix}_city") or "").strip(),
        ) if x
    )
    parts = [
        str(invoice.get(f"{prefix}_address") or "").strip(),
        city_line,
        str(invoice.get(f"{prefix}_country") or "").strip(),
    ]
    return "<br>".join(_safe(x) for x in parts if x) or "—"


def build_partner_statement_html(invoice: dict) -> str:
    number = invoice.get("statement_number") or invoice.get("invoice_number") or "Relevé"
    month = int(invoice.get("period_month") or 0)
    year = int(invoice.get("period_year") or 0)
    period = f"{MONTHS[month-1]} {year}" if 1 <= month <= 12 else str(year or "")

    rows = []
    for line in invoice.get("lines") or []:
        rows.append(
            "<tr>"
            f"<td>{_safe(line.get('setter_name'))}</td>"
            f"<td>{_safe(line.get('prospect_name'))}</td>"
            f"<td>{_safe(line.get('offer_name') or line.get('offer_reference'))}</td>"
            f"<td>{_date_fr(line.get('signed_at'))}</td>"
            f"<td class='right'>{_rate(line.get('commission_rate'))}</td>"
            f"<td class='right strong'>{_euro(line.get('commission_cents'))}</td>"
            "</tr>"
        )
    if not rows:
        rows.append("<tr><td colspan='6' class='empty'>Aucune commission dans ce relevé.</td></tr>")

    reg = str(invoice.get("seller_registration_number") or "").strip()
    tax_id = str(invoice.get("seller_tax_id") or "").strip()
    buyer_siret = str(invoice.get("buyer_siret") or "").strip()

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
body{{font-family:Arial,Helvetica,sans-serif;color:#0B1220;font-size:10pt;margin:0}}
.brand{{color:#338CE4;font-size:11pt;font-weight:700;margin-bottom:3px}}
h1{{font-size:22pt;margin:0 0 4px 0;color:#0B1220}}
.subtitle{{color:#64748B;margin-bottom:18px}}
.meta{{width:100%;border-collapse:collapse;margin-bottom:18px}}
.meta td{{width:50%;vertical-align:top;border:1px solid #E2E8F0;padding:10px}}
.label{{color:#64748B;font-size:8pt;font-weight:700;text-transform:uppercase;margin-bottom:4px}}
.name{{font-size:11pt;font-weight:700;margin-bottom:4px}}
.lines{{width:100%;border-collapse:collapse;margin-top:8px}}
.lines th{{background:#F1F6FC;color:#334155;border:1px solid #D9E4F0;padding:7px 5px;font-size:8pt;text-align:left}}
.lines td{{border:1px solid #E2E8F0;padding:7px 5px;font-size:8.5pt}}
.right{{text-align:right}} .strong{{font-weight:700}}
.total{{margin-top:16px;text-align:right;font-size:14pt;font-weight:700;color:#0B2A52}}
.note{{margin-top:22px;padding:12px;background:#F8FAFC;border:1px solid #E2E8F0;color:#475569;font-size:8.5pt}}
.empty{{text-align:center;color:#64748B}} .footer{{margin-top:18px;color:#94A3B8;font-size:7.5pt;text-align:center}}
</style></head><body>
<div class="brand">Form@Prospect · Form@Prof</div>
<h1>Relevé de commissions partenaire</h1>
<div class="subtitle">Relevé {_safe(number)} · {_safe(period)} · Émis le {_date_fr(invoice.get("issued_at"))}</div>
<table class="meta"><tr>
<td><div class="label">Partenaire bénéficiaire</div><div class="name">{_safe(invoice.get("seller_name"))}</div>
{_address(invoice, "seller")}
{"<br>Immatriculation : " + _safe(reg) if reg else ""}
{"<br>Identifiant fiscal : " + _safe(tax_id) if tax_id else ""}</td>
<td><div class="label">Entreprise donneuse d'ordre</div><div class="name">{_safe(invoice.get("buyer_name"))}</div>
{_address(invoice, "buyer")}
{"<br>SIRET : " + _safe(buyer_siret) if buyer_siret else ""}</td>
</tr></table>
<div class="label">Détail des commissions figées</div>
<table class="lines"><tr><th>Setter</th><th>Client</th><th>Offre</th><th>Signature</th><th>Taux</th><th>Commission</th></tr>
{''.join(rows)}</table>
<div class="total">Total des commissions : {_euro(invoice.get("total_cents"))}</div>
<div class="note"><b>Important :</b> ce document est un relevé de commissions généré par Form@Prospect.
Il ne constitue pas une facture. Le partenaire commercial reste l'émetteur de sa facture officielle
à destination de NM FORMATION. Le paiement ne peut être validé dans Form@Prospect qu'après réception de cette facture.</div>
<div class="footer">Document de suivi interne généré par Form@Prospect.</div>
</body></html>"""


def save_partner_statement_pdf(invoice: dict, destination: str | Path) -> Path:
    target = Path(destination)
    if target.suffix.lower() != ".pdf":
        target = target.with_suffix(".pdf")
    target.parent.mkdir(parents=True, exist_ok=True)

    document = QTextDocument()
    document.setHtml(build_partner_statement_html(invoice))

    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(str(target))
    printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    document.print_(printer)

    if not target.is_file() or target.stat().st_size <= 0:
        raise RuntimeError("Le relevé PDF n'a pas pu être créé.")
    return target
