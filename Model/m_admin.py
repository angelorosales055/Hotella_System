import calendar as _calendar
from Model.m_database import Database


class AdminModel:
    def __init__(self):
        self.db = Database()

    # ── Dashboard ─────────────────────────────────────────────────────────────

    def get_total_revenue_year(self, year):
        c = self.db.get_cursor()
        try:
            c.execute(
                "SELECT SUM(amount_paid) FROM payments WHERE date_paid LIKE %s",
                (f"{year}%",)
            )
            res = c.fetchone()[0]
            return res if res else 0
        finally:
            if c: c.close()

    def get_employee_count(self):
        c = self.db.get_cursor()
        try:
            c.execute("SELECT COUNT(*) FROM employees WHERE status != 'Inactive'")
            res = c.fetchone()[0]
            return res if res else 0
        finally:
            if c: c.close()

    # ── Analytics ─────────────────────────────────────────────────────────────

    def get_payment_dates(self):
        c = self.db.get_cursor()
        try:
            c.execute("SELECT date_paid FROM payments")
            return [row[0] for row in c.fetchall()]
        finally:
            if c: c.close()

    def get_analytics_data(self):
        c = self.db.get_cursor()
        try:
            c.execute("SELECT * FROM payments")
            payments = c.fetchall()
            c.execute("SELECT room_type, date FROM bookings WHERE status != 'Cancelled'")
            bookings = c.fetchall()
            c.execute("SELECT service_name, date, price, quantity FROM services")
            services = c.fetchall()
            return payments, bookings, services
        finally:
            if c: c.close()

    def get_daily_revenue_data(self, year, month):
        """Return a list of dicts with per-day revenue for a given year/month."""
        last_day   = _calendar.monthrange(int(year), int(month))[1]
        start_date = f"{year}-{month:02d}-01"
        end_date   = f"{year}-{month:02d}-{last_day}"

        c = self.db.get_cursor()
        try:
            sql = """
                SELECT DATE(date_paid)           AS day,
                       SUM(room_total)           AS room_rev,
                       SUM(service_total)        AS service_rev,
                       COUNT(DISTINCT booking_id) AS bookings
                FROM payments
                WHERE DATE(date_paid) BETWEEN %s AND %s
                GROUP BY DATE(date_paid)
                ORDER BY day
            """
            c.execute(sql, (start_date, end_date))
            results = c.fetchall()

            daily_data = {
                f"{year}-{month:02d}-{day:02d}": {
                    'room_rev': 0, 'service_rev': 0,
                    'total_rev': 0, 'bookings': 0, 'day': day
                }
                for day in range(1, last_day + 1)
            }

            for row in results:
                date_str = str(row[0])
                if date_str in daily_data:
                    daily_data[date_str].update({
                        'room_rev':    float(row[1] or 0),
                        'service_rev': float(row[2] or 0),
                        'total_rev':   float(row[1] or 0) + float(row[2] or 0),
                        'bookings':    int(row[3] or 0),
                    })
            return list(daily_data.values())
        finally:
            if c: c.close()

    def get_monthly_revenue_data(self, year):
        """Return a list of dicts with per-month revenue for a given year."""
        c = self.db.get_cursor()
        try:
            monthly_data = []
            for month in range(1, 13):
                start    = f"{year}-{month:02d}-01"
                last_day = _calendar.monthrange(int(year), month)[1]
                end      = f"{year}-{month:02d}-{last_day}"

                sql = """
                    SELECT COALESCE(SUM(room_total),    0) AS room_rev,
                           COALESCE(SUM(service_total), 0) AS service_rev,
                           COUNT(DISTINCT booking_id)      AS bookings
                    FROM payments
                    WHERE DATE(date_paid) BETWEEN %s AND %s
                """
                c.execute(sql, (start, end))
                row = c.fetchone()

                monthly_data.append({
                    'month':       month,
                    'month_name':  _calendar.month_abbr[month],
                    'room_rev':    float(row[0] or 0),
                    'service_rev': float(row[1] or 0),
                    'total_rev':   float(row[0] or 0) + float(row[1] or 0),
                    'bookings':    int(row[2] or 0),
                })
            return monthly_data
        finally:
            if c: c.close()

    def get_detailed_revenue_report(self):
        c = self.db.get_cursor()
        try:
            sql = """
                SELECT p.customer_name, t.room_number, b.date, b.days,
                       p.grand_total, p.date_paid, p.booking_id
                FROM payments p
                LEFT JOIN bookings b     ON p.booking_id = b.id
                LEFT JOIN transactions t ON t.booking_id = b.id
                ORDER BY p.date_paid DESC
            """
            c.execute(sql)
            return c.fetchall()
        finally:
            if c: c.close()

    def get_report_data_comprehensive(self):
        c = self.db.get_cursor()
        data = {}
        try:
            c.execute(
                "SELECT p.id, p.booking_id, p.customer_name, p.room_total, p.service_total, "
                "p.grand_total, p.method, p.date_paid, p.amount_paid, p.card_number, "
                "p.processed_by, p.remarks FROM payments p ORDER BY p.date_paid DESC"
            )
            data['payments'] = c.fetchall()

            c.execute(
                "SELECT id, name, room_type, date, days, price, status "
                "FROM bookings ORDER BY date DESC"
            )
            data['bookings'] = c.fetchall()

            c.execute(
                "SELECT s.service_name, s.price, s.date, s.quantity, s.room_number, b.name "
                "FROM services s LEFT JOIN bookings b ON s.booking_id = b.id ORDER BY s.date DESC"
            )
            data['services'] = c.fetchall()

            c.execute(
                "SELECT room_number, action, date_time FROM housekeeping_logs ORDER BY date_time DESC"
            )
            data['housekeeping'] = c.fetchall()

            c.execute(
                "SELECT guest_name, action_type, timestamp, booking_id, performed_by "
                "FROM booking_logs ORDER BY timestamp DESC"
            )
            data['logs'] = c.fetchall()

            return data
        finally:
            if c: c.close()

    # ── Employee management ───────────────────────────────────────────────────

    def get_all_employees(self):
        c = self.db.get_cursor()
        try:
            c.execute(
                "SELECT e.id, e.name, e.role, e.contact, e.status, u.username "
                "FROM employees e LEFT JOIN users u ON e.id = u.employee_id "
                "WHERE e.role != 'Manager' ORDER BY e.id DESC"
            )
            return c.fetchall()
        finally:
            c.close()

    def add_employee(self, name, role, contact):
        c = self.db.get_cursor()
        try:
            c.execute(
                "INSERT INTO employees (name, role, contact, status) VALUES (%s, %s, %s, 'Active')",
                (name, role, contact)
            )
            c.execute("SELECT LAST_INSERT_ID()")
            emp_id = c.fetchone()[0]
            self.db.conn.commit()
            return emp_id
        except Exception:
            self.db.conn.rollback()
            return None
        finally:
            c.close()

    def create_user_account(self, username, password, role, emp_id):
        c = self.db.get_cursor()
        try:
            c.execute(
                "INSERT INTO users (username, password, role, employee_id) VALUES (%s, %s, %s, %s)",
                (username, password, role, emp_id)
            )
            self.db.conn.commit()
            return True
        except Exception:
            self.db.conn.rollback()
            return False
        finally:
            c.close()

    def update_employee_status(self, emp_id, status):
        c = self.db.get_cursor()
        try:
            c.execute("UPDATE employees SET status=%s WHERE id=%s", (status, emp_id))
            self.db.conn.commit()
            return True
        except Exception:
            return False
        finally:
            c.close()

    def delete_employee(self, emp_id):
        c = self.db.get_cursor()
        try:
            c.execute("DELETE FROM users WHERE employee_id=%s", (emp_id,))
            c.execute("DELETE FROM employees WHERE id=%s", (emp_id,))
            self.db.conn.commit()
            return True
        except Exception:
            self.db.conn.rollback()
            return False
        finally:
            c.close()

    # ── Room management ───────────────────────────────────────────────────────

    def get_all_rooms(self):
        c = self.db.get_cursor()
        try:
            c.execute("SELECT room_number, description, status FROM rooms ORDER BY room_number")
            return c.fetchall()
        finally:
            c.close()

    def check_active_bookings(self, room_number):
        c = self.db.get_cursor()
        try:
            c.execute(
                "SELECT COUNT(*) FROM transactions t "
                "JOIN bookings b ON t.booking_id = b.id "
                "WHERE t.room_number = %s AND b.status IN ('Confirmed','Arrived','Checked In')",
                (room_number,)
            )
            return c.fetchone()[0] > 0
        finally:
            c.close()

    def update_room_status(self, room_number, status):
        c = self.db.get_cursor()
        try:
            c.execute("UPDATE rooms SET status=%s WHERE room_number=%s", (status, room_number))
            self.db.conn.commit()
            return True
        finally:
            c.close()

    def update_room_type(self, room_number, room_type):
        c = self.db.get_cursor()
        try:
            c.execute("UPDATE rooms SET description=%s WHERE room_number=%s", (room_type, room_number))
            self.db.conn.commit()
            return True
        finally:
            c.close()

    def get_room_history_data(self, room_number):
        c = self.db.get_cursor()
        try:
            c.execute(
                "SELECT b.id, b.name, b.date, b.days, b.status, b.created_by "
                "FROM transactions t JOIN bookings b ON t.booking_id = b.id "
                "WHERE t.room_number = %s ORDER BY b.date DESC",
                (room_number,)
            )
            return c.fetchall()
        finally:
            c.close()

    def get_all_room_history_data(self):
        c = self.db.get_cursor()
        try:
            c.execute(
                "SELECT t.room_number, b.id, b.name, b.date, b.days, b.status, b.created_by "
                "FROM transactions t JOIN bookings b ON t.booking_id = b.id "
                "ORDER BY b.date DESC"
            )
            return c.fetchall()
        except Exception as e:
            print("Error fetching history:", e)
            return []
        finally:
            if c: c.close()

    def add_room(self, data):
        self.db.add_room(*data)

    def update_room(self, old_id, data):
        self.db.update_room(old_id, *data)

    def delete_room(self, room_number):
        self.db.delete_room(room_number)

    # ── Booking management ────────────────────────────────────────────────────

    def get_all_bookings(self):
        c = self.db.get_cursor()
        try:
            c.execute(
                "SELECT id, name, email, phone, address, room_type, date, days, price "
                "FROM bookings ORDER BY id DESC"
            )
            return c.fetchall()
        finally:
            c.close()

    def add_booking(self, data):
        self.db.add_booking(*data)

    def update_booking(self, old_email, data):
        self.db.update_booking(old_email, *data)

    def delete_booking(self, email):
        self.db.delete_booking(email)

    # ── Services ─────────────────────────────────────────────────────────────

    def get_all_services(self):
        c = self.db.get_cursor()
        try:
            c.execute("SELECT * FROM services ORDER BY date DESC")
            return c.fetchall()
        finally:
            c.close()

    def delete_service(self, service_id):
        self.db.delete_service(service_id)

    # ── Payments ─────────────────────────────────────────────────────────────

    def get_all_payments(self):
        c = self.db.get_cursor()
        try:
            c.execute("SELECT * FROM payments ORDER BY date_paid DESC")
            return c.fetchall()
        finally:
            c.close()

    def get_payments_by_date(self, start_date, end_date):
        c = self.db.get_cursor()
        try:
            c.execute("SELECT * FROM payments")
            res = c.fetchall()
            return [p for p in res if start_date <= str(p[7]).split(' ')[0] <= end_date]
        finally:
            c.close()

    # ── Logs ─────────────────────────────────────────────────────────────────

    def get_all_activity_logs(self):
        c = self.db.get_cursor()
        try:
            c.execute("SELECT * FROM booking_logs ORDER BY timestamp DESC LIMIT 200")
            return c.fetchall()
        finally:
            c.close()

    def get_housekeeping_logs(self):
        c = self.db.get_cursor()
        try:
            c.execute("SELECT * FROM housekeeping_logs ORDER BY date_time DESC")
            return c.fetchall()
        finally:
            c.close()
