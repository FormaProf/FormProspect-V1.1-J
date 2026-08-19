from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QVBoxLayout,
)

from core.constants import VERSION
from services.update_service import UpdateError, UpdateInfo, UpdateService


class UpdateDialog(QDialog):
    def __init__(
        self,
        service: UpdateService,
        info: UpdateInfo,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.info = info
        self._install_started = False

        self.setWindowTitle("Mise à jour Form@Prospect")
        self.setMinimumWidth(610)
        self.setModal(True)
        self.setStyleSheet("QDialog{background:#F4F7FB;}")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        hero = QFrame()
        hero.setStyleSheet(
            "QFrame{background:#0B2A52;border:none;}"
            "QLabel{background:transparent;border:none;color:white;}"
        )
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(26, 22, 26, 22)
        hero_layout.setSpacing(5)

        overline = QLabel("FORM@PROSPECT  •  MISE À JOUR")
        overline.setStyleSheet(
            "color:#7CC0FF;font-size:10px;font-weight:900;letter-spacing:1px;"
        )
        title = QLabel("Une nouvelle version est disponible")
        title.setStyleSheet("font-size:23px;font-weight:900;")
        subtitle = QLabel(
            f"Version installée : {VERSION}   •   Nouvelle version : {info.version}"
        )
        subtitle.setStyleSheet("color:#D8E9FB;font-size:11px;")
        hero_layout.addWidget(overline)
        hero_layout.addWidget(title)
        hero_layout.addWidget(subtitle)
        root.addWidget(hero)

        body = QVBoxLayout()
        body.setContentsMargins(26, 22, 26, 22)
        body.setSpacing(14)

        if info.mandatory:
            required = QLabel(
                "Mise à jour requise • Cette version doit être installée pour continuer."
            )
            required.setWordWrap(True)
            required.setStyleSheet(
                "background:#FFF7ED;color:#9A3412;border:1px solid #FED7AA;"
                "border-radius:10px;padding:10px 12px;font-size:11px;font-weight:800;"
            )
            body.addWidget(required)

        notes_card = QFrame()
        notes_card.setStyleSheet(
            "QFrame{background:white;border:1px solid #DFE8F2;border-radius:14px;}"
            "QLabel{background:transparent;border:none;}"
        )
        notes_layout = QVBoxLayout(notes_card)
        notes_layout.setContentsMargins(16, 14, 16, 14)
        notes_layout.setSpacing(7)

        notes_title = QLabel("Nouveautés")
        notes_title.setStyleSheet(
            "color:#338CE4;font-size:10px;font-weight:900;letter-spacing:.8px;"
        )
        notes_layout.addWidget(notes_title)

        notes = self.info.notes or (
            "Améliorations et corrections de Form@Prospect.",
        )
        for item in notes:
            label = QLabel(f"•  {item}")
            label.setWordWrap(True)
            label.setStyleSheet(
                "color:#26364A;font-size:11px;padding:1px 0;"
            )
            notes_layout.addWidget(label)

        body.addWidget(notes_card)

        security = QLabel(
            "🔒 Le fichier est téléchargé en HTTPS et son empreinte SHA-256 "
            "est vérifiée avant l'installation."
        )
        security.setWordWrap(True)
        security.setStyleSheet(
            "background:#ECFDF5;color:#087A45;border:1px solid #A7F3D0;"
            "border-radius:10px;padding:10px 12px;font-size:10px;font-weight:700;"
        )
        body.addWidget(security)

        buttons = QHBoxLayout()
        buttons.addStretch()

        if not self.info.mandatory:
            later = QPushButton("Plus tard")
            later.setCursor(Qt.PointingHandCursor)
            later.setMinimumSize(105, 38)
            later.setStyleSheet(
                "QPushButton{background:white;color:#334155;border:1px solid #D6E0EA;"
                "border-radius:9px;padding:0 15px;font-weight:800;}"
                "QPushButton:hover{background:#F8FAFC;}"
            )
            later.clicked.connect(self.reject)
            buttons.addWidget(later)

        install = QPushButton("Installer la mise à jour")
        install.setCursor(Qt.PointingHandCursor)
        install.setMinimumSize(190, 38)
        install.setStyleSheet(
            "QPushButton{background:#338CE4;color:white;border:none;border-radius:9px;"
            "padding:0 17px;font-weight:900;}"
            "QPushButton:hover{background:#287FD4;}"
        )
        install.clicked.connect(self._install)
        buttons.addWidget(install)

        body.addLayout(buttons)
        root.addLayout(body)

    def _install(self) -> None:
        progress = QProgressDialog(
            "Téléchargement de la mise à jour…",
            "Annuler",
            0,
            100,
            self,
        )
        progress.setWindowTitle("Mise à jour Form@Prospect")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setValue(0)

        def on_progress(done: int, total: int) -> bool:
            if progress.wasCanceled():
                return False
            if total > 0:
                progress.setValue(min(99, int(done * 100 / total)))
            else:
                progress.setLabelText(
                    f"Téléchargement… {done / (1024 * 1024):.1f} Mo"
                )
            QApplication.processEvents()
            return not progress.wasCanceled()

        try:
            installer = self.service.download_installer(
                self.info,
                progress_callback=on_progress,
            )
            progress.setValue(100)
            progress.close()

            self.service.launch_installer(installer)
            self._install_started = True
            self.accept()
            QApplication.quit()

        except UpdateError as exc:
            progress.close()
            QMessageBox.critical(
                self,
                "Mise à jour impossible",
                str(exc),
            )

    def reject(self) -> None:
        if self.info.mandatory and not self._install_started:
            QApplication.quit()
            return
        super().reject()
