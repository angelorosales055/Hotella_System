from Model.m_database import Database

class AdminModel:
    def __init__(self):
        self.db = Database()

    # 🟢 DASHBOARD: New Stats Methods
    def get_total_revenue_year(self, year):
        c = self.db.get_cursor()
        try:
            # ✅ FIX: Sum amount_paid (actual cash collected), not grand_total (duplicated per booking)
            c.execute("SELECT SUM(amount_paid) FROM payments WHERE date_paid LIKE %s", (f"{year}%",))
            res = c.fetchone()[0]
            return res if res else 0
        finally:
            if c: c.close()

    def get_employee_count(self):
        c = self.db.get_cursor()
        try:
            # Counts active employees (excluding inactive ones is usually better for dashboards)
            c.execute("SELECT COUNT(*) FROM employees WHERE status != 'Inactive'")
            res = c.fetchone()[0]
            return res if res else 0
        finally:
            if c: c.close()

    # --- EXISTING ANALYTICS & REPORT METHODS ---
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

    def get_detailed_revenue_report(self):
        c = self.db.get_cursor()
        try:
            sql = """
                SELECT 
                    p.customer_name, 
                    t.room_number, 
                    b.date, 
                    b.days, 
                    p.grand_total, 
                    p.date_paid,
                    p.booking_id
                FROM payments p
                LEFT JOIN bookings b ON p.booking_id = b.id
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
            sql_pay = "SELECT p.id, p.booking_id, p.customer_name, p.room_total, p.service_total, p.grand_total, p.method, p.date_paid, p.amount_paid, p.card_number, p.processed_by, p.remarks FROM payments p ORDER BY p.date_paid DESC"
            c.execute(sql_pay)
            data['payments'] = c.fetchall()

            c.execute("SELECT id, name, room_type, date, days, price, status FROM bookings ORDER BY date DESC")
            data['bookings'] = c.fetchall()

            sql_svc = "SELECT s.service_name, s.price, s.date, s.quantity, s.room_number, b.name FROM services s LEFT JOIN bookings b ON s.booking_id = b.id ORDER BY s.date DESC"
            c.execute(sql_svc)
            data['services'] = c.fetchall()

            c.execute("SELECT room_number, action, date_time FROM housekeeping_logs ORDER BY date_time DESC")
            data['housekeeping'] = c.fetchall()

            c.execute("SELECT guest_name, action_type, timestamp, booking_id, performed_by FROM booking_logs ORDER BY timestamp DESC")
            data['logs'] = c.fetchall()

            return data
        finally:
            if c: c.close()

    # --- STANDARD MANAGEMENT METHODS ---
    def get_all_employees(self):
        c = self.db.get_cursor()
        try:
            sql = "SELECT e.id, e.name, e.role, e.contact, e.status, u.username FROM employees e LEFT JOIN users u ON e.id = u.employee_id WHERE e.role != 'Manager' ORDER BY e.id DESC"
            c.execute(sql); return c.fetchall()
        finally: c.close()

    def add_employee(self, name, role, contact):
        c = self.db.get_cursor()
        try:
            c.execute("INSERT INTO employees (name, role, contact, status) VALUES (%s, %s, %s, 'Active')", (name, role, contact))
            c.execute("SELECT LAST_INSERT_ID()")
            emp_id = c.fetchone()[0]
            self.db.conn.commit(); return emp_id
        except: self.db.conn.rollback(); return None
        finally: c.close()

    def create_user_account(self, u, p, r, eid):
        c = self.db.get_cursor()
        try:
            c.execute("INSERT INTO users (username, password, role, employee_id) VALUES (%s, %s, %s, %s)", (u, p, r, eid))
            self.db.conn.commit(); return True
        except: self.db.conn.rollback(); return False
        finally: c.close()

    def update_employee_status(self, eid, s):
        c = self.db.get_cursor()
        try:
            c.execute("UPDATE employees SET status=%s WHERE id=%s", (s, eid))
            self.db.conn.commit(); return True
        except: return False
        finally: c.close()

    def delete_employee(self, eid):
        c = self.db.get_cursor()
        try:
            c.execute("DELETE FROM users WHERE employee_id=%s", (eid,))
            c.execute("DELETE FROM employees WHERE id=%s", (eid,))
            self.db.conn.commit(); return True
        except: self.db.conn.rollback(); return False
        finally: c.close()

    def get_room_history_data(self, r): c = self.db.get_cursor(); c.execute("SELECT b.id, b.name, b.date, b.days, b.status, b.created_by FROM transactions t JOIN bookings b ON t.booking_id = b.id WHERE t.room_number = %s ORDER BY b.date DESC", (r,)); return c.fetchall()
    def get_all_activity_logs(self): c = self.db.get_cursor(); c.execute("SELECT * FROM booking_logs ORDER BY timestamp DESC LIMIT 200"); return c.fetchall()
    def check_active_bookings(self, r): c = self.db.get_cursor(); c.execute("SELECT COUNT(*) FROM transactions t JOIN bookings b ON t.booking_id = b.id WHERE t.room_number = %s AND b.status IN ('Confirmed', 'Arrived', 'Checked In')", (r,)); return c.fetchone()[0] > 0
    def update_room_status(self, r, s): c = self.db.get_cursor(); c.execute("UPDATE rooms SET status=%s WHERE room_number=%s", (s, r)); self.db.conn.commit(); return True
    def update_room_type(self, r, t): c = self.db.get_cursor(); c.execute("UPDATE rooms SET description=%s WHERE room_number=%s", (t, r)); self.db.conn.commit(); return True
    def get_all_bookings(self): c = self.db.get_cursor(); c.execute("SELECT id, name, email, phone, address, room_type, date, days, price FROM bookings ORDER BY id DESC"); return c.fetchall()
    def get_all_rooms(self): c = self.db.get_cursor(); c.execute("SELECT room_number, description, status FROM rooms ORDER BY room_number"); return c.fetchall()
    def get_payments_by_date(self, s, e): c = self.db.get_cursor(); c.execute("SELECT * FROM payments"); res = c.fetchall(); return [p for p in res if s <= str(p[7]).split(' ')[0] <= e]
    def get_all_services(self): c = self.db.get_cursor(); c.execute("SELECT * FROM services ORDER BY date DESC"); return c.fetchall()
    def get_all_payments(self): c = self.db.get_cursor(); c.execute("SELECT * FROM payments ORDER BY date_paid DESC"); return c.fetchall()
    def get_housekeeping_logs(self): c = self.db.get_cursor(); c.execute("SELECT * FROM housekeeping_logs ORDER BY date_time DESC"); return c.fetchall()
    def add_booking(self, d): self.db.add_booking(*d)
    def update_booking(self, o, d): self.db.update_booking(o, *d)
    def delete_booking(self, e): self.db.delete_booking(e)
    def add_room(self, d): self.db.add_room(*d)
    def update_room(self, o, d): self.db.update_room(o, *d)
    def delete_room(self, r): self.db.delete_room(r)
    def delete_service(self, s): self.db.delete_service(s)

    def get_all_room_history_data(self):
        c = self.db.get_cursor()
        try:
            c.execute("SELECT t.room_number, b.id, b.name, b.date, b.days, b.status, b.created_by FROM transactions t JOIN bookings b ON t.booking_id = b.id ORDER BY b.date DESC")
            return c.fetchall()
        except Exception as e:
            print("Error fetching history:", e)
            return []
        finally:
            if c: c.close()