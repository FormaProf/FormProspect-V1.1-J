from pathlib import Path

path = Path("ui/dialogs/prospect_dialog.py")
text = path.read_text(encoding="utf-8")

replacements = [
(
'''        self.telephone_input = QTextEdit()
        self.telephone_input.setFixedHeight(76)
        self.telephone_input.setPlaceholderText("Un numéro par ligne")
        self.site_input = QLineEdit()
''',
'''        self.telephone_input = QLineEdit()
        self.telephone_input.setPlaceholderText("Téléphone principal")
        self.mobile_input = QLineEdit()
        self.mobile_input.setPlaceholderText("Mobile / second numéro")
        self.site_input = QLineEdit()
'''),
(
'''        identity_grid.addWidget(self._field_block("Téléphone", self.telephone_input), 2, 0)
        identity_grid.addWidget(self._field_block("E-mail", self.email_input), 2, 1)
        identity_grid.addWidget(self._field_block("Site web", self.site_input), 3, 0, 1, 2)
''',
'''        identity_grid.addWidget(self._field_block("Téléphone", self.telephone_input), 2, 0)
        identity_grid.addWidget(self._field_block("Mobile", self.mobile_input), 2, 1)
        identity_grid.addWidget(self._field_block("E-mail", self.email_input), 3, 0)
        identity_grid.addWidget(self._field_block("Site web", self.site_input), 3, 1)
'''),
(
'''            self.telephone_input,
            self.site_input,
''',
'''            self.telephone_input,
            self.mobile_input,
            self.site_input,
'''),
(
'''        self.telephone_input.setPlainText(str(telephone or ""))
        self.site_input.setText(str(site_web or ""))
''',
'''        self.telephone_input.setText(str(telephone or ""))

        mobile_value = ""
        if self._is_cloud_mode and CloudRuntime.is_active():
            try:
                cloud_record = CloudRuntime.api().get_prospect(str(self.prospect_id))
                mobile_value = str(cloud_record.get("mobile") or "")
            except Exception:
                mobile_value = ""
        self.mobile_input.setText(mobile_value)

        self.site_input.setText(str(site_web or ""))
'''),
(
'''                self.telephone_input.toPlainText().strip(),
                self.site_input.text().strip(),
''',
'''                self.telephone_input.text().strip(),
                self.site_input.text().strip(),
'''),
(
'''                    {
                        "twitter": self.twitter_input.text().strip(),
                        "social_other_urls": (
                            self.social_other_urls_input.toPlainText().strip()
                        ),
                    },
''',
'''                    {
                        "mobile": self.mobile_input.text().strip(),
                        "twitter": self.twitter_input.text().strip(),
                        "social_other_urls": (
                            self.social_other_urls_input.toPlainText().strip()
                        ),
                    },
'''),
]

for old, new in replacements:
    if old not in text:
        raise RuntimeError("Un bloc attendu est introuvable dans ui/dialogs/prospect_dialog.py")
    text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
print("ui/dialogs/prospect_dialog.py corrigé")
