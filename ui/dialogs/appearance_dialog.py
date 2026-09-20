from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.theme_settings import (
    THEME_CLASSIC,
    THEME_UI_DARK,
    THEME_UI_LIGHT,
    get_theme_preference,
    set_theme_preference,
)

THEME_SHORT_LABELS = {
    THEME_CLASSIC: "CLASSIQUE",
    THEME_UI_LIGHT: "UI CLAIR",
    THEME_UI_DARK: "UI SOMBRE",
}

THEME_CATALOG = (
    {
        "mode": THEME_CLASSIC,
        "title": "Form@Prospect Classique",
        "tagline": "L'expérience historique",
        "description": "L'interface d'origine, familière et efficace.",
        "badge": "ORIGINAL",
        "accent": "#338CE4",
        "preview": {
            "canvas": "#EEF2F6",
            "sidebar": "#0B2A52",
            "content": "#F5F8FC",
            "card": "#FFFFFF",
            "border": "#D9E3ED",
            "line": "#AEBED0",
            "accent": "#338CE4",
            "accent_2": "#338CE4",
        },
    },
    {
        "mode": THEME_UI_LIGHT,
        "title": "Form@Prospect UI Clair",
        "tagline": "Premium IA lumineux",
        "description": "Profondeur, cartes dynamiques et identité nouvelle technologie.",
        "badge": "PREMIUM",
        "accent": "#338CE4",
        "preview": {
            "canvas": "#EAF4FD",
            "sidebar": "#092A4B",
            "content": "#F3F8FD",
            "card": "#FFFFFF",
            "border": "#C9E0F3",
            "line": "#8FB7D6",
            "accent": "#338CE4",
            "accent_2": "#5C63F2",
        },
    },
    {
        "mode": THEME_UI_DARK,
        "title": "Form@Prospect UI Sombre",
        "tagline": "AI Command Center",
        "description": "Cockpit sombre, glow subtil et univers automatisation / IA.",
        "badge": "AI PREMIUM",
        "accent": "#65D8FF",
        "preview": {
            "canvas": "#06111F",
            "sidebar": "#071522",
            "content": "#081725",
            "card": "#0B1A2B",
            "border": "#1A3A59",
            "line": "#4B7398",
            "accent": "#65D8FF",
            "accent_2": "#5C63F2",
        },
    },
)


class ThemePreviewCard(QFrame):
    selected = Signal(str)

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.mode = theme["mode"]
        self.accent = theme["accent"]
        self._selected = False
        self._active = False

        self.setObjectName("ThemePreviewCard")
        self.setProperty("selected", False)
        self.setProperty("active", False)
        self.setProperty("hovered", False)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumWidth(270)
        self.setMinimumHeight(352)

        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(22.0)
        self._shadow.setOffset(0.0, 7.0)
        self._shadow.setColor(QColor(26, 68, 104, 32))
        self.setGraphicsEffect(self._shadow)

        self._blur_animation = QPropertyAnimation(self._shadow, b"blurRadius", self)
        self._blur_animation.setDuration(170)
        self._blur_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._offset_animation = QPropertyAnimation(self._shadow, b"yOffset", self)
        self._offset_animation.setDuration(170)
        self._offset_animation.setEasingCurve(QEasingCurve.OutCubic)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        root.addWidget(self._build_preview())

        meta_row = QHBoxLayout()
        meta_row.setSpacing(8)

        badge = QLabel(theme["badge"])
        badge.setFixedHeight(24)
        badge.setStyleSheet(
            f"font-size:9px; font-weight:900; letter-spacing:0.8px; "
            f"color:{self.accent}; background:#EDF6FF; "
            f"border:1px solid #CBE5F8; border-radius:8px; padding:0 9px;"
            if self.mode != THEME_UI_DARK
            else
            "font-size:9px; font-weight:900; letter-spacing:0.8px; "
            "color:#65D8FF; background:#0A2740; "
            "border:1px solid #24587E; border-radius:8px; padding:0 9px;"
        )
        meta_row.addWidget(badge)
        meta_row.addStretch()

        self.active_badge = QLabel("✓ THÈME ACTIF")
        self.active_badge.setFixedHeight(24)
        self.active_badge.setStyleSheet(
            "font-size:9px; font-weight:900; color:#0B7D5A; "
            "background:#E9F9F3; border:1px solid #B9E8D6; "
            "border-radius:8px; padding:0 9px;"
        )
        self.active_badge.hide()
        meta_row.addWidget(self.active_badge)
        root.addLayout(meta_row)

        title = QLabel(theme["title"])
        title.setStyleSheet(
            "font-size:17px; font-weight:900; color:#0B1E33; "
            "background:transparent; border:none;"
        )
        root.addWidget(title)

        tagline = QLabel(theme["tagline"])
        tagline.setStyleSheet(
            f"font-size:11px; font-weight:850; color:{self.accent if self.mode != THEME_UI_DARK else '#287CB6'}; "
            "background:transparent; border:none;"
        )
        root.addWidget(tagline)

        description = QLabel(theme["description"])
        description.setWordWrap(True)
        description.setMinimumHeight(42)
        description.setStyleSheet(
            "font-size:10px; line-height:1.3; color:#6B8197; "
            "background:transparent; border:none;"
        )
        root.addWidget(description)

        root.addStretch()

        self.selection_hint = QLabel("Cliquer pour sélectionner")
        self.selection_hint.setStyleSheet(
            "font-size:9px; font-weight:750; color:#8A9CAF; "
            "background:transparent; border:none;"
        )
        root.addWidget(self.selection_hint)

        self._apply_card_style()

        for child in self.findChildren(QWidget):
            child.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def _build_preview(self) -> QFrame:
        p = self.theme["preview"]
        preview = QFrame()
        preview.setObjectName("ThemeMiniPreview")
        preview.setFixedHeight(150)
        preview.setStyleSheet(
            f"QFrame#ThemeMiniPreview {{ background:{p['canvas']}; "
            f"border:1px solid {p['border']}; border-radius:15px; }}"
        )

        row = QHBoxLayout(preview)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        sidebar = QFrame()
        sidebar.setFixedWidth(54)
        sidebar.setStyleSheet(
            f"background:{p['sidebar']}; border:none; "
            "border-top-left-radius:14px; border-bottom-left-radius:14px;"
        )
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(10, 14, 10, 12)
        side_layout.setSpacing(8)

        logo = QFrame()
        logo.setFixedSize(20, 20)
        logo.setStyleSheet(
            f"background:{p['accent']}; border:none; border-radius:10px;"
        )
        side_layout.addWidget(logo, 0, Qt.AlignHCenter)
        side_layout.addSpacing(4)

        for index in range(5):
            line = QFrame()
            line.setFixedHeight(6 if index else 8)
            line.setStyleSheet(
                f"background:{p['accent'] if index == 0 else p['line']}; "
                "border:none; border-radius:3px;"
            )
            side_layout.addWidget(line)
        side_layout.addStretch()
        row.addWidget(sidebar)

        content = QFrame()
        content.setStyleSheet(f"background:{p['content']}; border:none;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(11, 11, 11, 11)
        content_layout.setSpacing(8)

        top = QHBoxLayout()
        header_line = QFrame()
        header_line.setFixedHeight(9)
        header_line.setStyleSheet(
            f"background:{p['accent']}; border:none; border-radius:4px;"
        )
        top.addWidget(header_line, 2)
        top.addSpacing(10)
        status = QFrame()
        status.setFixedSize(44, 9)
        status.setStyleSheet(
            f"background:{p['accent_2']}; border:none; border-radius:4px;"
        )
        top.addWidget(status)
        content_layout.addLayout(top)

        hero = QFrame()
        hero.setFixedHeight(48)
        hero.setStyleSheet(
            f"background:{p['card']}; border:1px solid {p['border']}; border-radius:9px;"
        )
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(8, 8, 8, 8)
        hero_layout.setSpacing(5)
        for width in (115, 78):
            line = QFrame()
            line.setFixedSize(width, 6)
            line.setStyleSheet(
                f"background:{p['line']}; border:none; border-radius:3px;"
            )
            hero_layout.addWidget(line)
        content_layout.addWidget(hero)

        mini_row = QHBoxLayout()
        mini_row.setSpacing(7)
        for index in range(2):
            mini = QFrame()
            mini.setFixedHeight(42)
            mini.setStyleSheet(
                f"background:{p['card']}; border:1px solid {p['border']}; border-radius:9px;"
            )
            mini_layout = QVBoxLayout(mini)
            mini_layout.setContentsMargins(7, 7, 7, 7)
            mini_layout.setSpacing(4)
            dot = QFrame()
            dot.setFixedSize(16 if index == 0 else 23, 5)
            dot.setStyleSheet(
                f"background:{p['accent'] if index == 0 else p['accent_2']}; "
                "border:none; border-radius:2px;"
            )
            mini_layout.addWidget(dot)
            mini_layout.addStretch()
            mini_row.addWidget(mini, 1)
        content_layout.addLayout(mini_row)
        row.addWidget(content, 1)

        return preview

    def _apply_card_style(self):
        self.setStyleSheet(f'''
            QFrame#ThemePreviewCard {{
                background:#FFFFFF;
                border:1px solid #D7E4F0;
                border-radius:22px;
            }}
            QFrame#ThemePreviewCard[hovered="true"] {{
                background:#FBFDFF;
                border:2px solid #9CCCF1;
            }}
            QFrame#ThemePreviewCard[selected="true"] {{
                background:#F7FBFF;
                border:3px solid {self.accent};
            }}
            QFrame#ThemePreviewCard[active="true"] {{
                background:#FCFEFF;
            }}
        ''')

    def _refresh_property_style(self):
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def set_selected(self, selected: bool):
        self._selected = bool(selected)
        self.setProperty("selected", self._selected)
        self.selection_hint.setText(
            "✓ Sélectionné" if self._selected else "Cliquer pour sélectionner"
        )
        self.selection_hint.setStyleSheet(
            f"font-size:9px; font-weight:900; color:{self.accent}; "
            "background:transparent; border:none;"
            if self._selected
            else
            "font-size:9px; font-weight:750; color:#8A9CAF; "
            "background:transparent; border:none;"
        )
        self._refresh_property_style()

    def set_active(self, active: bool):
        self._active = bool(active)
        self.setProperty("active", self._active)
        self.active_badge.setVisible(self._active)
        self._refresh_property_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.selected.emit(self.mode)
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self.setProperty("hovered", True)
        self._refresh_property_style()
        self._blur_animation.stop()
        self._blur_animation.setStartValue(self._shadow.blurRadius())
        self._blur_animation.setEndValue(36.0)
        self._blur_animation.start()
        self._offset_animation.stop()
        self._offset_animation.setStartValue(self._shadow.yOffset())
        self._offset_animation.setEndValue(10.0)
        self._offset_animation.start()
        self._shadow.setColor(QColor(51, 140, 228, 72))
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setProperty("hovered", False)
        self._refresh_property_style()
        self._blur_animation.stop()
        self._blur_animation.setStartValue(self._shadow.blurRadius())
        self._blur_animation.setEndValue(22.0)
        self._blur_animation.start()
        self._offset_animation.stop()
        self._offset_animation.setStartValue(self._shadow.yOffset())
        self._offset_animation.setEndValue(7.0)
        self._offset_animation.start()
        self._shadow.setColor(QColor(26, 68, 104, 32))
        super().leaveEvent(event)


class AppearanceDialog(QDialog):
    """Global Form@Prospect appearance selector."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Apparence de Form@Prospect")
        self.setModal(True)
        self.resize(1040, 650)
        self.setMinimumSize(930, 610)
        self.setStyleSheet("background:#F3F7FB;")

        self._current_theme = get_theme_preference()
        self._selected_theme = self._current_theme
        self._cards: dict[str, ThemePreviewCard] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 26)
        root.setSpacing(18)

        header = QHBoxLayout()
        header.setSpacing(18)

        header_text = QVBoxLayout()
        header_text.setSpacing(7)
        eyebrow = QLabel("FORM@PROSPECT  •  GALERIE D'APPARENCE")
        eyebrow.setStyleSheet(
            "font-size:10px; font-weight:900; letter-spacing:1.2px; "
            "color:#338CE4; background:transparent;"
        )
        title = QLabel("Choisissez votre expérience Form@Prospect")
        title.setStyleSheet(
            "font-size:26px; font-weight:900; color:#0B1E33; "
            "background:transparent;"
        )
        subtitle = QLabel(
            "Trois identités visuelles, une seule expérience métier. "
            "Votre choix est mémorisé sur cet appareil."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(
            "font-size:12px; color:#6B839C; background:transparent;"
        )
        header_text.addWidget(eyebrow)
        header_text.addWidget(title)
        header_text.addWidget(subtitle)
        header.addLayout(header_text, 1)

        self.current_theme_pill = QLabel()
        self.current_theme_pill.setAlignment(Qt.AlignCenter)
        self.current_theme_pill.setFixedHeight(32)
        self.current_theme_pill.setMinimumWidth(168)
        self.current_theme_pill.setStyleSheet(
            "font-size:9px; font-weight:900; letter-spacing:0.7px; "
            "color:#0B6FAE; background:#EAF6FF; "
            "border:1px solid #B8DDF6; border-radius:11px; padding:0 12px;"
        )
        header.addWidget(self.current_theme_pill, 0, Qt.AlignTop)
        root.addLayout(header)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background:#DCE8F3; border:none;")
        root.addWidget(divider)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        for theme in THEME_CATALOG:
            card = ThemePreviewCard(theme, self)
            card.selected.connect(self._select_theme)
            self._cards[theme["mode"]] = card
            cards_layout.addWidget(card, 1)

        root.addLayout(cards_layout, 1)

        footer = QHBoxLayout()
        footer.setSpacing(12)

        info = QVBoxLayout()
        info.setSpacing(3)
        self.selection_title = QLabel()
        self.selection_title.setStyleSheet(
            "font-size:11px; font-weight:900; color:#23384D; "
            "background:transparent;"
        )
        selection_hint = QLabel(
            "Le thème choisi devient la préférence globale de Form@Prospect."
        )
        selection_hint.setStyleSheet(
            "font-size:10px; color:#7890A6; background:transparent;"
        )
        info.addWidget(self.selection_title)
        info.addWidget(selection_hint)
        footer.addLayout(info, 1)

        cancel = QPushButton("Annuler")
        cancel.setFixedHeight(44)
        cancel.setStyleSheet('''
            QPushButton {
                background:#FFFFFF;
                color:#334155;
                border:1px solid #D7E6F4;
                border-radius:12px;
                padding:0 19px;
                font-size:12px;
                font-weight:800;
            }
            QPushButton:hover {
                color:#338CE4;
                border-color:#9CC9EE;
                background:#F8FCFF;
            }
        ''')
        cancel.clicked.connect(self.reject)
        footer.addWidget(cancel)

        self.save_button = QPushButton("Utiliser ce thème")
        self.save_button.setFixedHeight(44)
        self.save_button.setMinimumWidth(176)
        self.save_button.setStyleSheet('''
            QPushButton {
                background:qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #338CE4,
                    stop:1 #5C63F2
                );
                color:#FFFFFF;
                border:1px solid #67B6F5;
                border-radius:12px;
                padding:0 20px;
                font-size:12px;
                font-weight:900;
            }
            QPushButton:hover {
                border-color:#9BD8FF;
            }
            QPushButton:disabled {
                background:#E4ECF4;
                color:#8AA0B5;
                border:1px solid #D5E0EA;
            }
        ''')
        self.save_button.clicked.connect(self._save)
        footer.addWidget(self.save_button)
        root.addLayout(footer)

        self._sync_gallery_state()

    def _theme_title(self, mode: str) -> str:
        for theme in THEME_CATALOG:
            if theme["mode"] == mode:
                return theme["title"]
        return "Form@Prospect"

    def _select_theme(self, mode: str):
        if mode not in self._cards:
            return
        self._selected_theme = mode
        self._sync_gallery_state()

    def _sync_gallery_state(self):
        for mode, card in self._cards.items():
            card.set_active(mode == self._current_theme)
            card.set_selected(mode == self._selected_theme)

        self.current_theme_pill.setText(
            f"ACTIF  •  {self._theme_title(self._current_theme)}"
        )
        self.selection_title.setText(
            f"Sélection : {self._theme_title(self._selected_theme)}"
        )

        is_current = self._selected_theme == self._current_theme
        self.save_button.setDisabled(is_current)
        self.save_button.setText(
            "Thème déjà actif" if is_current else "Utiliser ce thème"
        )

    def _save(self):
        set_theme_preference(self._selected_theme)
        self._current_theme = self._selected_theme
        self.accept()

    @property
    def selected_theme(self) -> str:
        return self._selected_theme
