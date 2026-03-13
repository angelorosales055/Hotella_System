from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout, QPushButton,
                             QLineEdit, QComboBox, QSpinBox, QCalendarWidget, QTableWidget, QStackedWidget,
                             QTableWidgetItem, QHeaderView, QMessageBox, QAbstractItemView, QDateEdit,
                             QScrollArea, QDialog, QTabWidget, QCheckBox, QApplication)
from PyQt6.QtCore import Qt, QTimer, QTime, QDate, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QPixmap, QIcon, QPainter, QPen, QPainterPath, QImage
from datetime import datetime
import os

# ── Shared styles ─────────────────────────────────────────────────────────────
INPUT_STYLE  = "padding: 10px; border: 1px solid #BDC3C7; border-radius: 5px; font-size: 14px; background: white; color: black;"
BTN_STYLE    = "QPushButton { background-color: #2C3E50; color: white; font-weight: bold; border-radius: 5px; padding: 12px; } QPushButton:hover { background-color: #34495E; }"
SIDEBAR_BG   = "background-color: #1A1A1D; color: white;"
CARD_STYLE   = "QFrame { background-color: white; border: 1px solid #E0E0E0; border-radius: 10px; } QFrame:hover { border: 2px solid #3498DB; }"
CALENDAR_STYLE = """
    QCalendarWidget QWidget { alternate-background-color: #F7F9F9; background-color: white; }
    QCalendarWidget QWidget#qt_calendar_navigationbar { background-color: #2C3E50; border: none; }
    QCalendarWidget QSpinBox { background-color: transparent; color: white; font-weight: bold; }
    QCalendarWidget QToolButton { color: white; font-weight: bold; icon-size: 24px; background-color: transparent; }
    QCalendarWidget QAbstractItemView { font-size: 14px; selection-background-color: #3498DB; selection-color: white; }
"""
SPINBOX_STYLE = """
    QSpinBox { padding: 5px 10px; border: 2px solid #BDC3C7; border-radius: 5px; font-size: 14px; background: white; color: #2C3E50; font-weight: bold; }
    QSpinBox:focus { border: 2px solid #3498DB; }
"""


# ── Main Staff Window ─────────────────────────────────────────────────────────
class StaffWindow(QWidget):
    def __init__(self, ctrl):
        super().__init__()
        self.ctrl = ctrl
        self.setStyleSheet("""
            QWidget { background-color: white; color: #2C3E50; font-family: 'Segoe UI', sans-serif; }
            QFrame#Sidebar { background-color: #1A1A1D; }
            QLabel { color: #2C3E50; }
            QLineEdit, QComboBox, QSpinBox { color: black; }
        """)

        main = QHBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(260)
        sidebar.setStyleSheet(SIDEBAR_BG)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(0, 0, 0, 0)
        sb_layout.setSpacing(0)

        logo_box = QFrame()
        logo_box.setFixedHeight(80)
        logo_box.setStyleSheet("background-color: #B71C1C;")
        lbl_logo = QLabel("HOTELLA\nSTAFF", logo_box)
        lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_logo.setStyleSheet("color: #F4D03F; font-size: 22px; font-weight: 900; background: transparent;")
        vl = QVBoxLayout(logo_box)
        vl.addWidget(lbl_logo)
        sb_layout.addWidget(logo_box)
        sb_layout.addSpacing(20)

        self.stack = QStackedWidget()
        self.btns  = []

        self.stack.addWidget(BookingsManagerPage(ctrl))
        self.stack.addWidget(BookingPage(ctrl))
        self.stack.addWidget(ServicesPage(ctrl))
        self.stack.addWidget(PaymentPage(ctrl))
        self.stack.addWidget(HousekeepingPage(ctrl))

        page_names = ["ALL BOOKINGS", "BOOK A ROOM", "SERVICES", "PAYMENT", "HOUSEKEEPING"]

        for i, name in enumerate(page_names):
            btn = QPushButton(name)
            btn.setFixedHeight(55)
            btn.setStyleSheet("""
                QPushButton { text-align: left; padding-left: 30px; color: #ECF0F1; border: none; font-weight: 600; font-size: 14px; background: transparent; }
                QPushButton:checked { background-color: #F4D03F; color: black; border-left: 5px solid #B71C1C; }
                QPushButton:hover { background-color: #34495E; }
            """)
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, idx=i: self.nav(idx))
            sb_layout.addWidget(btn)
            self.btns.append(btn)

        sb_layout.addStretch()

        btn_logout = QPushButton("LOG OUT")
        btn_logout.setFixedHeight(55)
        btn_logout.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_logout.setStyleSheet(
            "QPushButton { color: white; font-weight: bold; border: none; font-size: 14px; } QPushButton:hover { color:gray }")
        btn_logout.clicked.connect(lambda: self.window().close())
        sb_layout.addWidget(btn_logout)

        main.addWidget(sidebar)
        main.addWidget(self.stack)
        self.nav(0)

    def nav(self, idx):
        for b in self.btns: b.setChecked(False)
        self.btns[idx].setChecked(True)
        self.stack.setCurrentIndex(idx)
        current_widget = self.stack.currentWidget()
        if hasattr(current_widget, 'refresh'):
            current_widget.refresh()


# ── Page 1: All Bookings ──────────────────────────────────────────────────────
class BookingsManagerPage(QWidget):
    def __init__(self, ctrl):
        super().__init__()
        self.ctrl = ctrl
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.addWidget(QLabel("Booking Management",
                                styleSheet="font-size: 24px; font-weight: 800; color: #2C3E50; margin-bottom: 10px;"))
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #DDD; background: white; border-radius: 5px; }
            QTabBar::tab { background: #E0E0E0; color: #333; padding: 12px 25px; margin-right: 2px;
                           border-top-left-radius: 5px; border-top-right-radius: 5px; font-weight: bold; }
            QTabBar::tab:selected { background: #3498DB; color: white; }
            QTabBar::tab:hover { background: #BDC3C7; }
        """)
        self.tab_today = TodayBookingsTab(ctrl)
        self.tabs.addTab(self.tab_today, "📅 Today's Bookings")
        self.tab_all = AllBookingsTab(ctrl)
        self.tabs.addTab(self.tab_all, "📚 All Bookings History")
        self.tabs.currentChanged.connect(self.on_tab_change)
        layout.addWidget(self.tabs)

    def on_tab_change(self, index):
        (self.tab_today if index == 0 else self.tab_all).refresh()

    def refresh(self):
        self.on_tab_change(self.tabs.currentIndex())


class TodayBookingsTab(QWidget):
    def __init__(self, ctrl):
        super().__init__()
        self.ctrl = ctrl
        l = QVBoxLayout(self)
        l.setContentsMargins(20, 20, 20, 20)
        l.addWidget(QLabel("Guests Arriving Today", styleSheet="font-size: 18px; font-weight: bold; color: #2C3E50;"))
        scroll  = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none; background: transparent;")
        content = QWidget()
        self.grid = QGridLayout(content)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        scroll.setWidget(content)
        l.addWidget(scroll)

    def refresh(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        bookings = self.ctrl.get_todays_arrivals()
        if not bookings:
            self.grid.addWidget(QLabel("No arrivals scheduled for today.", styleSheet="color: #7f8c8d; font-size: 14px;"), 0, 0)
            return

        r, c = 0, 0
        for b in bookings:
            self.grid.addWidget(self.create_card(b), r, c)
            c += 1
            if c > 3: c = 0; r += 1

    def create_card(self, b):
        card = QFrame()
        card.setFixedSize(220, 160)
        card.setStyleSheet(CARD_STYLE)
        v = QVBoxLayout(card)
        v.addWidget(QLabel(b['name'], styleSheet="font-weight:bold; font-size:15px; border:none; color:#2C3E50;"))
        v.addWidget(QLabel(f"ID: {b['bid']}", styleSheet="color:#7F8C8D; font-size:12px; border:none;"))
        v.addWidget(QLabel(f"Room: {b['room']} ({b['type']})", styleSheet="color:#E67E22; font-weight:bold; border:none;"))

        current_status = str(b.get('status', '')).strip().lower()
        if current_status not in ('arrived', 'checked in'):
            btn_box = QHBoxLayout()
            btn1 = QPushButton("✓ Check-In")
            btn1.setStyleSheet("background:#27AE60; color:white; border-radius:4px; font-weight:bold; border:none;")
            btn2 = QPushButton("✕ Cancel")
            btn2.setStyleSheet("background:#E74C3C; color:white; border-radius:4px; font-weight:bold; border:none;")
            btn1.clicked.connect(lambda: self.do_action(b, "Check-In"))
            btn2.clicked.connect(lambda: self.do_action(b, "Cancelled"))
            btn_box.addWidget(btn1); btn_box.addWidget(btn2)
            v.addLayout(btn_box)
        else:
            v.addStretch()
            status_lbl = QLabel("Checked In")
            status_lbl.setStyleSheet("color: #27AE60; font-weight: 800; border: none; font-size: 16px;")
            status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            v.addWidget(status_lbl)
        return card

    def do_action(self, b, action):
        if QMessageBox.question(self, "Confirm", f"Confirm {action} for {b['name']}?") == QMessageBox.StandardButton.Yes:
            if action == "Check-In":
                success, msg = self.ctrl.mark_arrived(b['bid'], b['name'])
                if success: QMessageBox.information(self, "Success", msg)
                else:        QMessageBox.warning(self, "Check-In Blocked", msg)
            else:
                self.ctrl.cancel_booking_today(b['bid'], b['name'])
            self.refresh()


class AllBookingsTab(QWidget):
    def __init__(self, ctrl):
        super().__init__()
        self.ctrl = ctrl
        l = QVBoxLayout(self)
        l.setContentsMargins(20, 20, 20, 20)
        top = QHBoxLayout()
        self.search   = QLineEdit(placeholderText="Search Guest or ID...")
        self.search.setStyleSheet(INPUT_STYLE)
        self.search.textChanged.connect(self.refresh)
        self.cb_filter = QComboBox()
        self.cb_filter.addItems(["All", "Confirmed", "Cancelled", "Checked Out"])
        self.cb_filter.setStyleSheet(INPUT_STYLE)
        self.cb_filter.currentTextChanged.connect(self.refresh)
        top.addWidget(QLabel("Search:")); top.addWidget(self.search)
        top.addWidget(QLabel("Filter:")); top.addWidget(self.cb_filter)
        l.addLayout(top)
        scroll  = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none; background: transparent;")
        content = QWidget()
        self.grid = QGridLayout(content)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        scroll.setWidget(content)
        l.addWidget(scroll)

    def refresh(self):
        while self.grid.count(): self.grid.takeAt(0).widget().deleteLater()
        all_b  = self.ctrl.get_all_bookings()
        txt    = self.search.text().lower()
        stat   = self.cb_filter.currentText()
        filtered = [b for b in all_b
                    if (txt in b['name'].lower() or txt in b['bid'].lower())
                    and (stat == "All" or b['status'] == stat)]
        r, c = 0, 0
        for b in filtered:
            self.grid.addWidget(self.create_card(b), r, c)
            c += 1
            if c > 3: c = 0; r += 1

    def create_card(self, b):
        card = QFrame()
        card.setFixedSize(220, 150)
        bg = "#ECF0F1" if b['status'] != 'Confirmed' else "white"
        br = "#BDC3C7" if b['status'] != 'Confirmed' else "#3498DB"
        card.setStyleSheet(f"QFrame {{ background: {bg}; border: 2px solid {br}; border-radius: 8px; }}")
        v = QVBoxLayout(card)
        v.addWidget(QLabel(b['bid'],  styleSheet="font-weight:bold; color:#2C3E50; border:none;"))
        v.addWidget(QLabel(b['name'], styleSheet="font-size:14px; border:none;"))
        v.addWidget(QLabel(f"{b['date']} ({b['days']} days)", styleSheet="color:#7F8C8D; font-size:12px; border:none;"))
        v.addWidget(QLabel(b['status'],
                           styleSheet=f"color:{'red' if b['status']=='Cancelled' else 'green'}; font-weight:bold; border:none;"))
        return card


# ── Page 2: Book a Room ───────────────────────────────────────────────────────
class BookingPage(QWidget):
    def __init__(self, ctrl):
        super().__init__()
        self.ctrl          = ctrl
        self.selected_room = None
        layout = QHBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(30)

        left_panel = QFrame()
        left_panel.setFixedWidth(350)
        left_panel.setStyleSheet("background: white; border-radius: 10px; border: 1px solid #E0E0E0;")
        lp_layout = QVBoxLayout(left_panel)
        lp_layout.setContentsMargins(25, 25, 25, 25)
        lp_layout.setSpacing(15)
        lp_layout.addWidget(QLabel("Guest Details", styleSheet="font-size: 20px; font-weight: 800; color: #2C3E50;border:0px;"))

        self.inp = {}
        for f in ["Name", "Email", "Phone", "Address"]:
            lp_layout.addWidget(QLabel(f, styleSheet="font-weight:bold; color:#555;border:0px;"))
            t = QLineEdit(placeholderText=f"Enter {f}")
            t.setStyleSheet(INPUT_STYLE)
            lp_layout.addWidget(t)
            self.inp[f] = t

        lp_layout.addWidget(QLabel("Number of Guests", styleSheet="font-weight:bold; color:#555;border:0px;"))
        self.spin_guests = QSpinBox()
        self.spin_guests.setRange(1, 10)
        self.spin_guests.setStyleSheet(SPINBOX_STYLE)
        self.spin_guests.valueChanged.connect(self.load_rooms)
        lp_layout.addWidget(self.spin_guests)

        self.lbl_sel = QLabel("No Room Selected", styleSheet="color: #E74C3C; font-weight: bold;border:0px;")
        self.lbl_tot = QLabel("Total: ₱0", styleSheet="font-size: 22px; font-weight: 900; color: #27AE60;border:0px")
        lp_layout.addWidget(self.lbl_sel)
        lp_layout.addWidget(self.lbl_tot)

        self.lbl_room_details = QLabel("")
        self.lbl_room_details.setStyleSheet(
            "font-size: 13px; color: #333; border: 1px solid #BDC3C7; padding: 12px; border-radius: 5px; background: #F9F9F9;")
        self.lbl_room_details.hide()
        lp_layout.addWidget(self.lbl_room_details)
        lp_layout.addStretch()

        btn_pay = QPushButton("PROCEED TO PAYMENT")
        btn_pay.setStyleSheet(BTN_STYLE)
        btn_pay.clicked.connect(self.pay)
        lp_layout.addWidget(btn_pay)
        layout.addWidget(left_panel)

        right_panel  = QWidget()
        rp_layout    = QVBoxLayout(right_panel)
        rp_layout.setContentsMargins(0, 0, 0, 0)

        ctrl_section = QFrame()
        ctrl_section.setStyleSheet("background: white; border-radius: 10px; border: 1px solid #E0E0E0;")
        cs_layout    = QHBoxLayout(ctrl_section)

        self.cal = QCalendarWidget()
        self.cal.setFixedHeight(250)
        self.cal.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.cal.setStyleSheet(CALENDAR_STYLE)
        self.cal.clicked.connect(self.load_rooms)

        dur_box = QVBoxLayout()
        dur_box.addWidget(QLabel("Booking Duration:", styleSheet="font-weight:bold;border:0px;"))
        self.dur = QSpinBox()
        self.dur.setRange(1, 30)
        self.dur.setSuffix(" Night(s)")
        self.dur.setFixedHeight(40)
        self.dur.setStyleSheet(SPINBOX_STYLE)
        self.dur.valueChanged.connect(self.load_rooms)

        btn_refresh = QPushButton("Check Availability")
        btn_refresh.setStyleSheet("background: #3498DB; color: white; padding: 10px;")
        btn_refresh.clicked.connect(self.load_rooms)
        dur_box.addWidget(self.dur)
        dur_box.addWidget(btn_refresh)
        dur_box.addStretch()

        cs_layout.addWidget(self.cal, stretch=2)
        cs_layout.addLayout(dur_box, stretch=1)
        rp_layout.addWidget(ctrl_section)
        rp_layout.addWidget(QLabel("Available Rooms (Select One):", styleSheet="font-weight:bold; margin-top:10px;"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none;")
        room_container = QWidget()
        self.grid = QGridLayout(room_container)
        scroll.setWidget(room_container)
        rp_layout.addWidget(scroll)
        layout.addWidget(right_panel)

    def refresh(self):
        self.load_rooms()

    def load_rooms(self):
        if self.cal.selectedDate() < QDate.currentDate():
            while self.grid.count(): self.grid.takeAt(0).widget().deleteLater()
            self.lbl_sel.setText("Invalid Date Selected")
            self.lbl_room_details.hide()
            return

        while self.grid.count(): self.grid.takeAt(0).widget().deleteLater()
        self.selected_room = None
        self.lbl_tot.setText("Total: ₱0")
        self.lbl_room_details.hide()

        d_in  = self.cal.selectedDate().toString("yyyy-MM-dd")
        d_out = self.cal.selectedDate().addDays(self.dur.value()).toString("yyyy-MM-dd")

        rooms        = self.ctrl.search_rooms(d_in, d_out)
        prices       = self.ctrl.get_room_prices()
        guests_count = self.spin_guests.value()

        r, c = 0, 0
        for rm in rooms:
            rtype = rm[1]
            limit = self.ctrl.MAX_OCCUPANCY.get(rtype, 2)
            if limit < guests_count:
                continue
            p   = prices.get(rtype, 1500)
            btn = QPushButton(f"Room {rm[0]}\n{rtype}\n₱{p}/night")
            btn.setCheckable(True)
            btn.setFixedSize(140, 100)
            btn.setStyleSheet(
                "QPushButton { background: #2ECC71; color: white; border-radius: 8px; font-weight: bold; } "
                "QPushButton:checked { background: #27AE60; border: 3px solid #F1C40F; }"
            )
            btn.clicked.connect(lambda ch, x=rm[0], y=rtype, z=p, l=limit, b=btn: self.select_room(x, y, z, l, b))
            self.grid.addWidget(btn, r, c)
            c += 1
            if c > 3: c = 0; r += 1

        if self.grid.count() == 0:
            self.grid.addWidget(QLabel(f"No available rooms can accommodate {guests_count} guest(s) for the selected dates."))

    def select_room(self, rid, rtype, price, limit, btn):
        for i in range(self.grid.count()):
            w = self.grid.itemAt(i).widget()
            if w != btn and isinstance(w, QPushButton): w.setChecked(False)
        btn.setChecked(True)
        self.selected_room = {'id': rid, 'type': rtype, 'price': price}

        total       = price * self.dur.value()
        downpayment = total * 0.20
        self.lbl_sel.setText(f"Selected: {rid} ({rtype})")
        self.lbl_tot.setText(f"Total: ₱{total:,}")
        self.lbl_room_details.setText(f"""
        <table width='100%'>
            <tr><td><b>Room Type:</b></td><td align='right'>{rtype}</td></tr>
            <tr><td><b>Max Occupancy:</b></td><td align='right'>{limit} Person(s)</td></tr>
            <tr><td colspan='2'><hr></td></tr>
            <tr><td><b>Room Rate:</b></td><td align='right'>₱{price:,} / night</td></tr>
            <tr><td><b>Required DP (20%):</b></td><td align='right'>₱{downpayment:,.2f}</td></tr>
            <tr><td><b>Grand Total:</b></td><td align='right'><b>₱{total:,.2f}</b></td></tr>
        </table>
        """)
        self.lbl_room_details.show()

    def pay(self):
        if self.cal.selectedDate() < QDate.currentDate():
            return QMessageBox.warning(self, "Error", "Cannot book for a past date.")
        if not self.selected_room:
            return QMessageBox.warning(self, "Error", "Please select a room.")
        if not all(v.text().strip() for v in self.inp.values()):
            return QMessageBox.warning(self, "Error", "Please fill in all guest details.")

        total = self.selected_room['price'] * self.dur.value()
        dlg   = PaymentDialog(self, total)
        if dlg.exec() == 1:
            b_data = {k: v.text() for k, v in self.inp.items()}
            b_data.update({
                'date':       self.cal.selectedDate().toString("yyyy-MM-dd"),
                'days':       self.dur.value(),
                'total_price': total,
                'room_type':  self.selected_room['type'],
                'guests':     self.spin_guests.value(),
            })
            res, return_data = self.ctrl.create_booking_final(b_data, self.selected_room['id'], dlg.data)
            if res:
                bid, receipt_data, paid, method, pay_id = return_data
                ReceiptPreviewDialog(self, receipt_data, paid, method, pay_id, self.ctrl).exec()
                self.load_rooms()
                for t in self.inp.values(): t.clear()
                self.spin_guests.setValue(1)
            else:
                QMessageBox.critical(self, "Error", return_data)


# ── Masked Card Input ─────────────────────────────────────────────────────────
class MaskedCardInput(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.actual_value = ""
        self.is_showing   = False
        self.setMaxLength(19)

        self.eye_icon     = self._create_eye_icon(hidden=False)
        self.eye_off_icon = self._create_eye_icon(hidden=True)

        self.toggle_btn = QPushButton(self)
        self.toggle_btn.setFixedSize(30, 30)
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.clicked.connect(self.toggle_visibility)
        self.textChanged.connect(self._on_text_changed)
        self._update_icon()

    def _create_eye_icon(self, hidden=False):
        img = QImage(24, 24, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.transparent)
        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#7F8C8D"), 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        path = QPainterPath()
        path.moveTo(2, 12); path.quadTo(12, 4, 22, 12); path.quadTo(12, 20, 2, 12)
        painter.drawPath(path)
        painter.drawEllipse(9, 9, 6, 6)
        if hidden: painter.drawLine(4, 4, 20, 20)
        painter.end()
        return QIcon(QPixmap.fromImage(img))

    def _update_icon(self):
        self.toggle_btn.setIcon(self.eye_off_icon if self.is_showing else self.eye_icon)
        self.toggle_btn.setIconSize(QSize(18, 18))
        self.toggle_btn.setStyleSheet("QPushButton { border: none; background: transparent; padding: 0; } QPushButton:hover { background-color: rgba(0,0,0,0.1); border-radius: 4px; }")

    def resizeEvent(self, event):
        button_size = self.toggle_btn.size()
        frame_width = self.style().pixelMetric(self.style().PixelMetric.PM_DefaultFrameWidth)
        self.toggle_btn.move(self.rect().right() - button_size.width() - frame_width - 5,
                             (self.rect().bottom() + 1 - button_size.height()) // 2)
        super().resizeEvent(event)

    def _on_text_changed(self, text):
        cursor_pos = self.cursorPosition()
        old_len    = len(self.actual_value)
        raw = text.replace(' ', '').replace('•', '')
        if raw.isdigit() or raw == '':
            self.actual_value = raw
            self.blockSignals(True)
            if self.actual_value:
                formatted = self._format_card_visible(self.actual_value) if self.is_showing \
                            else self._format_card_masked(self.actual_value)
                self.setText(formatted)
                self.setCursorPosition(min(cursor_pos + (1 if len(self.actual_value) > old_len else 0), len(formatted)))
            else:
                self.clear()
            self.blockSignals(False)
        else:
            self.blockSignals(True)
            self.setText(self._format_card_visible(self.actual_value) if self.is_showing
                         else self._format_card_masked(self.actual_value))
            self.blockSignals(False)

    def _format_card_masked(self, number):
        full = '•' * len(number)
        return ' '.join([full[i:i+4] for i in range(0, len(full), 4)])

    def _format_card_visible(self, number):
        return ' '.join([number[i:i+4] for i in range(0, len(number), 4)])

    def toggle_visibility(self):
        self.is_showing = not self.is_showing
        self.blockSignals(True)
        self._update_icon()
        if self.is_showing:
            self.setText(self._format_card_visible(self.actual_value))
        else:
            self.setText(self._format_card_masked(self.actual_value) if self.actual_value else "")
        self.blockSignals(False)

    def get_card_number(self):  return self.actual_value
    def set_card_number(self, number):
        self.actual_value = str(number).replace(' ', '')
        self.setText(self._format_card_visible(self.actual_value) if self.is_showing
                     else self._format_card_masked(self.actual_value))


# ── Payment Dialog ────────────────────────────────────────────────────────────
class PaymentDialog(QDialog):
    def __init__(self, parent, total):
        super().__init__(parent)
        self.setWindowTitle("Payment"); self.setFixedSize(450, 450)
        self.total = total; self.data = {}
        l = QVBoxLayout(self); l.setSpacing(15); l.setContentsMargins(30, 30, 30, 30)
        l.addWidget(QLabel(f"Total Amount: ₱{total:,}", styleSheet="font-size:20px; font-weight:bold; color:#2C3E50;"))
        self.cb = QComboBox()
        self.cb.addItems(["Cash (Walk-in)", "Debit Card", "Credit Card"])
        self.cb.setStyleSheet(INPUT_STYLE)
        self.cb.currentTextChanged.connect(self.chk)
        l.addWidget(QLabel("Payment Method:")); l.addWidget(self.cb)
        self.card_inp = MaskedCardInput(placeholderText="Enter Card Number")
        self.card_inp.setStyleSheet(INPUT_STYLE + " QLineEdit { padding-right: 40px; }")
        self.card_inp.hide(); l.addWidget(self.card_inp)
        self.spin = QSpinBox()
        self.spin.setRange(0, total); self.spin.setValue(int(total * 0.20))
        self.spin.setStyleSheet(INPUT_STYLE)
        self.lbl_amt = QLabel("Amount to Pay:")
        l.addWidget(self.lbl_amt); l.addWidget(self.spin)
        self.lbl_note = QLabel("Minimum 20% downpayment required.")
        self.lbl_note.setWordWrap(True)
        self.lbl_note.setStyleSheet("color:#7f8c8d; font-style:italic;")
        l.addWidget(self.lbl_note)
        btn = QPushButton("Confirm Booking"); btn.setStyleSheet(BTN_STYLE)
        btn.clicked.connect(self.save); l.addWidget(btn)
        self.chk("Cash (Walk-in)")

    def chk(self, m):
        if "Card" in m:
            self.card_inp.setPlaceholderText(f"Enter {m} Number"); self.card_inp.show()
            if "Credit" in m:
                self.spin.hide(); self.lbl_amt.hide(); self.spin.setValue(0)
                self.lbl_note.setText("Credit Card Guarantee. No immediate charge.")
            else:
                self.spin.show(); self.lbl_amt.show()
                min_dp = int(self.total * 0.20)
                self.spin.setRange(min_dp, self.total); self.spin.setValue(min_dp)
                self.lbl_note.setText(f"Minimum 20% Downpayment: ₱{min_dp:,}")
        else:
            self.card_inp.hide(); self.spin.show(); self.lbl_amt.show()
            min_dp = int(self.total * 0.20)
            self.spin.setRange(min_dp, self.total); self.spin.setValue(min_dp)
            self.lbl_note.setText(f"Minimum 20% Downpayment: ₱{min_dp:,}")

    def save(self):
        method = self.cb.currentText()
        if "Card" in method:
            card_num = self.card_inp.get_card_number()
            if not card_num or len(card_num) < 12:
                return QMessageBox.warning(self, "Error", f"Please enter a valid {method} Number (at least 12 digits).")
            self.data = {'amount': self.spin.value(), 'method': method, 'card_number': card_num}
        else:
            self.data = {'amount': self.spin.value(), 'method': method, 'card_number': None}
        self.accept()


# ── Page 3: Services ──────────────────────────────────────────────────────────
class ServicesPage(QWidget):
    def __init__(self, ctrl):
        super().__init__()
        self.ctrl = ctrl
        l = QVBoxLayout(self); l.setContentsMargins(20, 20, 20, 20)
        l.addWidget(QLabel("Guest Services", styleSheet="font-size: 24px; font-weight: 800; color: #2C3E50; margin-bottom: 10px;"))
        l.addWidget(QLabel("Click on a GREEN (Occupied) room to offer services.", styleSheet="color: #7f8c8d; margin-bottom: 20px;"))
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none; background: transparent;")
        content = QWidget()
        self.grid = QGridLayout(content)
        self.grid.setSpacing(15)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        scroll.setWidget(content); l.addWidget(scroll)
        btn_ref = QPushButton("Refresh Room Status")
        btn_ref.setStyleSheet("background: #2C3E50; color: white; padding: 10px; border-radius: 5px;")
        btn_ref.clicked.connect(self.refresh); l.addWidget(btn_ref)
        self.refresh()

    def refresh(self):
        while self.grid.count(): self.grid.takeAt(0).widget().deleteLater()
        rooms = self.ctrl.get_map_data()
        r, c = 0, 0
        for rm in rooms:
            self.grid.addWidget(self.create_room_btn(rm), r, c)
            c += 1
            if c > 5: c = 0; r += 1

    def create_room_btn(self, rm):
        room_num, status, desc = rm[0], rm[1], rm[2]
        is_occupied = (status == 'Occupied')
        if is_occupied:
            color = "#2ECC71"; hover = "#27AE60"; border = "#27AE60"
        else:
            color = "#95A5A6"; hover = "#95A5A6"; border = "#7F8C8D"
        btn = QPushButton(f"{room_num}\n{desc}\n{status}")
        btn.setFixedSize(120, 90)
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {color}; color: white; border-radius: 8px; font-weight: bold; border: 2px solid {border}; }} "
            f"QPushButton:hover {{ background-color: {hover}; }}"
        )
        if is_occupied:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda: self.open_service_dialog(room_num))
        else:
            btn.setDisabled(True)
        return btn

    def open_service_dialog(self, room_num):
        bid, name = self.ctrl.get_active_room_details(room_num)
        if not bid:
            return QMessageBox.warning(self, "Error", "Could not find active booking.")
        dlg = ServiceDialog(self, room_num, bid, name, self.ctrl)
        if dlg.exec() == 1: self.refresh()


class ServiceDialog(QDialog):
    """
    Purely a UI form. It asks the controller for the list of available services
    (including availability flags), then renders them. No business logic here.
    """

    def __init__(self, parent, room, bid, name, ctrl):
        super().__init__(parent)
        self.setWindowTitle(f"Services for Room {room}")
        self.setFixedSize(450, 650)
        self.ctrl = ctrl; self.bid = bid; self.room = room

        l = QVBoxLayout(self); l.setSpacing(15); l.setContentsMargins(25, 25, 25, 25)
        l.addWidget(QLabel(f"Guest: {name}", styleSheet="font-size: 18px; font-weight: bold; color: #2C3E50;"))
        l.addWidget(QLabel(f"Booking ID: {bid}", styleSheet="color: #7F8C8D;"))
        l.addWidget(QLabel("Select Services to Add:", styleSheet="margin-top: 10px; font-weight: bold;"))

        # Controller decides availability; view only renders
        available_services = self.ctrl.get_available_services()
        self.service_widgets = []

        for svc in available_services:
            row  = QHBoxLayout()
            label = f"{svc['name']} - ₱{svc['price']}"
            if not svc['available']:
                label += f" ({svc['note']})"
            cb   = QCheckBox(label); cb.setStyleSheet("font-size: 14px; padding: 5px;")
            spin = QSpinBox(); spin.setRange(1, 10); spin.setEnabled(False); spin.setFixedWidth(60)
            cb.toggled.connect(spin.setEnabled)
            row.addWidget(cb); row.addWidget(spin)
            l.addLayout(row)
            self.service_widgets.append((cb, spin, svc['name'], svc['price']))

        l.addWidget(QLabel("Assigned Staff:", styleSheet="margin-top: 10px; font-weight: bold;"))
        self.cb_emp = QComboBox()
        self.cb_emp.addItems(self.ctrl.get_service_staff_list())
        self.cb_emp.setStyleSheet(INPUT_STYLE)
        l.addWidget(self.cb_emp)
        l.addStretch()

        btn = QPushButton("Add Charges to Bill"); btn.setStyleSheet(BTN_STYLE)
        btn.clicked.connect(self.save); l.addWidget(btn)

    def save(self):
        emp = self.cb_emp.currentText()
        if not emp:
            return QMessageBox.warning(self, "Error", "Please select a staff member.")
        added = []
        for cb, spin, svc, price in self.service_widgets:
            if cb.isChecked():
                qty = spin.value()
                self.ctrl.add_service_charge(self.bid, self.room, svc, price, qty, emp)
                added.append(f"{svc} (x{qty})")
        if added:
            QMessageBox.information(self, "Success", "Added services:\n" + "\n".join(added))
            self.accept()
        else:
            QMessageBox.warning(self, "Warning", "No services selected.")


# ── Page 4: Checkout / Payment ────────────────────────────────────────────────
class PaymentPage(QWidget):
    def __init__(self, ctrl):
        super().__init__()
        self.ctrl = ctrl
        l = QVBoxLayout(self); l.setContentsMargins(20, 20, 20, 20)
        l.addWidget(QLabel("Checkout & Payment", styleSheet="font-size: 24px; font-weight: 800; color: #2C3E50; margin-bottom: 10px;"))
        btn_refresh = QPushButton("Refresh List")
        btn_refresh.setStyleSheet("background: #3498DB; color: white; padding: 8px; border-radius: 5px; font-weight: bold;")
        btn_refresh.clicked.connect(self.refresh); l.addWidget(btn_refresh)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setStyleSheet("border:none; background: transparent;")
        content = QWidget()
        self.grid = QGridLayout(content)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.grid.setSpacing(20)
        scroll.setWidget(content); l.addWidget(scroll)
        self.refresh()

    def refresh(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        try:
            data = self.ctrl.get_checkout_cards()
            if not data:
                self.grid.addWidget(QLabel("No occupied rooms pending checkout.", styleSheet="color: #7f8c8d; font-size: 16px;"), 0, 0)
                return
            r, c = 0, 0
            for row_data in data:
                self.grid.addWidget(self.create_card(row_data), r, c)
                c += 1
                if c > 3: c = 0; r += 1
        except Exception as e:
            print(f"Error loading checkout cards: {e}")

    def create_card(self, data):
        card = QFrame(); card.setFixedSize(220, 160)
        if data['final_balance'] > 0:
            status_color = "#E74C3C"; status_text = f"Due: ₱{data['final_balance']:,}"; border_color = "#E74C3C"
        else:
            status_color = "#27AE60"; status_text = "Fully Paid"; border_color = "#27AE60"
        card.setStyleSheet(
            f"QFrame {{ background-color: white; border: 2px solid {border_color}; border-radius: 10px; }} "
            f"QFrame:hover {{ background-color: #F9F9F9; border: 2px solid #3498DB; }}"
        )
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.mousePressEvent = lambda event: self.open_checkout(data)
        layout = QVBoxLayout(card); layout.setSpacing(5)
        layout.addWidget(QLabel(f"Room {data['room']}", styleSheet="font-size: 18px; font-weight: 900; color: #2C3E50; border:none;"))
        lbl_name = QLabel(data['guest'], styleSheet="font-size: 14px; font-weight: bold; color: #555; border:none;")
        lbl_name.setWordWrap(True); layout.addWidget(lbl_name)
        layout.addWidget(QLabel(f"ID: {data['bid']}", styleSheet="color: #999; font-size: 12px; border:none;"))
        layout.addStretch()
        layout.addWidget(QLabel(status_text, styleSheet=f"font-size: 16px; font-weight: 800; color: {status_color}; border:none;"))
        return card

    def open_checkout(self, data):
        dlg = CheckoutDialog(self, data, self.ctrl)
        if dlg.exec() == 1:
            QTimer.singleShot(200, self.refresh)


class CheckoutDialog(QDialog):
    def __init__(self, parent, data, ctrl):
        super().__init__(parent)
        self.setWindowTitle(f"Checkout Room {data['room']}")
        self.setMinimumWidth(500)
        self.ctrl = ctrl; self.data = data
        self.balance_due = int(data['final_balance'])

        l = QVBoxLayout(self); l.setSpacing(12); l.setContentsMargins(35, 35, 35, 35)
        l.setSizeConstraint(QVBoxLayout.SizeConstraint.SetFixedSize)
        l.addWidget(QLabel(f"Guest: {data['guest']}", styleSheet="font-size: 20px; font-weight: bold;"))
        l.addWidget(QLabel(f"Room Charge: ₱{data['room_cost']:,}", styleSheet="font-size: 16px;"))

        if data.get('svc_details'):
            l.addWidget(QLabel("Services Availed:", styleSheet="font-size: 16px; font-weight: bold; color: #2980B9; margin-top: 5px;"))
            for s in data['svc_details']:
                l.addWidget(QLabel(f"  • {s['name']} (x{s['qty']}): ₱{s['total']:,}", styleSheet="font-size: 15px; color: #444;"))
        elif data.get('svc_cost', 0) > 0:
            l.addWidget(QLabel(f"Services Fee: ₱{data['svc_cost']:,}", styleSheet="font-size: 16px;"))

        if data.get('penalty', 0) > 0:
            l.addWidget(QLabel(f"Penalty ({data['penalty_desc']}): ₱{data['penalty']:,}",
                               styleSheet="font-size: 16px; color: #C0392B; font-weight: bold;"))

        l.addWidget(QLabel("---------------------------------"))
        l.addWidget(QLabel(f"Grand Total: ₱{data['final_total']:,}", styleSheet="font-size: 18px; font-weight: bold;"))
        l.addWidget(QLabel(f"Already Paid: -₱{data['paid']:,}", styleSheet="font-size: 18px; color: #27AE60; font-weight: bold;"))
        l.addWidget(QLabel("---------------------------------"))
        l.addWidget(QLabel(f"BALANCE DUE: ₱{self.balance_due:,}", styleSheet="font-size: 26px; font-weight: 900; color: #C0392B;"))
        l.addWidget(QLabel("---------------------------------"))

        if self.balance_due > 0:
            l.addWidget(QLabel("Amount Tendered (Cash/Card):", styleSheet="font-size: 16px; font-weight:bold;"))
            self.spin = QSpinBox()
            self.spin.setRange(0, 1000000); self.spin.setValue(self.balance_due)
            self.spin.setStyleSheet("QSpinBox { font-size: 20px; padding: 12px; font-weight: bold; }")
            self.spin.valueChanged.connect(self.calculate_change); l.addWidget(self.spin)
            self.cb_method = QComboBox()
            self.cb_method.addItems(["Cash", "Credit Card", "Debit Card"])
            self.cb_method.setStyleSheet("padding: 10px; font-size: 16px; border: 1px solid #BDC3C7; border-radius: 5px;")
            l.addWidget(self.cb_method)
            self.lbl_change = QLabel("Change: ₱0")
            self.lbl_change.setStyleSheet("font-size: 20px; font-weight: bold; color: #27AE60; margin-top: 10px;")
            self.lbl_change.setAlignment(Qt.AlignmentFlag.AlignRight); l.addWidget(self.lbl_change)
        else:
            l.addWidget(QLabel("✅ Fully Paid", styleSheet="color: green; font-size: 18px; font-weight: bold;"))
            self.spin = None

        l.addStretch()
        btn = QPushButton("PROCESS CHECKOUT")
        btn.setStyleSheet("QPushButton { background-color: #2C3E50; color: white; font-weight: bold; border-radius: 5px; padding: 18px; font-size: 18px; } QPushButton:hover { background-color: #34495E; }")
        btn.clicked.connect(self.process); l.addWidget(btn)

    def calculate_change(self):
        if not self.spin: return
        change = self.spin.value() - self.balance_due
        if change < 0:
            self.lbl_change.setText(f"Short: ₱{abs(change):,}")
            self.lbl_change.setStyleSheet("font-size: 20px; font-weight: bold; color: #C0392B; margin-top: 10px;")
        else:
            self.lbl_change.setText(f"Change: ₱{change:,}")
            self.lbl_change.setStyleSheet("font-size: 20px; font-weight: bold; color: #27AE60; margin-top: 10px;")

    def process(self):
        try:
            tendered = self.spin.value() if self.spin else 0
            method   = self.cb_method.currentText() if hasattr(self, 'cb_method') else "None"
            if self.balance_due > 0 and tendered < self.balance_due:
                QMessageBox.warning(self, "Insufficient Payment",
                                    f"The guest is short by ₱{self.balance_due - tendered:,}.\nPlease collect the full amount.")
                return
            self.setEnabled(False); QApplication.processEvents()
            res, msg, receipt_data, pay_id = self.ctrl.process_checkout(self.data, tendered, method)
            self.setEnabled(True)
            if res:
                ReceiptPreviewDialog(self, receipt_data, tendered, method, pay_id, self.ctrl).exec()
                self.accept()
            else:
                QMessageBox.critical(self, "Error", f"Checkout failed:\n{msg}")
        except Exception as e:
            self.setEnabled(True)
            import traceback; traceback.print_exc()
            QMessageBox.critical(self, "System Error", f"An unexpected error occurred:\n{str(e)}")


# ── Page 5: Housekeeping ──────────────────────────────────────────────────────
class HousekeepingPage(QWidget):
    def __init__(self, ctrl):
        super().__init__()
        self.ctrl = ctrl
        l = QVBoxLayout(self); l.setContentsMargins(20, 20, 20, 20)
        l.addWidget(QLabel("Housekeeping & Room Status", styleSheet="font-size: 24px; font-weight: 800; color: #2C3E50; margin-bottom: 10px;"))
        l.addWidget(QLabel("Click 'Dirty' (Orange) rooms to assign a cleaner.\nClick 'Cleaning' (Yellow) rooms to mark as Clean.",
                           styleSheet="color: #7f8c8d; margin-bottom: 20px; font-style: italic;"))
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none; background: transparent;")
        content = QWidget()
        self.grid = QGridLayout(content)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.grid.setSpacing(15)
        scroll.setWidget(content); l.addWidget(scroll)
        btn_refresh = QPushButton("Refresh Status")
        btn_refresh.setStyleSheet("background: #2C3E50; color: white; padding: 10px; border-radius: 5px; font-weight: bold;")
        btn_refresh.clicked.connect(self.refresh); l.addWidget(btn_refresh)
        self.refresh()

    def refresh(self):
        while self.grid.count(): self.grid.takeAt(0).widget().deleteLater()
        rooms = self.ctrl.get_map_data()
        r, c = 0, 0
        for rm in rooms:
            self.grid.addWidget(self.create_card(rm), r, c)
            c += 1
            if c > 5: c = 0; r += 1

    def create_card(self, rm):
        room_num, status, desc = rm[0], rm[1], rm[2]
        if status == 'Dirty':
            color = "#E67E22"; hover = "#D35400"; border = "#D35400"; cursor = Qt.CursorShape.PointingHandCursor
        elif status == 'Cleaning':
            color = "#F1C40F"; hover = "#F39C12"; border = "#D68910"; cursor = Qt.CursorShape.PointingHandCursor
        elif status == 'Occupied':
            color = "#2ECC71"; hover = "#2ECC71"; border = "#27AE60"; cursor = Qt.CursorShape.ForbiddenCursor
        else:
            color = "#95A5A6"; hover = "#95A5A6"; border = "#7F8C8D"; cursor = Qt.CursorShape.ForbiddenCursor

        btn = QPushButton(f"{room_num}\n{desc}\n{status}")
        btn.setFixedSize(120, 90); btn.setCursor(cursor)
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {color}; color: white; border-radius: 8px; font-weight: bold; border: 2px solid {border}; }} "
            f"QPushButton:hover {{ background-color: {hover}; }}"
        )
        if status == 'Dirty':
            btn.clicked.connect(lambda checked, rn=room_num: self.open_assign_dialog(rn))
        elif status == 'Cleaning':
            btn.clicked.connect(lambda checked, rn=room_num: self.finish_cleaning(rn))
        else:
            btn.setDisabled(True)
        return btn

    def open_assign_dialog(self, room_num):
        dlg = AssignCleanerDialog(self, room_num, self.ctrl)
        if dlg.exec() == 1: self.refresh()

    def finish_cleaning(self, room_num):
        if QMessageBox.question(self, "Confirm", f"Room {room_num} cleaning finished? (Mark Vacant)") == QMessageBox.StandardButton.Yes:
            res, msg = self.ctrl.finish_cleaning(room_num)
            if res: QMessageBox.information(self, "Success", msg)
            self.refresh()


class AssignCleanerDialog(QDialog):
    def __init__(self, parent, room_num, ctrl):
        super().__init__(parent)
        self.setWindowTitle(f"Assign Cleaner for Room {room_num}")
        self.setFixedSize(350, 200)
        self.ctrl = ctrl; self.room_num = room_num
        l = QVBoxLayout(self)
        l.addWidget(QLabel("Select Available Cleaner:", styleSheet="font-weight:bold; font-size:14px;"))
        self.cb = QComboBox()
        cleaners = [c[1] for c in self.ctrl.get_available_cleaners()]
        self.cb.addItems(cleaners); self.cb.setStyleSheet(INPUT_STYLE)
        l.addWidget(self.cb)
        if not cleaners:
            l.addWidget(QLabel("No available cleaners!", styleSheet="color:red;"))
            self.cb.setDisabled(True)
        btn = QPushButton("Assign and Start Cleaning"); btn.setStyleSheet(BTN_STYLE)
        btn.clicked.connect(self.assign)
        if not cleaners: btn.setDisabled(True)
        l.addWidget(btn)

    def assign(self):
        res, msg = self.ctrl.assign_cleaner(self.room_num, self.cb.currentText())
        if res: QMessageBox.information(self, "Success", msg); self.accept()
        else:   QMessageBox.warning(self, "Error", msg)


# ── Receipt Preview Dialog ────────────────────────────────────────────────────
class ReceiptPreviewDialog(QDialog):
    def __init__(self, parent, receipt_data, paid, method, pay_id, ctrl):
        super().__init__(parent)
        self.setWindowTitle("Transaction Confirmed"); self.setFixedSize(400, 250)
        self.ctrl = ctrl; self.receipt_data = receipt_data
        self.paid = paid; self.method = method; self.pay_id = pay_id

        l = QVBoxLayout(self); l.setContentsMargins(25, 25, 25, 25)
        l.addWidget(QLabel("✅ Transaction Successful!", styleSheet="font-size: 18px; font-weight: 800; color: #27AE60;"),
                   alignment=Qt.AlignmentFlag.AlignCenter)
        bid_str = receipt_data['bid'] if receipt_data else 'N/A'
        l.addWidget(QLabel(f"Booking ID: {bid_str}", styleSheet="font-size: 14px; font-weight: bold; color: #555;"),
                   alignment=Qt.AlignmentFlag.AlignCenter)
        l.addSpacing(15)
        if receipt_data:
            l.addWidget(QLabel("Would you like to generate a PDF receipt for this transaction?"),
                       alignment=Qt.AlignmentFlag.AlignCenter)
        else:
            l.addWidget(QLabel("Credit Card Guarantee applied (No immediate receipt generated)."),
                       alignment=Qt.AlignmentFlag.AlignCenter)
        l.addStretch()

        btn_box = QHBoxLayout(); btn_box.setSpacing(10)
        if receipt_data:
            btn_pdf = QPushButton("📄 Generate PDF Receipt")
            btn_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_pdf.setStyleSheet("background: #E67E22; color: white; padding: 12px; font-weight: bold; border-radius: 5px;")
            btn_pdf.clicked.connect(self.generate_pdf); btn_box.addWidget(btn_pdf)

        btn_close = QPushButton("Confirm Without Receipt")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("background: #7F8C8D; color: white; padding: 12px; font-weight: bold; border-radius: 5px;")
        btn_close.clicked.connect(self.accept); btn_box.addWidget(btn_close)
        l.addLayout(btn_box)

    def generate_pdf(self):
        if self.receipt_data:
            self.ctrl.generate_receipt(self.receipt_data, self.paid, self.method, self.pay_id)
            QMessageBox.information(self, "Success", "PDF Receipt generated successfully! Check your 'receipts' folder.")
        self.accept()