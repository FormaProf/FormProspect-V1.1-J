from pathlib import Path

path = Path("services/dashboard_data_provider.py")
text = path.read_text(encoding="utf-8")

text = text.replace(
    "        enriched = 0\n        enrichment_errors = 0\n",
    "        enriched = 0\n        no_reliable_result = 0\n        enrichment_errors = 0\n",
)

old = '''            if status in {
                "enrichi",
                "enriched",
                "completed",
                "complete",
            }:
                enriched += 1

            elif status in {
                "erreur enrichissement",
                "error",
                "failed",
                "failure",
            }:
                enrichment_errors += 1

        remaining = max(0, total - enriched)
'''

new = '''            if status in {
                "enrichi",
                "enriched",
                "completed",
                "complete",
            }:
                enriched += 1

            elif status in {
                "aucun résultat fiable",
                "aucun resultat fiable",
                "no_reliable_result",
            }:
                no_reliable_result += 1

            elif status in {
                "erreur enrichissement",
                "error",
                "failed",
                "failure",
            }:
                enrichment_errors += 1

        treated = enriched + no_reliable_result + enrichment_errors
        remaining = max(0, total - treated)
'''

if old not in text:
    raise RuntimeError("Bloc statut enrichissement introuvable")
text = text.replace(old, new)

old2 = '''            "enrichment": {
                "enriched": enriched,
                "remaining": remaining,
                "errors": enrichment_errors,
                "percentage": self._percentage(
                    enriched,
                    total,
                ),
            },
'''

new2 = '''            "enrichment": {
                "enriched": enriched,
                "no_reliable_result": no_reliable_result,
                "treated": treated,
                "remaining": remaining,
                "errors": enrichment_errors,
                "percentage": self._percentage(
                    treated,
                    total,
                ),
            },
'''

if old2 not in text:
    raise RuntimeError("Bloc dictionnaire enrichment introuvable")
text = text.replace(old2, new2)

path.write_text(text, encoding="utf-8")
print("dashboard_data_provider.py corrigé")
