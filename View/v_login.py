import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QFrame,
                             QToolButton)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QPen, QColor, QPainterPath


class LoginView(QWidget):
    success = pyqtSignal(str, str, str)

    def __init__(self, login_controller):
        super().__init__()
        self.ctrl = login_controller
        self.setWindowTitle('Hotella Login')
        self.setMinimumSize(900, 700)

        # --- Gradient Background ---
        self.setStyleSheet("""
            QWidget#LoginWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2C3E50, stop:1 #4CA1AF);
            }
        """)
        self.setObjectName("LoginWindow")

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addStretch()

        # --- Card Styling ---
        card = QFrame()
        card.setFixedWidth(420)
        card.setStyleSheet("""
            QFrame { 
                background-color: rgba(255, 255, 255, 0.95); 
                border-radius: 25px; 
                border: 1px solid rgba(0,0,0,0.1);
            }
        """)

        cl = QVBoxLayout()
        cl.setContentsMargins(50, 60, 50, 60)
        cl.setSpacing(25)

        logo_lbl = QLabel()
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        possible_paths = ["Hotella.png", "assets/Hotella.png", "assets/logo.png"]
        logo_found = False

        for path in possible_paths:
            if os.path.exists(path):
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    logo_lbl.setPixmap(pixmap.scaled(180, 180, Qt.AspectRatioMode.KeepAspectRatio,
                                                     Qt.TransformationMode.SmoothTransformation))
                    logo_found = True
                    break

        if not logo_found:
            logo_lbl.setText("HOTELLA")
            logo_lbl.setStyleSheet(
                "font-size: 32px; font-weight: bold; color: #2C3E50; border: none; background: transparent;")

        input_style = """
            QLineEdit {
                background-color: #F5F6FA; 
                border: 2px solid #E0E0E0; 
                border-radius: 12px; 
                padding: 0 15px;
                font-size: 15px;
                height: 55px;
                color: #2C3E50;
            }
            QLineEdit:focus {
                border: 2px solid #D4AF37; 
                background-color: #FFFFFF;
            }
        """

        pwd_container_style = """
            QFrame {
                background-color: #F5F6FA; 
                border: 2px solid #E0E0E0; 
                border-radius: 12px; 
            }
            QFrame:focus-within {
                border: 2px solid #D4AF37; 
                background-color: #FFFFFF;
            }
        """

        self.user = QLineEdit()
        self.user.setPlaceholderText("Username")
        self.user.setStyleSheet(input_style)

        self.pwd_frame = QFrame()
        self.pwd_frame.setFixedHeight(59)
        self.pwd_frame.setStyleSheet(pwd_container_style)

        pwd_layout = QHBoxLayout(self.pwd_frame)
        pwd_layout.setContentsMargins(15, 0, 10, 0)
        pwd_layout.setSpacing(5)

        self.pwd = QLineEdit()
        self.pwd.setPlaceholderText("Password")
        self.pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd.setStyleSheet("border: none; background: transparent; font-size: 15px; color: #2C3E50;")

        # 🟢 Generate Standard Vector Icons Programmatically
        self.eye_icon = self._create_eye_icon(hidden=False)
        self.eye_off_icon = self._create_eye_icon(hidden=True)

        self.peek_btn = QToolButton()
        self.peek_btn.setFixedSize(40, 40)
        self.peek_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.peek_btn.clicked.connect(self.toggle_password)

        self.update_peek_icon()

        pwd_layout.addWidget(self.pwd)
        pwd_layout.addWidget(self.peek_btn)

        self.pwd.returnPressed.connect(self.do_login)

        btn = QPushButton("SIGN IN")
        btn.setFixedHeight(60)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #D4AF37, stop:1 #FDB515);
                color: white; font-weight: bold; font-size: 18px; border-radius: 12px; border: none;
            } 
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #C09F32, stop:1 #E5A313); }
        """)
        btn.clicked.connect(self.do_login)

        cl.addWidget(logo_lbl)
        cl.addSpacing(20)
        cl.addWidget(self.user)
        cl.addWidget(self.pwd_frame)
        cl.addWidget(btn)
        card.setLayout(cl)

        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(card)
        row.addStretch()
        main_layout.addLayout(row)
        main_layout.addStretch()
        self.setLayout(main_layout)

    def _create_eye_icon(self, hidden=False):
        """Draws a standard vector eye icon natively using QPainter"""
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen = QPen(QColor("#7F8C8D"), 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        # Draw eye outline
        path = QPainterPath()
        path.moveTo(2, 12)
        path.quadTo(12, 4, 22, 12)
        path.quadTo(12, 20, 2, 12)
        painter.drawPath(path)

        # Draw pupil
        painter.drawEllipse(9, 9, 6, 6)

        # Draw slash if hidden
        if hidden:
            painter.drawLine(4, 4, 20, 20)

        painter.end()
        return QIcon(pixmap)

    def toggle_password(self):
        if self.pwd.echoMode() == QLineEdit.EchoMode.Password:
            self.pwd.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.update_peek_icon()

    def update_peek_icon(self):
        is_password = (self.pwd.echoMode() == QLineEdit.EchoMode.Password)
        self.peek_btn.setIcon(self.eye_icon if is_password else self.eye_off_icon)
        self.peek_btn.setIconSize(QSize(22, 22))
        self.peek_btn.setStyleSheet("border: none; background: transparent;")

    def do_login(self):
        u, p = self.user.text().strip(), self.pwd.text().strip()
        ok, role, real_name = self.ctrl.login(u, p)
        if ok:
            self.success.emit(role, u, real_name)
        else:
            QMessageBox.warning(self, "Login Failed", "Invalid credentials.")
            self.pwd.clear()