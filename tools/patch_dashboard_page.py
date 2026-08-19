from pathlib import Path

path = Path("ui/pages/dashboard_page.py")
text = path.read_text(encoding="utf-8")

old = '''            self.enrichment_label.setText(
                f"{self._format_number(enrichment['enriched'])} / "
                f"{self._format_number(data['kpi']['prospects'])} prospects enrichis"
            )
            self.enrichment_progress.setValue(enrichment["percentage"])
            self.enrichment_progress.setFormat(
                f"{enrichment['percentage']} %"
            )
            self.enrichment_detail.setText(
                f"{self._format_number(enrichment['remaining'])} restant(s) • "
                f"{self._format_number(enrichment['errors'])} erreur(s)"
            )
'''

new = '''            treated = int(enrichment.get("treated", enrichment["enriched"]) or 0)
            no_reliable = int(enrichment.get("no_reliable_result", 0) or 0)

            self.enrichment_label.setText(
                f"{self._format_number(treated)} / "
                f"{self._format_number(data['kpi']['prospects'])} prospects traités"
            )
            self.enrichment_progress.setValue(enrichment["percentage"])
            self.enrichment_progress.setFormat(
                f"{enrichment['percentage']} %"
            )
            self.enrichment_detail.setText(
                f"{self._format_number(enrichment['enriched'])} enrichi(s) • "
                f"{self._format_number(no_reliable)} sans résultat fiable • "
                f"{self._format_number(enrichment['remaining'])} restant(s) • "
                f"{self._format_number(enrichment['errors'])} erreur(s)"
            )
'''

if old not in text:
    raise RuntimeError("Bloc affichage enrichissement introuvable")
text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
print("dashboard_page.py corrigé")
