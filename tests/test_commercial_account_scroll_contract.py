from pathlib import Path


SOURCE = Path("ui/pages/commercial_account_page.py").read_text(
    encoding="utf-8"
)


def test_commercial_account_page_uses_vertical_scroll_area():
    assert "QScrollArea" in SOURCE
    assert 'setObjectName("AccountScrollArea")' in SOURCE
    assert "setWidgetResizable(True)" in SOURCE
    assert "setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)" in SOURCE
    assert "setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)" in SOURCE


def test_profile_card_cannot_collapse_over_its_contents():
    assert "root.addWidget(self._build_profile_card(), 1)" not in SOURCE
    assert "self.profile_card = self._build_profile_card()" in SOURCE
    assert "self.profile_card.setMinimumHeight(365)" in SOURCE
    assert "root.addWidget(self.profile_card)" in SOURCE


def test_scroll_content_keeps_existing_account_sections():
    assert "root.addWidget(self.organization_card)" in SOURCE
    assert "root.addWidget(self._build_security_card())" in SOURCE
    assert "root.addWidget(self._build_license_card())" in SOURCE
    assert "self.scroll_area.setWidget(content)" in SOURCE
    assert "outer.addWidget(self.scroll_area)" in SOURCE
