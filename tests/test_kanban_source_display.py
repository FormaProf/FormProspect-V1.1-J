from PySide6.QtWidgets import QApplication, QLabel
from ui.widgets.crm.kanban_card import KanbanCard


def test_kanban_card_displays_prospect_source():
    app = QApplication.instance() or QApplication([])
    prospect = (
        "prospect-1", "TEST BTP", "Lille", "59000",
        "03 20 00 00 00", "https://example.test", "test@example.test",
        "Lead chaud", "Haute", "Rappeler", "",
        "Nass MESSADI", 75, "4/5", "Bon prospect",
        "06 00 00 00 00", "Landing Page Nass",
    )
    card = KanbanCard(prospect)
    texts = [label.text() for label in card.findChildren(QLabel)]
    assert "Source : Landing Page Nass" in texts
