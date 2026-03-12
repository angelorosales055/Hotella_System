from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFrame
from PyQt6.QtCore import Qt, pyqtSignal

class Sidebar(QWidget):
    page = pyqtSignal(int)
    logout = pyqtSignal()

    def __init__(self, role):
        super().__init__()
        self.setFixedWidth(240)
        self.setStyleSheet("background-color: #1A1A1D;")
        l = QVBoxLayout()
        l.setContentsMargins(0, 0, 0, 20)
        l.setSpacing(10)

        bf = QFrame(styleSheet="background: #2C3E50; border: none;")
        bf.setFixedHeight(80)
        bl = QVBoxLayout(bf)
        lbl = QLabel(f"HOTELLA\n{role.upper()}", styleSheet="color: #FDB515; font-size: 20px; font-weight: 900;",
                     alignment=Qt.AlignmentFlag.AlignCenter)
        bl.addWidget(lbl)
        l.addWidget(bf)
        l.addSpacing(20)

        self.btns = []
        # Fixed: Correct menu items for each role
        if role == 'admin':
            opts = ["DASHBOARD", "MANAGEMENT", "ANALYTICS"]
        else:
            # Staff has 5 menu items matching 5 pages
            opts = ["HOME", "BOOK A ROOM", "SERVICES", "TASKS", "PAYMENT"]

        for i, t in enumerate(opts):
            b = QPushButton(t, checkable=True,
                            styleSheet="QPushButton {color:white; background:transparent; border:none; text-align:left; padding:15px 30px; font-weight:600} QPushButton:checked {background:#D4AC0D; color:black;}")
            b.clicked.connect(lambda _, x=i: self.nav(x))
            l.addWidget(b)
            self.btns.append(b)

        if self.btns: self.btns[0].setChecked(True)
        l.addStretch()
        lo = QPushButton("Log out", styleSheet="color:#7F8C8D; background:transparent; font-weight:bold; border:none")
        lo.clicked.connect(self.logout.emit)
        l.addWidget(lo)
        self.setLayout(l)

    def nav(self, i):
        for b in self.btns: b.setChecked(False)
        self.btns[i].setChecked(True)
        self.page.emit(i)