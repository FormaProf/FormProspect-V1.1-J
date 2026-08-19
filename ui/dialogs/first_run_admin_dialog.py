from PySide6.QtWidgets import QDialog,QFormLayout,QHBoxLayout,QLabel,QLineEdit,QMessageBox,QPushButton,QVBoxLayout
from core.constants import APP_NAME
from core.premium_theme import INPUT_STYLE,PRIMARY_BUTTON,TEXT,MUTED
from services.auth_service import AuthService
class FirstRunAdminDialog(QDialog):
    def __init__(self,auth_service:AuthService,parent=None):
        super().__init__(parent);self.auth_service=auth_service;self.setWindowTitle(f"Configuration initiale — {APP_NAME}");self.setModal(True);self.setFixedSize(560,610);self.setStyleSheet("QDialog{background:#F5F7FB;}"+INPUT_STYLE)
        root=QVBoxLayout(self);root.setContentsMargins(34,30,34,28);root.setSpacing(14);icon=QLabel("♙");icon.setStyleSheet("font-size:35px;color:#338CE4;");title=QLabel("Créer le premier administrateur");title.setStyleSheet(f"font-size:25px;font-weight:900;color:{TEXT};");sub=QLabel("Ce compte principal permettra d'administrer les utilisateurs, les rôles et la licence de Form@Prospect.");sub.setWordWrap(True);sub.setStyleSheet(f"font-size:13px;color:{MUTED};");root.addWidget(icon);root.addWidget(title);root.addWidget(sub)
        form=QFormLayout();form.setVerticalSpacing(12);self.first_name=QLineEdit();self.last_name=QLineEdit();self.email=QLineEdit();self.username=QLineEdit();self.password=QLineEdit();self.password.setEchoMode(QLineEdit.Password);self.confirm=QLineEdit();self.confirm.setEchoMode(QLineEdit.Password)
        for label,w in [("Prénom",self.first_name),("Nom",self.last_name),("E-mail",self.email),("Identifiant",self.username),("Mot de passe",self.password),("Confirmation",self.confirm)]:form.addRow(label,w)
        root.addLayout(form);root.addStretch();button=QPushButton("Créer le compte administrateur");button.setStyleSheet(PRIMARY_BUTTON);button.setFixedHeight(45);button.clicked.connect(self._create);root.addWidget(button)
    def _create(self):
        if self.password.text()!=self.confirm.text():QMessageBox.warning(self,"Mot de passe","Les deux mots de passe ne correspondent pas.");return
        try:self.auth_service.create_user(self.username.text(),self.password.text(),first_name=self.first_name.text(),last_name=self.last_name.text(),email=self.email.text(),role="Administrateur")
        except Exception as e:QMessageBox.critical(self,"Création impossible",str(e));return
        self.accept()
