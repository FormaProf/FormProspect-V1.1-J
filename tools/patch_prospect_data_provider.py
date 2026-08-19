from pathlib import Path

path = Path("services/prospect_data_provider.py")
text = path.read_text(encoding="utf-8")

old = '''        base = (
            item.get("id"),
            item.get("company_name", ""),
            item.get("city", ""),
            item.get("postal_code", ""),
            item.get("phone", ""),
            item.get("website", ""),
            item.get("email", ""),
            pipeline_to_ui(item.get("pipeline_stage", "nouveau")),
            priority_to_ui(item.get("priority", "normal")),
            item.get("next_action", "") or "Aucune",
            display_datetime(item.get("next_action_at")),
            owner_display_name,
            0,
            "★☆☆☆☆",
            "Score Cloud à venir",
        )
'''

new = '''        base = (
            item.get("id"),
            item.get("company_name", ""),
            item.get("city", ""),
            item.get("postal_code", ""),
            item.get("phone", ""),
            item.get("website", ""),
            item.get("email", ""),
            pipeline_to_ui(item.get("pipeline_stage", "nouveau")),
            priority_to_ui(item.get("priority", "normal")),
            item.get("next_action", "") or "Aucune",
            display_datetime(item.get("next_action_at")),
            owner_display_name,
            0,
            "★☆☆☆☆",
            "Score Cloud à venir",
            item.get("mobile", ""),
        )
'''

if old not in text:
    raise RuntimeError("Bloc Cloud _row(base) introuvable dans services/prospect_data_provider.py")

text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
print("services/prospect_data_provider.py corrigé")
