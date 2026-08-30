from __future__ import annotations

from html import escape
from pathlib import Path

from PySide6.QtCore import QMarginsF
from PySide6.QtGui import QPageLayout, QPageSize, QPdfWriter, QTextDocument


MONTHS = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
]


def _euro(cents: int) -> str:
    return f"{int(cents or 0) / 100:,.2f} EUR".replace(",", " ").replace(".", ",")


def _date_fr(value) -> str:
    text = str(value or "")
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return f"{text[8:10]}/{text[5:7]}/{text[0:4]}"
    return text


def _safe(value) -> str:
    return escape(str(value or ""))


def build_invoice_html(invoice: dict) -> str:
    month = int(invoice.get("period_month") or 1)
    year = int(invoice.get("period_year") or 0)
    period = f"{MONTHS[month - 1]} {year}" if 1 <= month <= 12 else str(year)

    seller_lines = [
        _safe(invoice.get("seller_name")),
        _safe(invoice.get("seller_address")),
        f"{_safe(invoice.get('seller_postal_code'))} {_safe(invoice.get('seller_city'))}".strip(),
        _safe(invoice.get("seller_country")),
        f"SIRET : {_safe(invoice.get('seller_siret'))}",
        _safe(invoice.get("seller_email")),
    ]
    if invoice.get("seller_vat_number"):
        seller_lines.append(f"TVA intracommunautaire : {_safe(invoice.get('seller_vat_number'))}")

    buyer_lines = [
        _safe(invoice.get("buyer_name")),
        _safe(invoice.get("buyer_address")),
        f"{_safe(invoice.get('buyer_postal_code'))} {_safe(invoice.get('buyer_city'))}".strip(),
        _safe(invoice.get("buyer_country")),
        f"SIRET : {_safe(invoice.get('buyer_siret'))}",
    ]

    rows = []
    for line in invoice.get("lines") or []:
        rows.append(
            "<tr>"
            f"<td>{_date_fr(line.get('signed_at'))}</td>"
            f"<td>{_safe(line.get('prospect_name'))}</td>"
            f"<td>{_safe(line.get('offer_name'))}</td>"
            f"<td style='text-align:right'>{float(line.get('commission_rate') or 0):g} %</td>"
            f"<td style='text-align:right'>{_euro(int(line.get('commission_cents') or 0))}</td>"
            "</tr>"
        )

    tax_version = int(invoice.get("tax_calculation_version") or 1)
    vat_mention = _safe(invoice.get("seller_vat_mention"))

    if tax_version >= 2:
        total_ht_cents = int(invoice.get("total_ht_cents") or 0)
        vat_cents = int(invoice.get("vat_cents") or 0)
        total_ttc_cents = int(invoice.get("total_cents") or 0)
        try:
            vat_rate = float(invoice.get("seller_vat_rate") or 0)
        except (TypeError, ValueError):
            vat_rate = 0.0
        totals_html = (
            "<table class='totals'>"
            f"<tr><td>TOTAL HT</td><td><b>{_euro(total_ht_cents)}</b></td></tr>"
            f"<tr><td>TVA {vat_rate:g} %</td><td><b>{_euro(vat_cents)}</b></td></tr>"
            f"<tr class='grand'><td>TOTAL TTC</td><td><b>{_euro(total_ttc_cents)}</b></td></tr>"
            "</table>"
        )
        vat_html = (
            f"<p><b>Mention TVA :</b> {vat_mention}</p>" if vat_mention else ""
        )
        commission_heading = "Commission HT"
    else:
        # Factures historiques : préserver l'ancien rendu et ne jamais leur
        # appliquer rétroactivement le régime fiscal actuel du commercial.
        totals_html = (
            f"<p class='total'>TOTAL À PAYER : {_euro(int(invoice.get('total_cents') or 0))}</p>"
        )
        vat_html = f"<p><b>TVA :</b> {vat_mention}</p>" if vat_mention else ""
        commission_heading = "Commission"

    return f"""
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: Arial, sans-serif; color:#111827; font-size:10pt; }}
        h1 {{ color:#338CE4; font-size:24pt; margin-bottom:4px; }}
        .muted {{ color:#6B7280; }}
        .boxes {{ width:100%; margin-top:18px; }}
        .box {{ width:47%; vertical-align:top; border:1px solid #E5E7EB; padding:10px; }}
        table.lines {{ width:100%; border-collapse:collapse; margin-top:22px; }}
        table.lines th {{ background:#EEF6FF; color:#123B63; padding:7px; border:1px solid #D9E8F5; }}
        table.lines td {{ padding:7px; border:1px solid #E5E7EB; }}
        .total {{ text-align:right; font-size:15pt; font-weight:bold; margin-top:16px; }}
        table.totals {{ width:44%; margin-left:56%; margin-top:16px; border-collapse:collapse; }}
        table.totals td {{ padding:5px 4px; text-align:right; }}
        table.totals td:first-child {{ text-align:left; }}
        table.totals tr.grand td {{ border-top:2px solid #123B63; font-size:15pt; padding-top:8px; }}
        .footer {{ margin-top:26px; color:#6B7280; font-size:9pt; }}
      </style>
    </head>
    <body>
      <h1>FACTURE</h1>
      <p>
        <b>N° {_safe(invoice.get('invoice_number'))}</b><br>
        Date d'émission : {_date_fr(invoice.get('issued_at'))}<br>
        Période de commissions : <b>{_safe(period)}</b><br>
        Paiement prévu : <b>{_date_fr(invoice.get('scheduled_payment_on'))}</b>
      </p>

      <table class="boxes">
        <tr>
          <td class="box"><b>Prestataire / Émetteur</b><br>{"<br>".join(seller_lines)}</td>
          <td style="width:6%"></td>
          <td class="box"><b>Client</b><br>{"<br>".join(buyer_lines)}</td>
        </tr>
      </table>

      <p style="margin-top:20px"><b>Objet :</b> Commissions commerciales - {period}</p>

      <table class="lines">
        <tr>
          <th>Date vente</th>
          <th>Client</th>
          <th>Formation</th>
          <th>Taux</th>
          <th>{commission_heading}</th>
        </tr>
        {"".join(rows)}
      </table>

      {totals_html}
      {vat_html}
      <p>Modalité de règlement : virement bancaire selon le cycle mensuel convenu.</p>
      <div class="footer">
        Facture générée depuis Form@Prospect à partir des commissions validées automatiquement à J+15.
      </div>
    </body>
    </html>
    """


def save_invoice_pdf(invoice: dict, destination: str | Path) -> Path:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    writer = QPdfWriter(str(destination))
    writer.setPageSize(QPageSize(QPageSize.A4))
    writer.setPageMargins(QMarginsF(14, 14, 14, 14), QPageLayout.Millimeter)
    writer.setResolution(96)
    writer.setTitle(f"Facture {invoice.get('invoice_number', '')}")
    writer.setCreator("Form@Prospect - NM FORMATION")

    document = QTextDocument()
    document.setHtml(build_invoice_html(invoice))
    document.print_(writer)
    return destination
