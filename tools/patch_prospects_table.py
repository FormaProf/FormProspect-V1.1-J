from pathlib import Path

path = Path("ui/widgets/crm/prospects_table.py")
text = path.read_text(encoding="utf-8")

replacements = [
(
'''        if col == 7:
            self._paint_pipeline_badge(painter, option.rect, raw)
        elif col == 8:
            self._paint_priority_badge(painter, option.rect, raw)
        elif col == 12:
            self._paint_score_badge(painter, option.rect, raw)
        elif col == 13:
            self._paint_level_badge(painter, option.rect, raw)
''',
'''        if col == 8:
            self._paint_pipeline_badge(painter, option.rect, raw)
        elif col == 9:
            self._paint_priority_badge(painter, option.rect, raw)
        elif col == 13:
            self._paint_score_badge(painter, option.rect, raw)
        elif col == 14:
            self._paint_level_badge(painter, option.rect, raw)
'''),
(
'''        elif col == 9 and text.lower() not in {"", "aucune", "—"}:
''',
'''        elif col == 10 and text.lower() not in {"", "aucune", "—"}:
'''),
(
'''            Qt.AlignCenter if col in {0, 3, 4, 10, 11} else Qt.AlignLeft
''',
'''            Qt.AlignCenter if col in {0, 3, 4, 5, 11, 12} else Qt.AlignLeft
'''),
(
'''    COLUMN_WIDTHS = {
        0: 52,    # N°
        1: 245,   # Entreprise
        2: 145,   # Ville
        3: 78,    # CP
        4: 128,   # Téléphone
        5: 150,   # Site web
        6: 190,   # Email
        7: 178,   # Pipeline
        8: 118,   # Priorité
        9: 190,   # Prochaine action
        10: 118,  # Date action
        11: 145,  # Commercial
        12: 105,  # Score
        13: 120,  # Niveau
    }
''',
'''    COLUMN_WIDTHS = {
        0: 52,    # N°
        1: 245,   # Entreprise
        2: 145,   # Ville
        3: 78,    # CP
        4: 128,   # Téléphone
        5: 128,   # Mobile
        6: 150,   # Site web
        7: 190,   # Email
        8: 178,   # Pipeline
        9: 118,   # Priorité
        10: 190,  # Prochaine action
        11: 118,  # Date action
        12: 145,  # Commercial
        13: 105,  # Score
        14: 120,  # Niveau
    }
'''),
(
'''        self.setColumnCount(14)
        self.setHorizontalHeaderLabels([
            "N°",
            "Entreprise",
            "Ville",
            "CP",
            "Téléphone",
            "Site web",
            "Email",
            "Pipeline",
            "Priorité",
            "Prochaine action",
            "Date action",
            "Commercial",
            "Score",
            "Niveau",
        ])
''',
'''        self.setColumnCount(15)
        self.setHorizontalHeaderLabels([
            "N°",
            "Entreprise",
            "Ville",
            "CP",
            "Téléphone",
            "Mobile",
            "Site web",
            "Email",
            "Pipeline",
            "Priorité",
            "Prochaine action",
            "Date action",
            "Commercial",
            "Score",
            "Niveau",
        ])
'''),
(
'''            telephone = prospect[4]
            site_web = prospect[5]
            email = prospect[6]
            pipeline = prospect[7] if len(prospect) > 7 and prospect[7] else PIPELINE_DEFAULT
''',
'''            telephone = prospect[4]
            mobile = prospect[15] if len(prospect) > 15 and prospect[15] else ""
            site_web = prospect[5]
            email = prospect[6]
            pipeline = prospect[7] if len(prospect) > 7 and prospect[7] else PIPELINE_DEFAULT
'''),
(
'''                self.creer_item(telephone, str(telephone or ""), Qt.AlignCenter, prospect_id),
                self.creer_item(site_web, str(site_web or "").lower(), Qt.AlignVCenter, prospect_id),
                self.creer_item(email, str(email or "").lower(), Qt.AlignVCenter, prospect_id),
                self.creer_item(pipeline, self.PIPELINE_ORDER.get(pipeline, 999), Qt.AlignCenter, prospect_id),
''',
'''                self.creer_item(telephone, str(telephone or ""), Qt.AlignCenter, prospect_id),
                self.creer_item(mobile, str(mobile or ""), Qt.AlignCenter, prospect_id),
                self.creer_item(site_web, str(site_web or "").lower(), Qt.AlignVCenter, prospect_id),
                self.creer_item(email, str(email or "").lower(), Qt.AlignVCenter, prospect_id),
                self.creer_item(pipeline, self.PIPELINE_ORDER.get(pipeline, 999), Qt.AlignCenter, prospect_id),
'''),
(
'''            items[13].setToolTip(score_label)

            self.style_pipeline(items[7], pipeline)
''',
'''            items[14].setToolTip(score_label)

            self.style_pipeline(items[8], pipeline)
'''),
(
'''            if not str(telephone or "").strip():
                items[4].setText("—")
            if not str(site_web or "").strip():
                items[5].setText("—")
            if not str(email or "").strip():
                items[6].setText("—")
            if str(prochaine_action or "").strip().lower() in {"", "aucune"}:
                items[9].setText("Aucune")
''',
'''            if not str(telephone or "").strip():
                items[4].setText("—")
            if not str(mobile or "").strip():
                items[5].setText("—")
            if not str(site_web or "").strip():
                items[6].setText("—")
            if not str(email or "").strip():
                items[7].setText("—")
            if str(prochaine_action or "").strip().lower() in {"", "aucune"}:
                items[10].setText("Aucune")
'''),
]

for old, new in replacements:
    if old not in text:
        raise RuntimeError("Un bloc attendu est introuvable dans ui/widgets/crm/prospects_table.py")
    text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
print("ui/widgets/crm/prospects_table.py corrigé")
