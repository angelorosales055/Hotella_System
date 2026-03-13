from Model.m_admin import AdminModel
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtGui import QTextDocument, QPageSize, QPageLayout
from PyQt6.QtCore import QSizeF
from datetime import datetime, timedelta
import calendar


class AdminController:
    def __init__(self):
        self.model = AdminModel()

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def format_card_number(card_num, method):

        if not card_num or card_num == 'None' or str(card_num).strip() == '':
            return "N/A"

        card_num = str(card_num).replace(' ', '').replace('-', '').replace('*', '')
        if not card_num.isdigit():
            return "Invalid"

        if "Credit" in str(method):
            if len(card_num) >= 16:
                return f"**** **** **** {card_num[-4:]}"
            elif len(card_num) >= 4:
                return f"**** {card_num[-4:]}"
            return card_num
        elif "Debit" in str(method):
            if len(card_num) >= 12:
                return f"**** **** **** {card_num[-4:]}"
            elif len(card_num) >= 4:
                return f"**** {card_num[-4:]}"
            return card_num
        return "N/A"

    # ── Dashboard ─────────────────────────────────────────────────────────────

    def get_dashboard_stats(self):
        current_year = datetime.now().year
        return {
            'bookings':  len(self.model.get_all_bookings()),
            'revenue':   self.model.get_total_revenue_year(current_year),
            'employees': self.model.get_employee_count(),
            'rooms':     len(self.model.get_all_rooms()),
            'year':      current_year,
        }

    # ── Analytics ─────────────────────────────────────────────────────────────

    def get_available_dates(self):
        """Return {year: [month_str, ...]} dict derived from payment dates."""
        raw_dates = self.model.get_payment_dates()
        data = {}
        for d_str in raw_dates:
            try:
                date_part = d_str.split(' ')[0]
                year, month, _ = date_part.split('-')
                data.setdefault(year, set()).add(month)
            except Exception:
                continue
        return {y: sorted(list(data[y])) for y in sorted(data.keys(), reverse=True)}

    def get_current_month_stats(self):
        now = datetime.now()
        last_day = calendar.monthrange(now.year, now.month)[1]
        s_date = f"{now.year}-{now.month:02d}-01"
        e_date = f"{now.year}-{now.month:02d}-{last_day}"
        data = self.get_analytics(s_date, e_date)
        return {
            'total':      data['rev_room'] + data['rev_svc'],
            'room':       data['rev_room'],
            'service':    data['rev_svc'],
            'month_name': calendar.month_name[now.month],
        }

    def get_analytics(self, s_date, e_date):
        payments, bookings, services = self.model.get_analytics_data()
        all_rooms_data = self.model.get_all_rooms()

        pay_filt  = [p for p in payments  if s_date <= str(p[7]).split(' ')[0] <= e_date]
        book_filt = [b for b in bookings  if s_date <= str(b[1]) <= e_date]
        svc_filt  = [s for s in services  if s[1] and s_date <= str(s[1]).split(' ')[0] <= e_date]

        rev_room = sum(p[3] for p in pay_filt)
        rev_svc  = sum(p[4] for p in pay_filt)

        unique_types = set(r[1] for r in all_rooms_data if r[1]) or {"Single", "Double", "Queen", "King", "Suite"}
        room_counts  = {t: 0 for t in unique_types}
        for b in book_filt:
            rtype = b[0] or "Unknown"
            room_counts[rtype] = room_counts.get(rtype, 0) + 1

        official_services = {"Breakfast Set", "Lunch Set", "Dinner Set", "Laundry (Per kg)", "Cleaning Service"}
        svc_counts = {name: 0 for name in official_services}
        for s in svc_filt:
            sname = s[0] or "Misc"
            if sname in official_services:
                qty = s[3] if len(s) > 3 else 1
                svc_counts[sname] += qty

        return {'rev_room': rev_room, 'rev_svc': rev_svc,
                'room_counts': room_counts, 'svc_counts': svc_counts}

    def get_daily_revenue(self, year, month):
        """Return per-day revenue list for a given year/month (or monthly if month=='All')."""
        if month == "All":
            return self.get_monthly_revenue(year)
        # Delegate all DB work to the model
        return self.model.get_daily_revenue_data(year, month)

    def get_monthly_revenue(self, year):
        """Return per-month revenue list for a given year."""
        return self.model.get_monthly_revenue_data(year)

    # ── PDF Export ────────────────────────────────────────────────────────────

    def export_report(self, year, month_num, options=None, generated_by="Admin"):
        if options is None:
            options = {'financial': True, 'rooms': True, 'logs': True}

        if month_num == "All":
            start_date   = f"{year}-01-01"
            end_date     = f"{year}-12-31"
            period_label = f"Annual Report - {year}"
        else:
            last_day     = calendar.monthrange(int(year), int(month_num))[1]
            start_date   = f"{year}-{month_num}-01"
            end_date     = f"{year}-{month_num}-{last_day}"
            period_label = f"{calendar.month_name[int(month_num)]} {year}"

        all_data = self.model.get_report_data_comprehensive()

        def in_range(date_str):
            try:
                return start_date <= str(date_str).split(' ')[0] <= end_date
            except Exception:
                return False

        payments      = [p for p in all_data['payments']    if in_range(p[7])]
        bookings      = [b for b in all_data['bookings']    if in_range(b[3])]
        services      = [s for s in all_data['services']    if in_range(s[2])]
        housekeeping  = [h for h in all_data['housekeeping'] if in_range(h[2])]
        activity_logs = [l for l in all_data['logs']        if in_range(l[2])]

        total_rev       = sum(p[5] for p in payments)
        header_color    = "#E67E22"
        table_header    = "#2C3E50"
        analytics_data  = self.get_analytics(start_date, end_date)
        top_room        = max(analytics_data['room_counts'], key=analytics_data['room_counts'].get, default="N/A")
        top_room_count  = analytics_data['room_counts'].get(top_room, 0)
        top_svc         = max(analytics_data['svc_counts'],  key=analytics_data['svc_counts'].get,  default="N/A")
        top_svc_count   = analytics_data['svc_counts'].get(top_svc, 0)
        rev_room        = analytics_data['rev_room']
        rev_svc         = analytics_data['rev_svc']
        occupancy_pct   = int(
            (len([b for b in bookings if b[6] in ('Confirmed', 'Arrived', 'Checked In')]) /
             max(len(self.model.get_all_rooms()), 1)) * 100
        )
        now             = datetime.now()
        generated_on    = now.strftime("%B %d, %Y")
        generated_at    = now.strftime("%I:%M:%S %p")

        selected_sections = []
        if options.get('financial'): selected_sections.append("Financial Summary")
        if options.get('rooms'):     selected_sections.append("Room Utilization")
        if options.get('logs'):      selected_sections.append("Transaction Logs")
        report_type_label = " + ".join(selected_sections) if selected_sections else "Full Report"

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; font-size: 10px; }}
                h1 {{ color: {header_color}; margin-bottom: 5px; }}
                h3 {{ color: #555; margin-top: 0; }}
                h2 {{ color: {header_color}; border-bottom: 2px solid {header_color}; padding-bottom: 5px; margin-top: 25px; }}
                th {{ background-color: {table_header}; color: white; padding: 6px; font-weight: bold; text-align: left; }}
                td {{ padding: 6px; color: #333; border-bottom: 1px solid #eee; }}
                .total-box {{ background-color: #f9f9f9; padding: 15px; border: 1px solid #ddd; margin-bottom: 20px; }}
                .meta-table td {{ border: none; padding: 3px 8px; font-size: 10px; }}
                .meta-label {{ color: #888; font-weight: bold; }}
                .analytics-grid {{ width: 100%; border-collapse: collapse; margin-bottom: 15px; }}
                .analytics-grid td {{ border: 1px solid #ddd; padding: 10px; text-align: center; background: #f9f9f9; }}
                .analytics-grid .a-val {{ font-size: 16px; font-weight: bold; color: {header_color}; }}
                .analytics-grid .a-lbl {{ font-size: 9px; color: #888; }}
            </style>
        </head>
        <body>
            <center>
                <h1>HOTELLA MANAGEMENT REPORT</h1>
                <h3>{period_label}</h3>
            </center>
            <table class="meta-table" width="100%" cellpadding="0" cellspacing="0"
                   style="border: 1px solid #ddd; border-radius: 4px; margin-bottom: 15px; background: #fafafa;">
                <tr>
                    <td class="meta-label">Generated By:</td><td>{generated_by}</td>
                    <td class="meta-label">Report Type:</td><td>{report_type_label}</td>
                </tr>
                <tr>
                    <td class="meta-label">Date Generated:</td><td>{generated_on}</td>
                    <td class="meta-label">Time Generated:</td><td>{generated_at}</td>
                </tr>
                <tr>
                    <td class="meta-label">Period Covered:</td><td>{start_date} to {end_date}</td>
                    <td class="meta-label">Total Transactions:</td><td>{len(payments)}</td>
                </tr>
            </table>
            <h2>Analytics Snapshot</h2>
            <table class="analytics-grid" cellpadding="0" cellspacing="0">
                <tr>
                    <td><div class="a-val">₱{total_rev:,}</div><div class="a-lbl">Total Revenue</div></td>
                    <td><div class="a-val">₱{rev_room:,}</div><div class="a-lbl">Room Revenue</div></td>
                    <td><div class="a-val">₱{rev_svc:,}</div><div class="a-lbl">Service Revenue</div></td>
                    <td><div class="a-val">{len(bookings)}</div><div class="a-lbl">New Bookings</div></td>
                    <td><div class="a-val">{occupancy_pct}%</div><div class="a-lbl">Occupancy Rate</div></td>
                    <td><div class="a-val">{top_room} ({top_room_count})</div><div class="a-lbl">Top Room Type</div></td>
                    <td><div class="a-val">{top_svc} ({top_svc_count})</div><div class="a-lbl">Top Service</div></td>
                </tr>
            </table>
        """

        if options.get('financial'):
            html += f"""
            <div class="total-box">
                <span style="font-size: 12px; font-weight: bold; color: {table_header};">TOTAL REVENUE: </span>
                <span style="font-size: 16px; font-weight: bold; color: {header_color};">₱{total_rev:,}</span>
                <br>
                <span style="font-size: 10px;">Transactions: {len(payments)} | New Bookings: {len(bookings)}</span>
            </div>
            <h2>Revenue / Payments</h2>
            <table width="100%" border="0" cellspacing="0" cellpadding="4">
                <tr><th>ID</th><th>Guest</th><th>Amount</th><th>Method</th><th>Card Number</th><th>Date</th></tr>
            """
            for p in payments:
                card_display = self.format_card_number(p[9], p[6])
                html += f"<tr><td>{p[1]}</td><td>{p[2]}</td><td>₱{p[5]:,}</td><td>{p[6]}</td><td>{card_display}</td><td>{p[7]}</td></tr>"
            if not payments:
                html += "<tr><td colspan='6' align='center'>No Data</td></tr>"
            html += "</table>"

        if options.get('rooms'):
            html += """
            <h2>Booking History</h2>
            <table width="100%" border="0" cellspacing="0" cellpadding="4">
                <tr><th>ID</th><th>Name</th><th>Type</th><th>Status</th><th>Date</th></tr>
            """
            for b in bookings:
                html += f"<tr><td>B{b[0]:05d}</td><td>{b[1]}</td><td>{b[2]}</td><td>{b[6]}</td><td>{b[3]}</td></tr>"
            if not bookings:
                html += "<tr><td colspan='5' align='center'>No Data</td></tr>"
            html += "</table>"

        if options.get('logs'):
            html += """
            <h2>Services Availed</h2>
            <table width="100%" border="0" cellspacing="0" cellpadding="4">
                <tr><th>Service</th><th>Guest Name</th><th>Room</th><th>Qty</th><th>Price</th><th>Date</th></tr>
            """
            for s in services:
                guest_name = s[5] if s[5] else "Unknown"
                html += f"<tr><td>{s[0]}</td><td>{guest_name}</td><td>{s[4]}</td><td>{s[3]}</td><td>₱{s[1]:,}</td><td>{s[2]}</td></tr>"
            if not services:
                html += "<tr><td colspan='6' align='center'>No Data</td></tr>"
            html += "</table>"

            html += """
            <h2>Booking Activity Log</h2>
            <table width="100%" border="0" cellspacing="0" cellpadding="4">
                <tr><th>Timestamp</th><th>Booking ID</th><th>Guest</th><th>Action</th><th>Staff</th></tr>
            """
            for log in activity_logs:
                html += f"<tr><td>{log[2]}</td><td>{log[3]}</td><td>{log[0]}</td><td>{log[1]}</td><td>{log[4]}</td></tr>"
            if not activity_logs:
                html += "<tr><td colspan='5' align='center'>No Data</td></tr>"
            html += "</table>"

            html += """
            <h2>Housekeeping Logs</h2>
            <table width="100%" border="0" cellspacing="0" cellpadding="4">
                <tr><th>Room</th><th>Action</th><th>Time</th></tr>
            """
            for h in housekeeping:
                html += f"<tr><td>{h[0]}</td><td>{h[1]}</td><td>{h[2]}</td></tr>"
            if not housekeeping:
                html += "<tr><td colspan='3' align='center'>No Data</td></tr>"
            html += "</table>"

            html += """<br><br><div style="text-align:center; color:gray; font-size: 11px;">
                Generated by Hotella Management System<br>
                &copy; 2026 Hotella. All rights reserved.
                </div></body></html>"""

        fn, _ = QFileDialog.getSaveFileName(
            None, "Save Report",
            f"Custom_Report_{year}_{month_num}.pdf",
            "PDF Files (*.pdf)"
        )
        if fn:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(fn)
            printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            printer.setPageOrientation(QPageLayout.Orientation.Portrait)
            doc = QTextDocument()
            doc.setHtml(html)
            doc.setPageSize(QSizeF(printer.pageRect(QPrinter.Unit.Point).size()))
            doc.print(printer)
            return True, "Custom Report saved successfully!"
        return False, "Export cancelled by user."

    # ── Employee management ───────────────────────────────────────────────────

    def get_employees(self):
        return self.model.get_all_employees()

    def add_new_employee(self, name, role, contact, username, password):
        if not name or not role:
            return False, "Name and Role are required."
        if role == "Manager":
            return False, "Cannot create a Manager account."
        needs_account = (role == "Receptionist")
        if needs_account and (not username or not password):
            return False, "Username and Password are required for Receptionists."
        emp_id = self.model.add_employee(name, role, contact)
        if not emp_id:
            return False, "Database error while creating employee."
        if needs_account:
            self.model.create_user_account(username, password, 'staff', emp_id)
        return True, "Employee added successfully."

    def set_employee_status(self, emp_id, status):
        return self.model.update_employee_status(emp_id, status), "Status updated."

    def remove_employee(self, emp_id):
        return self.model.delete_employee(emp_id), "Employee removed."

    # ── Room management ───────────────────────────────────────────────────────

    def get_all_rooms(self):
        return self.model.get_all_rooms()

    def save_room(self, is_new, data, old_id=None):
        try:
            if is_new:
                self.model.add_room(data)
            else:
                self.model.update_room(old_id, data)
            return True, "Room saved successfully."
        except Exception as e:
            return False, str(e)

    def delete_room(self, room_number):
        self.model.delete_room(room_number)

    def set_room_status(self, room_number, status):
        if status == "Maintenance" and self.model.check_active_bookings(room_number):
            return False, "Cannot set to Maintenance: room has active bookings."
        return self.model.update_room_status(room_number, status), "Room status updated."

    def change_room_type(self, room_number, room_type):
        if self.model.check_active_bookings(room_number):
            return False, "Cannot change type: room has active bookings."
        return self.model.update_room_type(room_number, room_type), "Room type updated."

    def get_room_history(self, room_number):
        return self.model.get_room_history_data(room_number)

    def get_all_room_history(self):
        return self.model.get_all_room_history_data()

    # ── Booking management ────────────────────────────────────────────────────

    def get_filtered_bookings(self, start_date, end_date):
        return [b for b in self.model.get_all_bookings()
                if start_date <= (b[6] or "") <= end_date]

    def delete_booking(self, email):
        self.model.delete_booking(email)

    # ── Services & Payments ───────────────────────────────────────────────────

    def get_all_services(self):
        return self.model.get_all_services()

    def delete_service(self, service_id):
        self.model.delete_service(service_id)

    def get_all_payments(self):
        return self.model.get_all_payments()

    # ── Logs ──────────────────────────────────────────────────────────────────

    def get_activity_logs(self):
        return self.model.get_all_activity_logs()

    def get_unified_system_logs(self):
        """
        Merge booking_logs and service records into one sorted list.
        Previously this logic lived inside the View (SystemLogsTab).
        """
        unified = []

        # Booking logs
        for log in (self.model.get_all_activity_logs() or []):
            unified.append({
                'bid':    log[1],
                'target': str(log[2]),
                'action': str(log[3]),
                'staff':  str(log[5]) if len(log) > 5 and log[5] else "System Admin",
                'time':   str(log[4]),
            })

        # Service logs merged from history + services tables
        try:
            services = self.model.get_all_services() or []
            history  = self.model.get_all_room_history_data() or []
            employees = self.model.get_all_employees() or []

            guest_map = {h[1]: str(h[2]) for h in history}
            staff_map = {h[1]: str(h[6]) if len(h) > 6 else "System Admin" for h in history}
            emp_map   = {str(e[0]): str(e[1]) for e in employees}

            for s in services:
                bid      = s[1]
                svc_name = s[3]
                price    = s[4]
                svc_date = str(s[5])

                is_duplicate = any(
                    str(bid) == str(l['bid']) and svc_name in l['action'] and svc_date in l['time']
                    for l in unified
                )
                if is_duplicate:
                    continue

                if len(s) > 6 and s[6]:
                    emp_id_str = str(s[6])
                    staff_name = emp_map.get(emp_id_str, f"Staff ID {emp_id_str}") \
                        if emp_id_str.isdigit() else emp_id_str
                else:
                    staff_name = staff_map.get(bid, "System Admin")

                unified.append({
                    'bid':    bid,
                    'target': guest_map.get(bid, "Unknown Guest"),
                    'action': f"Service: {svc_name} (₱{price:,})",
                    'staff':  staff_name,
                    'time':   f"{svc_date} 00:00:00",
                })
        except Exception as e:
            print(f"[get_unified_system_logs] Error merging service logs: {e}")

        unified.sort(key=lambda x: x['time'], reverse=True)
        return unified
