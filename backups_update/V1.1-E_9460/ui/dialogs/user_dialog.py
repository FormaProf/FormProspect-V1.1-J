from PySide6.QtWidgets import QComboBox,QDialog,QFormLayout,QHBoxLayout,QLabel,QLineEdit,QMessageBox,QPushButton,QVBoxLayout
from core.premium_theme import INPUT_STYLE,PRIMARY_BUTTON,SECONDARY_BUTTON,TEXT,MUTED
from services.auth_service import AuthService
class UserDialog(QDialog):
    def __init__(self,auth_service:AuthService,parent=None):
        super().__init__(parent);self.auth_service=auth_service;self.setWindowTitle("Ajouter un utilisateur");self.setFixedSize(500,570);self.setStyleSheet("QDialog{background:#F5F7FB;}"+INPUT_STYLE)
        root=QVBoxLayout(self);root.setContentsMargins(30,26,30,26);root.setSpacing(14);title=QLabel("Ajouter un utilisateur");title.setStyleSheet(f"font-size:23px;font-weight:900;color:{TEXT};");sub=QLabel("Créez un nouveau compte et attribuez-lui un rôle.");sub.setStyleSheet(f"color:{MUTED};font-size:12px;");root.addWidget(title);root.addWidget(sub)
        form=QFormLayout();form.setVerticalSpacing(12);form.setLabelAlignment(__import__('PySide6').QtCore.Qt.AlignLeft);self.first_name=QLineEdit();self.last_name=QLineEdit();self.email=QLineEdit();self.username=QLineEdit();self.password=QLineEdit();self.password.setEchoMode(QLineEdit.Password);self.role=QComboBox();self.role.addItems(AuthService.ROLES)
        for label,w in [("Prénom",self.first_name),("Nom",self.last_name),("E-mail",self.email),("Identifiant",self.username),("Mot de passe",self.password),("Rôle",self.role)]:form.addRow(label,w)
        if getattr(auth_service,"is_cloud",False):
            self.username.setVisible(False);self.password.setVisible(False)
            form.labelForField(self.username).setVisible(False);form.labelForField(self.password).setVisible(False)
            sub.setText("Invitez un collaborateur par e-mail et attribuez-lui un rôle.")
        root.addLayout(form);root.addStretch();actions=QHBoxLayout();actions.addStretch();cancel=QPushButton("Annuler");cancel.setStyleSheet(SECONDARY_BUTTON);cancel.clicked.connect(self.reject);create=QPushButton("Créer l'utilisateur");create.setStyleSheet(PRIMARY_BUTTON);create.clicked.connect(self._create);actions.addWidget(cancel);actions.addWidget(create);root.addLayout(actions)
    def _create(self):
        try:self.auth_service.create_user(self.username.text(),self.password.text(),first_name=self.first_name.text(),last_name=self.last_name.text(),email=self.email.text(),role=self.role.currentText())
        except Exception as e:QMessageBox.critical(self,"Création impossible",str(e));return
        self.accept()
