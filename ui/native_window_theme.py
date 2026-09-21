from __future__ import annotations

import ctypes
import os
from ctypes import wintypes

from core.theme_settings import THEME_UI_DARK, normalize_theme_mode


# Windows 10 1903 utilisait 19 ; Windows 10 20H1+ / Windows 11 utilisent 20.
_DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19
_DWMWA_USE_IMMERSIVE_DARK_MODE = 20

# Force le recalcul de la zone non cliente apres le changement DWM.
_SWP_NOSIZE = 0x0001
_SWP_NOMOVE = 0x0002
_SWP_NOZORDER = 0x0004
_SWP_NOACTIVATE = 0x0010
_SWP_FRAMECHANGED = 0x0020


def apply_native_window_theme(window, mode: str) -> bool:
    """Synchronise la barre de titre Windows avec le theme Form@Prospect.

    Retourne True lorsque Windows accepte l'attribut DWM. Sur macOS/Linux,
    ou si l'API n'est pas disponible, la fonction est volontairement neutre.
    """
    if os.name != "nt" or window is None:
        return False

    dark = normalize_theme_mode(mode) == THEME_UI_DARK

    try:
        hwnd_value = int(window.winId())
    except Exception:
        return False

    if not hwnd_value:
        return False

    try:
        dwmapi = ctypes.windll.dwmapi
        user32 = ctypes.windll.user32
    except Exception:
        return False

    hwnd = wintypes.HWND(hwnd_value)
    enabled = ctypes.c_int(1 if dark else 0)
    applied = False

    # Attribut 20 sur Windows 10 20H1+ / Windows 11, avec fallback 19
    # pour les builds Windows 10 plus anciens.
    for attribute in (
        _DWMWA_USE_IMMERSIVE_DARK_MODE,
        _DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1,
    ):
        try:
            result = dwmapi.DwmSetWindowAttribute(
                hwnd,
                ctypes.c_uint(attribute),
                ctypes.byref(enabled),
                ctypes.sizeof(enabled),
            )
        except Exception:
            continue

        if int(result) == 0:
            applied = True
            break

    if not applied:
        return False

    try:
        user32.SetWindowPos(
            hwnd,
            wintypes.HWND(0),
            0,
            0,
            0,
            0,
            _SWP_NOMOVE
            | _SWP_NOSIZE
            | _SWP_NOZORDER
            | _SWP_NOACTIVATE
            | _SWP_FRAMECHANGED,
        )
    except Exception:
        # L'attribut DWM a deja ete applique ; l'echec du redraw n'est pas fatal.
        pass

    return True

def apply_qt_window_chrome(window, mode: str) -> None:
    """Synchronise la barre de menus et la barre d'etat avec le theme global.

    Le theme Classique rend la main aux styles historiques. UI Clair et UI
    Sombre utilisent un chrome discret coherent avec les surfaces UI 2.0.
    """
    if window is None:
        return

    normalized = normalize_theme_mode(mode)

    try:
        menu_bar = window.menuBar()
        status_bar = window.statusBar()
    except Exception:
        return

    # Classique = comportement historique exact : on retire tout QSS ajoute.
    if normalized not in (THEME_UI_DARK, "ui_light"):
        if menu_bar is not None:
            menu_bar.setStyleSheet("")
        if status_bar is not None:
            status_bar.setStyleSheet("")
        return

    dark = normalized == THEME_UI_DARK

    if dark:
        menu_bg = "#06111F"
        menu_fg = "#C9D8E8"
        menu_hover = "#10243A"
        menu_selected = "#12365B"
        menu_border = "#1A3A59"
        menu_disabled = "#607891"
        popup_bg = "#0B1A2B"
        status_bg = "#06111F"
        status_fg = "#8FA8C1"
    else:
        menu_bg = "#F7FAFD"
        menu_fg = "#243B53"
        menu_hover = "#EAF4FF"
        menu_selected = "#DDEEFF"
        menu_border = "#D6E4F0"
        menu_disabled = "#94A3B8"
        popup_bg = "#FFFFFF"
        status_bg = "#F7FAFD"
        status_fg = "#60758A"

    if menu_bar is not None:
        menu_bar.setStyleSheet(f"""
            QMenuBar {{
                background:{menu_bg};
                color:{menu_fg};
                border:none;
                border-bottom:1px solid {menu_border};
                spacing:2px;
                padding:1px 5px;
            }}
            QMenuBar::item {{
                background:transparent;
                color:{menu_fg};
                border-radius:5px;
                padding:4px 9px;
                margin:1px 1px;
            }}
            QMenuBar::item:selected {{
                background:{menu_hover};
                color:{menu_fg};
            }}
            QMenuBar::item:pressed {{
                background:{menu_selected};
                color:{menu_fg};
            }}
            QMenu {{
                background:{popup_bg};
                color:{menu_fg};
                border:1px solid {menu_border};
                padding:5px;
            }}
            QMenu::item {{
                background:transparent;
                color:{menu_fg};
                border-radius:5px;
                padding:6px 26px 6px 10px;
                margin:1px 2px;
            }}
            QMenu::item:selected {{
                background:{menu_selected};
                color:{menu_fg};
            }}
            QMenu::item:disabled {{
                color:{menu_disabled};
            }}
            QMenu::separator {{
                height:1px;
                background:{menu_border};
                margin:5px 8px;
            }}
        """)

    if status_bar is not None:
        status_bar.setStyleSheet(f"""
            QStatusBar {{
                background:{status_bg};
                color:{status_fg};
                border:none;
                border-top:1px solid {menu_border};
                padding:0 7px;
            }}
            QStatusBar QLabel {{
                background:transparent;
                color:{status_fg};
            }}
            QStatusBar::item {{
                border:none;
            }}
        """)

