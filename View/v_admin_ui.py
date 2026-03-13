from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QDateEdit,
                             QMessageBox, QDialog, QFormLayout, QLineEdit, QTabWidget, QAbstractItemView,
                             QComboBox, QSpinBox, QScrollArea, QGroupBox, QCheckBox)
from PyQt6.QtCore import Qt, QDate, QTimer, QTime, pyqtSignal
from PyQt6.QtGui import QTextDocument
from PyQt6.QtPrintSupport import QPrinter
from datetime import datetime
import calendar

# ── Shared styles ─────────────────────────────────────────────────────────────
TABLE_STYLE = """
    QTableWidget {
        background-color: white; color: #2C3E50;
        border: 1px solid #BDC3C7; border-radius: 5px;
        gridline-color: #ECF0F1; font-size: 13px;
    }
    QHeaderView::section {
        background-color: #2C3E50; color: white;
        font-weight: bold; border: none; padding: 10px; font-size: 13px;
    }
    QTableWidget::item { padding: 5px; }
    QTableWidget::item:hover { background-color: #EAFAF1; color: #2C3E50; }
    QTableWidget::item:selected { background-color: #3498DB; color: white; }
"""

INPUT_STYLE = """
    QLineEdit, QComboBox, QSpinBox {
        padding: 8px; border: 1px solid #BDC3C7;
        border-radius: 5px; font-size: 13px;
        background-color: white; color: #2C3E50;
    }
    QComboBox::drop-down { border: none; width: 20px; }
    QComboBox QAbstractItemView {
        background-color: white; color: #2C3E50;
        selection-background-color: #3498DB; selection-color: white;
        border: 1px solid #BDC3C7;
    }
"""

GROUP_STYLE = """
    QGroupBox {
        font-weight: bold; border: 1px solid #BDC3C7; margin-top: 10px;
        color: #2C3E50; background-color: white; border-radius: 5px;
    }
    QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
"""

MESSAGEBOX_STYLE = """
    QMessageBox { background-color: white; color: #2C3E50; }
    QMessageBox QLabel { color: #2C3E50; font-weight: bold; font-size: 14px; }
    QMessageBox QPushButton { background-color: #3498DB; color: white; padding: 6px 20px; border-radius: 4px; font-weight: bold; }
    QMessageBox QPushButton:hover { background-color: #2980B9; }
"""


def make_table_readonly(table):
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)


# ── Clickable dashboard card ──────────────────────────────────────────────────
class ClickableFrame(QFrame):
    clicked = pyqtSignal(str)

    def __init__(self, card_type, parent=None):
        super().__init__(parent)
        self.card_type = card_type
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        self.clicked.emit(self.card_type)
        super().mousePressEvent(event)


# ── Admin Home (Dashboard) ────────────────────────────────────────────────────
class AdminHome(QWidget):
    switch_tab_signal = pyqtSignal(str)

    def __init__(self, ctrl):
        super().__init__()
        self.ctrl = ctrl
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background-color: #F4F6F9;")
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(30, 30, 30, 30)
        self.layout.setSpacing(20)
        self.setLayout(self.layout)

        self.load_charts_module()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_clock)
        self.timer.start(1000)
        self.refresh_data()

    def load_charts_module(self):
        try:
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FC
            from matplotlib.figure import Figure as Fig
            self.FigureCanvas = FC
            self.Figure = Fig
            self.plt_available = True
        except ImportError:
            self.plt_available = False

    def refresh_data(self):
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.create_header()
        self.create_stats()

        if getattr(self, 'plt_available', False):
            self.create_trend_chart()

        self.layout.addStretch()
        lbl_footer = QLabel("© 2026 Hotella Management System. All rights reserved.")
        lbl_footer.setStyleSheet("color: #95A5A6; font-size: 12px; font-weight: bold;")
        lbl_footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(lbl_footer)

    def create_header(self):
        header_widget = QWidget()
        h = QHBoxLayout(header_widget)
        h.setContentsMargins(0, 0, 0, 20)

        lbl_title = QLabel("Hotella Dashboard")
        lbl_title.setStyleSheet("font-size: 28px; font-weight: 900; color: #2C3E50; background: transparent;")
        h.addWidget(lbl_title)
        h.addStretch()

        self.time_lbl = QLabel()
        self.time_lbl.setStyleSheet("font-size: 24px; color: #2C3E50; background: transparent; font-weight: bold;")
        self.date_lbl = QLabel()
        self.date_lbl.setStyleSheet("font-size: 14px; color: #7F8C8D; background: transparent; font-weight: bold;")

        r = QVBoxLayout()
        r.setAlignment(Qt.AlignmentFlag.AlignRight)
        r.addWidget(self.time_lbl)
        r.addWidget(self.date_lbl)
        h.addLayout(r)

        self.update_clock()
        self.layout.addWidget(header_widget)

    def update_clock(self):
        if hasattr(self, 'time_lbl'):
            self.time_lbl.setText(QTime.currentTime().toString('hh:mm:ss AP'))
            self.date_lbl.setText(datetime.now().strftime('%A, %B %d, %Y'))

    def create_stats(self):
        gl = QGridLayout()
        gl.setSpacing(20)

        # Controller supplies all values; view only renders them
        stats = self.ctrl.get_dashboard_stats()

        cards_data = [
            ("TOTAL BOOKINGS",            stats.get('bookings', 0),                 "#3498DB", "bookings"),
            (f"REVENUE ({stats.get('year')})", f"₱{stats.get('revenue', 0):,}",    "#2ECC71", "analytics"),
            ("TOTAL EMPLOYEES",           stats.get('employees', 0),                "#E67E22", "employees"),
            ("TOTAL ROOMS",               stats.get('rooms', 0),                    "#9B59B6", "rooms"),
        ]

        for i, (label, value, color, c_type) in enumerate(cards_data):
            card = ClickableFrame(c_type)
            card.setFixedHeight(140)
            card.setStyleSheet(f"background-color: {color}; border-radius: 10px; color: white;")
            card.clicked.connect(self.switch_tab_signal.emit)

            cl = QGridLayout(card)
            cl.setContentsMargins(20, 20, 20, 20)

            lbl_title = QLabel(str(label))
            lbl_title.setStyleSheet("font-size: 14px; font-weight: bold; background: transparent; color: rgba(255,255,255,0.9);")
            lbl_title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            lbl_title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

            lbl_val = QLabel(str(value))
            lbl_val.setStyleSheet("font-size: 40px; font-weight: 800; background: transparent;")
            lbl_val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
            lbl_val.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

            cl.addWidget(lbl_title, 0, 0)
            cl.addWidget(lbl_val, 1, 0)
            gl.addWidget(card, i // 2, i % 2)

        self.layout.addLayout(gl)

    def create_trend_chart(self):
        frame = QFrame()
        frame.setStyleSheet("background: white; border-radius: 10px; border: 1px solid #BDC3C7;")
        frame.setMinimumHeight(320)
        fl = QVBoxLayout(frame)

        lbl = QLabel(f"Revenue Trend ({datetime.now().year})")
        lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #2C3E50; border: none; padding-left: 10px; padding-top: 10px;")
        fl.addWidget(lbl)

        fig = self.Figure(figsize=(8, 2.5), dpi=100)
        ax  = fig.add_subplot(111)

        # Controller provides ready-made data; view only plots
        data   = self.ctrl.get_monthly_revenue(datetime.now().year)
        x_vals = [d['month_name'] for d in data]
        y_vals = [d['total_rev']  for d in data]

        ax.plot(x_vals, y_vals, marker='o', linestyle='-', color='#3498DB', linewidth=2.5, markersize=7)
        ax.fill_between(x_vals, y_vals, alpha=0.1, color='#3498DB')
        ax.set_ylabel("Total Revenue (₱)")
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        fig.tight_layout()

        canvas = self.FigureCanvas(fig)
        fl.addWidget(canvas)
        self.layout.addWidget(frame)


# ── Admin Management ──────────────────────────────────────────────────────────
class AdminManagement(QWidget):
    def __init__(self, ctrl):
        super().__init__()
        self.ctrl = ctrl
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background-color: #F4F6F9;")
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #BDC3C7; background: white; border-radius: 5px; }
            QTabBar::tab { background: #E0E0E0; color: #555; padding: 10px 25px; font-weight: bold;
                           border-top-left-radius: 5px; border-top-right-radius: 5px; margin-right: 2px; }
            QTabBar::tab:selected { background: #2C3E50; color: white; border-bottom: 3px solid #FDB515; }
        """)

        self.pages = [
            BookingTab(ctrl),
            RoomTab(ctrl),
            EmployeesTab(ctrl),
            RoomMaintenanceTab(ctrl),
            HistoryAndServicesTab(ctrl),
            PaymentReportTab(ctrl),
            SystemLogsTab(ctrl),
        ]
        titles = ["Bookings", "Rooms", "Employees", "Maintenance",
                  "History & Services", "Payments", "System Logs"]
        for p, t in zip(self.pages, titles):
            self.tabs.addTab(p, t)

        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def refresh_data(self):
        for p in self.pages:
            if hasattr(p, 'load'):         p.load()
            if hasattr(p, 'refresh_data'): p.refresh_data()

    def navigate_to(self, tab_name):
        mapping = {"bookings": 0, "rooms": 1, "employees": 2}
        if tab_name in mapping:
            self.tabs.setCurrentIndex(mapping[tab_name])


# ── Employees Tab ─────────────────────────────────────────────────────────────
class EmployeesTab(QWidget):
    def __init__(self, ctrl):
        super().__init__()
        self.ctrl = ctrl
        layout = QHBoxLayout(self)
        self.t = QTableWidget(0, 6)
        self.t.setHorizontalHeaderLabels(["ID", "Name", "Role", "Contact", "Status", "Username"])
        self.t.setStyleSheet(TABLE_STYLE)
        make_table_readonly(self.t)
        self.t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.t, stretch=2)

        ctrl_panel = QVBoxLayout()
        gb_add = QGroupBox("Add New Employee")
        gb_add.setStyleSheet(GROUP_STYLE)
        fl = QVBoxLayout(gb_add)
        fl.setSpacing(10)

        self.inp_name    = QLineEdit(placeholderText="Full Name")
        self.inp_name.setStyleSheet(INPUT_STYLE)
        self.inp_contact = QLineEdit(placeholderText="Contact Number")
        self.inp_contact.setStyleSheet(INPUT_STYLE)

        self.cb_role = QComboBox()
        self.cb_role.addItems(["Cleaner", "Receptionist", "Room Service"])
        self.cb_role.setStyleSheet(INPUT_STYLE)
        self.cb_role.currentTextChanged.connect(self.toggle_account_fields)

        fl.addWidget(QLabel("Role:", styleSheet="color:#555; font-weight:bold;"))
        fl.addWidget(self.cb_role)
        fl.addWidget(self.inp_name)
        fl.addWidget(self.inp_contact)

        self.gb_account = QGroupBox("System Login")
        self.gb_account.setStyleSheet("border:none; margin-top:5px;")
        gl = QVBoxLayout(self.gb_account)
        gl.setContentsMargins(0, 0, 0, 0)
        self.inp_user = QLineEdit(placeholderText="Username")
        self.inp_user.setStyleSheet(INPUT_STYLE)
        self.inp_pass = QLineEdit(placeholderText="Password")
        self.inp_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_pass.setStyleSheet(INPUT_STYLE)
        gl.addWidget(self.inp_user)
        gl.addWidget(self.inp_pass)
        fl.addWidget(self.gb_account)
        self.gb_account.hide()

        btn_add = QPushButton("Add Employee")
        btn_add.setStyleSheet("background: #27AE60; color: white; padding: 10px; font-weight: bold; border-radius: 5px;")
        btn_add.clicked.connect(self.add_employee)
        fl.addWidget(btn_add)
        ctrl_panel.addWidget(gb_add)

        gb_act = QGroupBox("Manage Status")
        gb_act.setStyleSheet(GROUP_STYLE)
        al = QVBoxLayout(gb_act)
        lbl_hint = QLabel(
            "To remove access, set status to Inactive.\nDo not delete employees to preserve history.",
            styleSheet="color: #7F8C8D; font-size: 11px; font-style: italic;"
        )
        lbl_hint.setWordWrap(True)
        al.addWidget(lbl_hint)

        btn_active = QPushButton("Set Active")
        btn_active.setStyleSheet("background: #3498DB; color: white; padding: 10px; font-weight: bold;")
        btn_active.clicked.connect(lambda: self.set_status("Active"))
        btn_inactive = QPushButton("Set Inactive")
        btn_inactive.setStyleSheet("background: #95A5A6; color: white; padding: 10px; font-weight: bold;")
        btn_inactive.clicked.connect(lambda: self.set_status("Inactive"))
        al.addWidget(btn_active)
        al.addWidget(btn_inactive)
        ctrl_panel.addWidget(gb_act)
        ctrl_panel.addStretch()
        layout.addLayout(ctrl_panel, stretch=1)

        self.toggle_account_fields(self.cb_role.currentText())
        self.load()

    def toggle_account_fields(self, role):
        if role == "Receptionist":
            self.gb_account.show()
        else:
            self.gb_account.hide()
            self.inp_user.clear()
            self.inp_pass.clear()

    def load(self):
        self.t.setRowCount(0)
        for e in self.ctrl.get_employees():
            r = self.t.rowCount()
            self.t.insertRow(r)
            self.t.setItem(r, 0, QTableWidgetItem(str(e[0])))
            self.t.setItem(r, 1, QTableWidgetItem(str(e[1])))
            self.t.setItem(r, 2, QTableWidgetItem(str(e[2])))
            self.t.setItem(r, 3, QTableWidgetItem(str(e[3])))
            status = str(e[4]) if e[4] else "Active"
            s_item = QTableWidgetItem(status)
            if status == "Inactive":   s_item.setForeground(Qt.GlobalColor.red)
            elif status == "Active":   s_item.setForeground(Qt.GlobalColor.green)
            elif status == "Busy":     s_item.setForeground(Qt.GlobalColor.blue)
            self.t.setItem(r, 4, s_item)
            self.t.setItem(r, 5, QTableWidgetItem(str(e[5]) if e[5] else "---"))

    def show_msg(self, title, txt, icon):
        msg = QMessageBox(self)
        msg.setWindowTitle(title); msg.setText(txt); msg.setIcon(icon)
        msg.setStyleSheet(MESSAGEBOX_STYLE); msg.exec()

    def add_employee(self):
        success, msg = self.ctrl.add_new_employee(
            self.inp_name.text(), self.cb_role.currentText(),
            self.inp_contact.text(), self.inp_user.text(), self.inp_pass.text()
        )
        if success:
            self.show_msg("Success", msg, QMessageBox.Icon.Information)
            self.inp_name.clear(); self.inp_contact.clear()
            self.inp_user.clear(); self.inp_pass.clear()
            self.load()
        else:
            self.show_msg("Error", msg, QMessageBox.Icon.Warning)

    def set_status(self, status):
        row = self.t.currentRow()
        if row < 0:
            return self.show_msg("Error", "Select an employee.", QMessageBox.Icon.Warning)
        res, msg = self.ctrl.set_employee_status(self.t.item(row, 0).text(), status)
        if res: self.load()
        else:   self.show_msg("Error", msg, QMessageBox.Icon.Warning)


# ── Room Maintenance Tab ──────────────────────────────────────────────────────
class RoomMaintenanceTab(QWidget):
    def __init__(self, ctrl):
        super().__init__()
        self.ctrl = ctrl
        layout = QHBoxLayout(self)
        self.t = QTableWidget(0, 3)
        self.t.setHorizontalHeaderLabels(["Room No", "Type", "Status"])
        self.t.setStyleSheet(TABLE_STYLE)
        make_table_readonly(self.t)
        self.t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.t.cellClicked.connect(self.on_row_click)
        self.t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.t, stretch=2)

        ctrl_panel = QVBoxLayout()
        gb1 = QGroupBox("Availability Control")
        gb1.setStyleSheet(GROUP_STYLE)
        gl1 = QVBoxLayout(gb1)
        btn_maint = QPushButton("Set to Maintenance")
        btn_maint.setStyleSheet("background: #E74C3C; color: white; padding: 10px; font-weight: bold;")
        btn_maint.clicked.connect(lambda: self.set_status("Maintenance"))
        btn_avail = QPushButton("Set Available")
        btn_avail.setStyleSheet("background: #27AE60; color: white; padding: 10px; font-weight: bold;")
        btn_avail.clicked.connect(lambda: self.set_status("Vacant"))
        gl1.addWidget(btn_maint); gl1.addWidget(btn_avail)
        ctrl_panel.addWidget(gb1)

        gb2 = QGroupBox("Upgrade / Change Room")
        gb2.setStyleSheet(GROUP_STYLE)
        gl2 = QVBoxLayout(gb2)
        gl2.addWidget(QLabel("New Room Type:", styleSheet="color: #2C3E50; font-weight: bold;"))
        self.cb_type = QComboBox()
        self.cb_type.addItems(["Single", "Double", "Queen", "King", "Suite"])
        self.cb_type.setStyleSheet(INPUT_STYLE)
        gl2.addWidget(self.cb_type)
        btn_update = QPushButton("Update Type")
        btn_update.setStyleSheet("background: #3498DB; color: white; padding: 10px; font-weight: bold;")
        btn_update.clicked.connect(self.update_type)
        gl2.addWidget(btn_update)
        ctrl_panel.addWidget(gb2)
        ctrl_panel.addStretch()
        layout.addLayout(ctrl_panel, stretch=1)

        self.selected_room = None
        self.load()

    def load(self):
        self.t.setRowCount(0)
        self.selected_room = None
        for r in self.ctrl.get_all_rooms():
            row = self.t.rowCount()
            self.t.insertRow(row)
            self.t.setItem(row, 0, QTableWidgetItem(str(r[0])))
            self.t.setItem(row, 1, QTableWidgetItem(str(r[1])))
            self.t.setItem(row, 2, QTableWidgetItem(str(r[2])))
            if str(r[2]) == "Maintenance":
                for i in range(3): self.t.item(row, i).setBackground(Qt.GlobalColor.lightGray)

    def on_row_click(self, row, col):
        self.selected_room = self.t.item(row, 0).text()
        self.cb_type.setCurrentText(self.t.item(row, 1).text())

    def show_message(self, title, text, icon):
        msg = QMessageBox(self)
        msg.setWindowTitle(title); msg.setText(text); msg.setIcon(icon)
        msg.setStyleSheet(MESSAGEBOX_STYLE); msg.exec()

    def set_status(self, status):
        if not self.selected_room:
            return self.show_message("Error", "Select a room from the table first.", QMessageBox.Icon.Warning)
        s, m = self.ctrl.set_room_status(self.selected_room, status)
        if s: self.show_message("Success", m, QMessageBox.Icon.Information); self.load()
        else: self.show_message("Blocked", m, QMessageBox.Icon.Warning)

    def update_type(self):
        if not self.selected_room:
            return self.show_message("Error", "Select a room from the table first.", QMessageBox.Icon.Warning)
        s, m = self.ctrl.change_room_type(self.selected_room, self.cb_type.currentText())
        if s: self.show_message("Success", m, QMessageBox.Icon.Information); self.load()
        else: self.show_message("Blocked", m, QMessageBox.Icon.Warning)


# ── Booking Tab ───────────────────────────────────────────────────────────────
class BookingTab(QWidget):
    def __init__(self, ctrl):
        super().__init__()
        self.ctrl = ctrl
        self.setLayout(QVBoxLayout())
        self.t = QTableWidget(0, 7)
        self.t.setHorizontalHeaderLabels(["ID", "Name", "Email", "Phone", "Address", "Type", "Date"])
        self.t.setStyleSheet(TABLE_STYLE)
        make_table_readonly(self.t)
        self.t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.layout().addWidget(self.t)
        self.load()

    def load(self):
        self.t.setRowCount(0)
        for b in self.ctrl.get_filtered_bookings("2020-01-01", "2030-12-31"):
            r = self.t.rowCount()
            self.t.insertRow(r)
            self.t.setItem(r, 0, QTableWidgetItem(f"B{b[0]:05d}"))
            for i in range(1, 7):
                self.t.setItem(r, i, QTableWidgetItem(str(b[i])))


# ── Room Tab ──────────────────────────────────────────────────────────────────
class RoomTab(QWidget):
    def __init__(self, ctrl):
        super().__init__()
        self.ctrl = ctrl
        self.setLayout(QVBoxLayout())
        self.t = QTableWidget(0, 3)
        self.t.setHorizontalHeaderLabels(["No", "Desc", "Status"])
        self.t.setStyleSheet(TABLE_STYLE)
        make_table_readonly(self.t)
        self.t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.layout().addWidget(self.t)
        btn = QPushButton("Add Room")
        btn.clicked.connect(self.add)
        self.layout().addWidget(btn)
        self.load()

    def load(self):
        self.t.setRowCount(0)
        for r in self.ctrl.get_all_rooms():
            row = self.t.rowCount()
            self.t.insertRow(row)
            for i in range(3): self.t.setItem(row, i, QTableWidgetItem(str(r[i])))

    def add(self):
        d = QDialog(self)
        f = QFormLayout(d)
        n = QLineEdit(); de = QLineEdit(); s = QLineEdit("Vacant")
        for w in (n, de, s): w.setStyleSheet(INPUT_STYLE)
        f.addRow("No", n); f.addRow("Desc", de); f.addRow("Stat", s)
        b = QPushButton("Save")
        b.clicked.connect(lambda: [self.ctrl.save_room(True, [n.text(), de.text(), s.text()]), d.accept(), self.load()])
        f.addRow(b)
        d.exec()


# ── System Logs Tab ───────────────────────────────────────────────────────────
class SystemLogsTab(QWidget):
    """
    Purely renders the unified log data returned by the controller.
    All merging / sorting logic was moved to AdminController.get_unified_system_logs().
    """

    def __init__(self, ctrl):
        super().__init__()
        self.ctrl = ctrl
        self.setLayout(QVBoxLayout())

        btn_refresh = QPushButton("Refresh Logs")
        btn_refresh.setStyleSheet(
            "background: #2C3E50; color: white; padding: 8px; border-radius: 5px; font-weight: bold; margin-bottom: 10px;"
        )
        btn_refresh.clicked.connect(self.load)
        self.layout().addWidget(btn_refresh)

        self.t = QTableWidget(0, 5)
        self.t.setHorizontalHeaderLabels(
            ["Booking ID", "Target (Guest/Room)", "Action Performed", "Performed By", "Timestamp"]
        )
        self.t.setStyleSheet(TABLE_STYLE)
        make_table_readonly(self.t)
        self.t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.layout().addWidget(self.t)
        self.load()

    def load(self):
        self.t.setRowCount(0)
        try:
            logs = self.ctrl.get_unified_system_logs()
        except Exception as e:
            print(f"[SystemLogsTab] Error loading logs: {e}")
            logs = []

        for log in logs:
            r = self.t.rowCount()
            self.t.insertRow(r)

            bid = log['bid']
            try:
                bid_str = f"B{int(bid):05d}" if bid and int(bid) > 0 else "---"
            except (ValueError, TypeError):
                bid_str = str(bid) if bid else "---"

            self.t.setItem(r, 0, QTableWidgetItem(bid_str))
            self.t.setItem(r, 1, QTableWidgetItem(log['target']))
            self.t.setItem(r, 2, QTableWidgetItem(log['action']))
            self.t.setItem(r, 3, QTableWidgetItem(log['staff']))
            self.t.setItem(r, 4, QTableWidgetItem(log['time']))


# ── History & Services Tab ────────────────────────────────────────────────────
class HistoryAndServicesTab(QWidget):
    def __init__(self, ctrl):
        super().__init__()
        self.ctrl = ctrl
        l = QVBoxLayout(self)

        h = QHBoxLayout()
        l_lbl = QLabel("Search Room Number:", styleSheet="color:#2C3E50; font-weight:bold; font-size: 14px;")
        self.inp = QLineEdit(placeholderText="e.g. 101")
        self.inp.setStyleSheet(INPUT_STYLE + " padding: 10px; font-size: 14px;")
        self.inp.textChanged.connect(self.search)
        h.addWidget(l_lbl); h.addWidget(self.inp); h.addStretch()
        l.addLayout(h)

        self.t_unified = QTableWidget(0, 8)
        self.t_unified.setHorizontalHeaderLabels(
            ["Room", "Type", "Date", "Booking ID", "Guest Name", "Action / Service", "Duration", "Cost"]
        )
        self.t_unified.setStyleSheet(TABLE_STYLE)
        make_table_readonly(self.t_unified)
        self.t_unified.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        l.addWidget(self.t_unified)

        self.all_services = []
        self.all_history  = []
        self.load()

    def load(self):
        try:
            self.all_services = self.ctrl.get_all_services() or []
            self.all_history  = self.ctrl.get_all_room_history() or []
        except AttributeError:
            self.all_services = []
            self.all_history  = []
            QMessageBox.warning(self, "Backend Update Required",
                                "Please add 'get_all_room_history' to your AdminController.")
        except Exception as e:
            self.all_services = []
            self.all_history  = []
            print(f"Error loading history: {e}")
        self.search()

    def search(self):
        rid = self.inp.text().strip().lower()
        self.t_unified.setRowCount(0)

        unified_data = []
        guest_map    = {}

        for h in self.all_history:
            room_num = str(h[0])
            guest_map[h[1]] = str(h[2])
            if rid and rid not in room_num.lower():
                continue
            unified_data.append({
                'sort_date': str(h[3]),
                'room':      room_num,
                'type':      'Booking',
                'date':      str(h[3]),
                'bid':       f"B{h[1]:05d}",
                'guest':     str(h[2]),
                'action':    str(h[5]),
                'duration':  f"{h[4]} Days",
                'cost':      "---",
            })

        for s in self.all_services:
            room_num = str(s[2])
            if rid and rid not in room_num.lower():
                continue
            bid_int = s[1]
            bid_str = f"B{bid_int:05d}" if isinstance(bid_int, int) else str(bid_int)
            unified_data.append({
                'sort_date': str(s[5]),
                'room':      room_num,
                'type':      'Service',
                'date':      str(s[5]),
                'bid':       bid_str,
                'guest':     guest_map.get(bid_int, "Unknown"),
                'action':    str(s[3]),
                'duration':  "---",
                'cost':      f"₱{s[4]:,}",
            })

        unified_data.sort(key=lambda x: x['sort_date'], reverse=True)

        from PyQt6.QtGui import QFont
        bold_font = QFont()
        bold_font.setBold(True)

        for row_data in unified_data:
            r = self.t_unified.rowCount()
            self.t_unified.insertRow(r)

            type_item = QTableWidgetItem(row_data['type'])
            type_item.setFont(bold_font)
            if row_data['type'] == 'Booking':
                type_item.setForeground(Qt.GlobalColor.blue)
            else:
                type_item.setForeground(Qt.GlobalColor.darkYellow)

            self.t_unified.setItem(r, 0, QTableWidgetItem(row_data['room']))
            self.t_unified.setItem(r, 1, type_item)
            self.t_unified.setItem(r, 2, QTableWidgetItem(row_data['date']))
            self.t_unified.setItem(r, 3, QTableWidgetItem(row_data['bid']))
            self.t_unified.setItem(r, 4, QTableWidgetItem(row_data['guest']))
            self.t_unified.setItem(r, 5, QTableWidgetItem(row_data['action']))

            dur_item = QTableWidgetItem(row_data['duration'])
            dur_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.t_unified.setItem(r, 6, dur_item)

            cost_item = QTableWidgetItem(row_data['cost'])
            if row_data['cost'] != "---":
                cost_item.setForeground(Qt.GlobalColor.darkGreen)
                cost_item.setFont(bold_font)
            cost_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.t_unified.setItem(r, 7, cost_item)


# ── Payment Report Tab ────────────────────────────────────────────────────────
class PaymentReportTab(QWidget):
    def __init__(self, ctrl):
        super().__init__()
        self.ctrl = ctrl
        self.setLayout(QVBoxLayout())
        self.t = QTableWidget(0, 10)
        self.t.setHorizontalHeaderLabels(
            ["Date", "Booking ID", "Guest", "Room Charge", "Service Fee",
             "Penalties", "Total", "Method", "Staff", "Remark"]
        )
        self.t.setStyleSheet(TABLE_STYLE)
        make_table_readonly(self.t)
        self.t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.layout().addWidget(self.t)
        self.load()

    def load(self):
        self.t.setRowCount(0)
        try:
            payments = self.ctrl.get_all_payments() or []
        except Exception:
            payments = []

        for p in payments:
            r = self.t.rowCount()
            self.t.insertRow(r)
            processed_by = p[10] if len(p) > 10 else "---"
            remarks      = p[11] if len(p) > 11 else "Payment"
            bid_str      = f"B{p[1]:05d}" if isinstance(p[1], int) else str(p[1])
            try:
                penalty = max(0, float(p[5]) - (float(p[3]) + float(p[4])))
            except Exception:
                penalty = 0

            items = [
                str(p[7]), bid_str, str(p[2]),
                f"₱{int(p[3]):,}", f"₱{int(p[4]):,}",
                f"₱{int(penalty):,}", f"₱{int(p[5]):,}",
                str(p[6]), str(processed_by), str(remarks),
            ]
            for i, v in enumerate(items):
                item = QTableWidgetItem(str(v))
                if i == 5 and penalty > 0:
                    item.setForeground(Qt.GlobalColor.red)
                    from PyQt6.QtGui import QFont
                    font = QFont(); font.setBold(True)
                    item.setFont(font)
                self.t.setItem(r, i, item)


# ── Export Report Dialog ──────────────────────────────────────────────────────
class ExportReportDialog(QDialog):
    def __init__(self, parent, year, month, admin_name="Admin"):
        super().__init__(parent)
        self.setWindowTitle("Export Custom Report")
        self.setFixedSize(350, 340)
        self.options       = {}
        self.generated_by  = admin_name

        l = QVBoxLayout(self)
        l.setContentsMargins(25, 25, 25, 25)
        l.setSpacing(15)

        period = f"{month} {year}" if month != "All" else f"Annual {year}"
        l.addWidget(QLabel(f"Report Period: {period}",
                           styleSheet="font-weight: bold; font-size: 16px; color: #2C3E50;"))
        l.addWidget(QLabel(f"Generated by: {admin_name}",
                           styleSheet="color: #E67E22; font-weight: bold; font-size: 12px;"))
        l.addWidget(QLabel("Select details to include in the PDF:",
                           styleSheet="color: #7F8C8D; margin-bottom: 10px;"))

        self.chk_financial = QCheckBox("Financial Summary (Revenue)")
        self.chk_financial.setChecked(True)
        self.chk_financial.setStyleSheet("font-size: 14px; padding: 5px; color: #2C3E50;")
        self.chk_rooms = QCheckBox("Room Utilization & Analytics")
        self.chk_rooms.setChecked(True)
        self.chk_rooms.setStyleSheet("font-size: 14px; padding: 5px; color: #2C3E50;")
        self.chk_logs = QCheckBox("Itemized Transaction Logs")
        self.chk_logs.setStyleSheet("font-size: 14px; padding: 5px; color: #2C3E50;")

        l.addWidget(self.chk_financial)
        l.addWidget(self.chk_rooms)
        l.addWidget(self.chk_logs)
        l.addStretch()

        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("padding: 10px; background: #95A5A6; color: white; border-radius: 5px; font-weight: bold;")
        btn_cancel.clicked.connect(self.reject)
        btn_export = QPushButton("Generate PDF")
        btn_export.setStyleSheet("padding: 10px; background: #E67E22; color: white; border-radius: 5px; font-weight: bold;")
        btn_export.clicked.connect(self.confirm_export)
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_export)
        l.addLayout(btn_box)

    def confirm_export(self):
        self.options = {
            'financial': self.chk_financial.isChecked(),
            'rooms':     self.chk_rooms.isChecked(),
            'logs':      self.chk_logs.isChecked(),
        }
        if not any(self.options.values()):
            QMessageBox.warning(self, "Warning", "Please select at least one detail to export.")
            return
        self.accept()


# ── Admin Summary (Analytics) ─────────────────────────────────────────────────
class AdminSummary(QWidget):
    def __init__(self, ctrl, admin_name="Admin"):
        super().__init__()
        self.ctrl       = ctrl
        self.admin_name = admin_name
        self.available_data = {}
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background-color: #F4F6F9;")
        self.figures     = {}
        self.plt         = None
        self.MaxNLocator = None
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(10)
        self.setLayout(self.main_layout)
        self.setup_header()
        self.setup_financial_banner()
        self.setup_content()
        self.load_charts_module()
        self.populate_filters()

    def load_charts_module(self):
        try:
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FC
            from matplotlib.figure import Figure as Fig
            import matplotlib.pyplot as plt
            from matplotlib.ticker import MaxNLocator
            self.plt         = plt
            self.FigureCanvas = FC
            self.Figure       = Fig
            self.MaxNLocator  = MaxNLocator
        except ImportError:
            pass

    def setup_header(self):
        h = QHBoxLayout()
        h.addWidget(QLabel("Analytics Dashboard",
                           styleSheet="font-size: 24px; font-weight: 800; color: #2C3E50;"))
        h.addStretch()
        self.cb_year = QComboBox()
        self.cb_year.setStyleSheet(INPUT_STYLE)
        self.cb_year.currentTextChanged.connect(self.on_year_changed)
        self.cb_month = QComboBox()
        self.cb_month.setStyleSheet(INPUT_STYLE)
        self.cb_month.currentIndexChanged.connect(self.load_data)

        btn_pdf = QPushButton("Export PDF")
        btn_pdf.setStyleSheet("background: #E67E22; color: white; padding: 5px 15px; font-weight: bold; border-radius: 5px;")
        btn_pdf.clicked.connect(self.export_pdf)

        h.addWidget(QLabel("Year:",  styleSheet="color:#555; font-weight:bold;"))
        h.addWidget(self.cb_year)
        h.addWidget(QLabel("Month:", styleSheet="color:#555; font-weight:bold;"))
        h.addWidget(self.cb_month)
        h.addWidget(btn_pdf)
        self.main_layout.addLayout(h)

    def setup_financial_banner(self):
        self.banner = QFrame()
        self.banner.setFixedHeight(90)
        self.banner.setStyleSheet("background: white; border-radius: 10px; border: 1px solid #BDC3C7;")
        layout = QHBoxLayout(self.banner)
        layout.setContentsMargins(20, 10, 20, 10)
        self.lbl_month_name = QLabel("Current Overview")
        self.lbl_month_name.setStyleSheet("font-size: 16px; font-weight: bold; color: #7F8C8D;")
        layout.addWidget(self.lbl_month_name)
        layout.addStretch()
        self.lbl_room_rev = QLabel("Room Rev: ₱0")
        self.lbl_room_rev.setStyleSheet("font-size: 14px; font-weight: bold; color: #27AE60; background: #EAFAF1; padding: 8px; border-radius: 5px;")
        layout.addWidget(self.lbl_room_rev)
        self.lbl_svc_rev = QLabel("Service Rev: ₱0")
        self.lbl_svc_rev.setStyleSheet("font-size: 14px; font-weight: bold; color: #F39C12; background: #FEF9E7; padding: 8px; border-radius: 5px;")
        layout.addWidget(self.lbl_svc_rev)
        self.lbl_total_rev = QLabel("TOTAL: ₱0")
        self.lbl_total_rev.setStyleSheet("font-size: 20px; font-weight: 800; color: #2C3E50; margin-left: 20px;")
        layout.addWidget(self.lbl_total_rev)
        self.main_layout.addWidget(self.banner)

    def update_financial_banner(self, rev_room, rev_svc, total):
        period = self.cb_month.currentText() + " " + self.cb_year.currentText()
        if self.cb_month.currentText() == "All":
            period = f"Annual Report {self.cb_year.currentText()}"
        self.lbl_month_name.setText(period)
        self.lbl_room_rev.setText(f"Room Rev: ₱{rev_room:,}")
        self.lbl_svc_rev.setText(f"Service Rev: ₱{rev_svc:,}")
        self.lbl_total_rev.setText(f"TOTAL: ₱{total:,}")

    def setup_content(self):
        from PyQt6.QtWidgets import QScrollArea
        scroll  = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        content = QWidget()
        self.cl = QVBoxLayout(content)
        self.chart_grid = QGridLayout()
        self.chart_grid.setSpacing(15)
        self.cl.addLayout(self.chart_grid)
        scroll.setWidget(content)
        self.main_layout.addWidget(scroll)

    def populate_filters(self):
        self.available_data = self.ctrl.get_available_dates()
        self.cb_year.blockSignals(True)
        self.cb_year.clear()
        years = sorted(self.available_data.keys(), reverse=True)
        if not years:
            self.cb_year.addItem(str(datetime.now().year))
            self.cb_year.blockSignals(False)
            self.on_year_changed(self.cb_year.currentText())
            return
        self.cb_year.addItems(years)
        curr = str(datetime.now().year)
        self.cb_year.setCurrentText(curr if curr in years else self.cb_year.itemText(0))
        self.cb_year.blockSignals(False)
        self.on_year_changed(self.cb_year.currentText())

    def on_year_changed(self, year):
        self.cb_month.blockSignals(True)
        self.cb_month.clear()
        self.cb_month.addItem("All", userData=None)
        if year in self.available_data:
            for m in self.available_data[year]:
                self.cb_month.addItem(calendar.month_name[int(m)], userData=m)
        curr = f"{datetime.now().month:02d}"
        idx  = self.cb_month.findData(curr)
        self.cb_month.setCurrentIndex(idx if idx >= 0 else 0)
        self.cb_month.blockSignals(False)
        self.load_data()

    def load_data(self):
        if not self.plt: return
        year      = self.cb_year.currentText()
        month_idx = self.cb_month.currentData()
        if not year: return

        if month_idx:
            last    = calendar.monthrange(int(year), int(month_idx))[1]
            s_date  = f"{year}-{month_idx}-01"
            e_date  = f"{year}-{month_idx}-{last}"
        else:
            s_date = f"{year}-01-01"
            e_date = f"{year}-12-31"

        data  = self.ctrl.get_analytics(s_date, e_date)
        total = data['rev_room'] + data['rev_svc']
        self.update_financial_banner(data['rev_room'], data['rev_svc'], total)

        while self.chart_grid.count():
            self.chart_grid.takeAt(0).widget().deleteLater()

        f1 = self.frame("Revenue Breakdown")
        self.pie(f1, data['rev_room'], data['rev_svc'])
        self.chart_grid.addWidget(f1, 0, 0)

        f2 = self.frame("Most Used Room Types")
        self.bar_rooms(f2, data['room_counts'])
        self.chart_grid.addWidget(f2, 0, 1)

        f3 = self.frame("Revenue Trend Over Time")
        self.line_trend(f3, year, month_idx)
        self.chart_grid.addWidget(f3, 1, 0, 1, 2)

        f4 = self.frame("Top Services Offered")
        self.bar_services(f4, data['svc_counts'])
        self.chart_grid.addWidget(f4, 2, 0, 1, 2)

    def export_pdf(self):
        year  = self.cb_year.currentText()
        month = self.cb_month.currentData() or "All"
        dlg   = ExportReportDialog(self, year, self.cb_month.currentText(), self.admin_name)
        if dlg.exec() == 1:
            try:
                s, m = self.ctrl.export_report(year, month, dlg.options, dlg.generated_by)
                msg  = QMessageBox(self)
                msg.setWindowTitle("Export"); msg.setText(m)
                msg.setIcon(QMessageBox.Icon.Information if s else QMessageBox.Icon.Warning)
                msg.setStyleSheet(MESSAGEBOX_STYLE); msg.exec()
            except TypeError:
                QMessageBox.critical(self, "Backend Update Required",
                                     "Update 'export_report' in c_admin.py to accept the 'options' argument.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export report: {str(e)}")

    # ── Chart helpers ─────────────────────────────────────────────────────────

    def frame(self, title):
        f = QFrame(styleSheet="background: white; border: 1px solid #BDC3C7; border-radius: 8px;")
        f.setMinimumHeight(350)
        l = QVBoxLayout(f)
        l.addWidget(QLabel(title, styleSheet="font-weight:bold; color:#2C3E50; border:none;"))
        return f

    def pie(self, f, r, s):
        if r == 0 and s == 0:
            f.layout().addWidget(QLabel("No Revenue Data")); return
        fig = self.Figure(figsize=(4, 4), dpi=100)
        ax  = fig.add_subplot(111)
        ax.pie([r, s], labels=['Room ', 'Service '], autopct='%1.1f%%', colors=['#2ECC71', '#F1C40F'])
        c = self.FigureCanvas(fig); f.layout().addWidget(c); c.draw()

    def line_trend(self, f, year, month_idx):
        fig = self.Figure(figsize=(8, 3.5), dpi=100)
        ax  = fig.add_subplot(111)
        if month_idx:
            data   = self.ctrl.get_daily_revenue(year, int(month_idx))
            x_vals = [d['day']       for d in data]
            y_vals = [d['total_rev'] for d in data]
            ax.set_xlabel("Day of Month")
        else:
            data   = self.ctrl.get_monthly_revenue(year)
            x_vals = [d['month_name'] for d in data]
            y_vals = [d['total_rev']  for d in data]

        ax.plot(x_vals, y_vals, marker='o', color='#E67E22', linewidth=2.5)
        ax.fill_between(x_vals, y_vals, alpha=0.1, color='#E67E22')
        ax.set_ylabel("Revenue (₱)")
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
        fig.tight_layout()
        c = self.FigureCanvas(fig); f.layout().addWidget(c); c.draw()

    def bar_rooms(self, f, d):
        if not d: f.layout().addWidget(QLabel("No Data")); return
        fig = self.Figure(figsize=(4, 4), dpi=100)
        ax  = fig.add_subplot(111)
        ax.bar(d.keys(), d.values(), color='#3498DB')
        ax.set_ylabel("Bookings Count")
        if self.MaxNLocator: ax.yaxis.set_major_locator(self.MaxNLocator(integer=True))
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
        fig.tight_layout()
        c = self.FigureCanvas(fig); f.layout().addWidget(c); c.draw()

    def bar_services(self, f, d):
        if not d: f.layout().addWidget(QLabel("No Data")); return
        fig        = self.Figure(figsize=(8, 4), dpi=100)
        ax         = fig.add_subplot(111)
        sorted_d   = dict(sorted(d.items(), key=lambda item: item[1], reverse=True))
        ax.bar(sorted_d.keys(), sorted_d.values(), color='#9B59B6')
        ax.set_ylabel("Quantity Sold")
        if self.MaxNLocator: ax.yaxis.set_major_locator(self.MaxNLocator(integer=True))
        ax.tick_params(axis='x', rotation=25, labelsize=9)
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
        fig.tight_layout()
        c = self.FigureCanvas(fig); f.layout().addWidget(c); c.draw()

    def refresh_data(self):
        self.populate_filters()

    def set_annual_view(self):
        self.cb_year.setCurrentText(str(datetime.now().year))
        self.cb_month.setCurrentIndex(0)
        self.load_data()
