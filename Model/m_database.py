import sys
from datetime import datetime

# Try to import MySQL connector2
try:
    import mysql.connector
except ImportError:
    print("CRITICAL ERROR: 'mysql-connector-python' is not installed.")
    sys.exit(1)


class Database:
    def __init__(self):
        self.conn = None
        try:
            # 1. Connect to Server
            self.server_conn = mysql.connector.connect(host="localhost", user="root", password="")
            cursor = self.server_conn.cursor()
            cursor.execute("CREATE DATABASE IF NOT EXISTS hotella")
            self.server_conn.commit()
            cursor.close()
            self.server_conn.close()

            # 2. Connect to Database
            self.conn = mysql.connector.connect(
                host="localhost", user="root", password="", database="hotella"
            )
            self.create_tables()
            print("Successfully connected to MySQL database: 'hotella'")

        except mysql.connector.Error as err:
            print(f"\n[DB ERROR] Could not connect: {err}")

    def get_cursor(self):
        if self.conn and self.conn.is_connected():
            return self.conn.cursor(buffered=True)
        return None

    def create_tables(self):
        c = self.get_cursor()
        if not c: return
        try:
            tables = [
                "CREATE TABLE IF NOT EXISTS users (username VARCHAR(50) PRIMARY KEY, password VARCHAR(255), role VARCHAR(20), employee_id INT)",
                "CREATE TABLE IF NOT EXISTS bookings (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(100), email VARCHAR(100), phone VARCHAR(20), address VARCHAR(255), room_type VARCHAR(50), date VARCHAR(20), days INT, price INT, status VARCHAR(50), guests_count INT DEFAULT 1, created_by VARCHAR(100) DEFAULT '---')",
                "CREATE TABLE IF NOT EXISTS rooms (id INT AUTO_INCREMENT PRIMARY KEY, room_number VARCHAR(10) UNIQUE, description VARCHAR(100), status VARCHAR(20) DEFAULT 'Vacant', assigned_employee_id INT)",
                "CREATE TABLE IF NOT EXISTS services (id INT AUTO_INCREMENT PRIMARY KEY, booking_id INT, room_number VARCHAR(10), service_name VARCHAR(100), price INT, date VARCHAR(20), employee_id INT, quantity INT DEFAULT 1)",
                "CREATE TABLE IF NOT EXISTS transactions (id INT AUTO_INCREMENT PRIMARY KEY, booking_id INT, room_number VARCHAR(10), date_confirmed VARCHAR(20))",
                "CREATE TABLE IF NOT EXISTS payments (id INT AUTO_INCREMENT PRIMARY KEY, booking_id INT, customer_name VARCHAR(100), room_total INT, service_total INT, grand_total INT, method VARCHAR(50), date_paid VARCHAR(20), amount_paid INT DEFAULT 0, card_number VARCHAR(50), processed_by VARCHAR(100) DEFAULT '---', remarks VARCHAR(50) DEFAULT 'Payment')",
                "CREATE TABLE IF NOT EXISTS housekeeping_logs (id INT AUTO_INCREMENT PRIMARY KEY, room_number VARCHAR(10), action VARCHAR(100), date_time VARCHAR(20))",
                "CREATE TABLE IF NOT EXISTS booking_logs (id INT AUTO_INCREMENT PRIMARY KEY, booking_id INT, guest_name VARCHAR(100), action_type VARCHAR(50), timestamp VARCHAR(30), performed_by VARCHAR(100) DEFAULT '---')",
                "CREATE TABLE IF NOT EXISTS employees (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(100), role VARCHAR(50), contact VARCHAR(50), status VARCHAR(20) DEFAULT 'Available')"
            ]
            for t in tables: c.execute(t)

            # Default Admin (Linked to dummy ID 999 or create one if missing)
            # NOTE: For production, ensure an employee exists for the admin.
            c.execute("INSERT IGNORE INTO users (username, password, role) VALUES ('admin','admin123','admin')")
            self.conn.commit()
            # ✅ FIX: Migrate booking_id columns from VARCHAR to INT if needed
            self._migrate_booking_id_columns(c)
        finally:
            c.close()

    def _migrate_booking_id_columns(self, c):
        """Migrate booking_id columns from VARCHAR(20) to INT on existing databases."""
        tables = ['transactions', 'services', 'payments', 'booking_logs']
        for table in tables:
            try:
                c.execute(f"SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA='hotella' AND TABLE_NAME='{table}' AND COLUMN_NAME='booking_id'")
                row = c.fetchone()
                if row and row[0].lower() in ('varchar', 'char', 'text'):
                    print(f"[Migration] Converting {table}.booking_id VARCHAR -> INT...")
                    # Convert stored 'B00001' strings to integers first, then alter column
                    c.execute(f"UPDATE {table} SET booking_id = CAST(REPLACE(booking_id, 'B', '') AS UNSIGNED) WHERE booking_id REGEXP '^B[0-9]+$'")
                    c.execute(f"ALTER TABLE {table} MODIFY COLUMN booking_id INT")
                    self.conn.commit()
                    print(f"[Migration] {table}.booking_id migrated successfully.")
            except Exception as e:
                print(f"[Migration] Warning for {table}: {e}")
                try: self.conn.rollback()
                except: pass

    # --- AUTH (UPDATED) ---
    def auth(self, u, p):
        c = self.get_cursor()
        if not c: return None
        try:
            # 🟢 UPDATED: Checks if the linked employee is 'Inactive'
            # If user has no employee_id (like super admin), it allows login (LEFT JOIN handles nulls, check status IS NULL or != Inactive)
            sql = """
                SELECT u.username, u.role, e.name 
                FROM users u 
                LEFT JOIN employees e ON u.employee_id = e.id 
                WHERE u.username=%s AND u.password=%s 
                AND (e.status IS NULL OR e.status != 'Inactive')
            """
            c.execute(sql, (u, p))
            return c.fetchone() # Returns (username, role, employee_name)
        finally:
            c.close()

    # --- ANALYTICS ---
    def get_analytics(self):
        c = self.get_cursor()
        if not c: return {0: 0, 1: 0, 2: 0}, "N/A", "N/A", [], 0, 0, 0
        try:
            c.execute("SELECT SUM(grand_total), SUM(room_total), SUM(service_total) FROM payments")
            rev = c.fetchone()
            revenue = {'total': rev[0] or 0, 'room': rev[1] or 0, 'service': rev[2] or 0}

            c.execute("SELECT room_type, COUNT(*) as c FROM bookings GROUP BY room_type ORDER BY c DESC LIMIT 1")
            pop_room = c.fetchone()
            top_room = f"{pop_room[0]} ({pop_room[1]})" if pop_room else "N/A"

            c.execute("SELECT service_name, COUNT(*) as c FROM services GROUP BY service_name ORDER BY c DESC LIMIT 1")
            top_svc = c.fetchone()
            best_service = f"{top_svc[0]} ({top_svc[1]})" if top_svc else "N/A"

            c.execute("SELECT customer_name, SUM(grand_total) as s FROM payments GROUP BY customer_name ORDER BY s DESC LIMIT 5")
            vips = c.fetchall()

            c.execute("SELECT COUNT(*) FROM rooms")
            total_rooms = c.fetchone()[0] or 1
            c.execute("SELECT COUNT(*) FROM rooms WHERE status='Occupied'")
            occupied = c.fetchone()[0] or 0
            c.execute("SELECT COUNT(*) FROM rooms WHERE status='Maintenance'")
            maintenance = c.fetchone()[0] or 0

            occupancy_rate = int((occupied / total_rooms) * 100) if total_rooms > 0 else 0

            return revenue, top_room, best_service, vips, occupancy_rate, maintenance, total_rooms
        except:
            return {0: 0, 1: 0, 2: 0}, "N/A", "N/A", [], 0, 0, 0
        finally:
            c.close()

    # --- BOOKINGS ---
    def bookings(self):
        c = self.get_cursor(); c.execute("SELECT * FROM bookings"); return c.fetchall()
    def add_booking(self, *args):
        c = self.get_cursor(); sql = "INSERT INTO bookings (name,email,phone,address,room_type,date,days,price) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"; c.execute(sql, args); self.conn.commit(); c.close()
    def update_booking(self, old_email, *args):
        c = self.get_cursor(); sql = "UPDATE bookings SET name=%s, email=%s, phone=%s, address=%s, room_type=%s WHERE email=%s"; params = list(args) + [old_email]; c.execute(sql, params); self.conn.commit(); c.close()
    def delete_booking(self, email):
        c = self.get_cursor(); c.execute("DELETE FROM bookings WHERE email=%s", (email,)); self.conn.commit(); c.close()

    # --- ROOMS ---
    def rooms(self):
        c = self.get_cursor(); c.execute("SELECT room_number,description,status FROM rooms"); return c.fetchall()
    def add_room(self, *args):
        c = self.get_cursor(); c.execute("INSERT INTO rooms (room_number,description,status) VALUES (%s,%s,%s)", args); self.conn.commit(); c.close()
    def update_room(self, old, *args):
        c = self.get_cursor(); sql = "UPDATE rooms SET room_number=%s,description=%s,status=%s WHERE room_number=%s"; params = list(args) + [old]; c.execute(sql, params); self.conn.commit(); c.close()
    def delete_room(self, num):
        c = self.get_cursor(); c.execute("DELETE FROM rooms WHERE room_number=%s", (num,)); self.conn.commit(); c.close()

    # --- HELPERS ---
    def get_booking_by_id(self, bid_str):
        c = self.get_cursor()
        try:
            bid = int(bid_str.replace("B", ""))
            c.execute("SELECT * FROM bookings WHERE id=%s", (bid,))
            return c.fetchone()
        except: return None
        finally: c.close()

    def get_active_booking_by_room(self, room_num):
        c = self.get_cursor()
        try:
            c.execute("SELECT booking_id FROM transactions WHERE room_number=%s ORDER BY id DESC LIMIT 1", (room_num,))
            res = c.fetchone()
            return f"B{res[0]:05d}" if res and res[0] else "-"
        finally: c.close()

    def get_services_by_booking_id(self, bid):
        c = self.get_cursor(); c.execute("SELECT service_name, price FROM services WHERE booking_id=%s", (bid,)); return c.fetchall()
    def add_service(self, *args):
        c = self.get_cursor(); date = datetime.now().strftime("%Y-%m-%d %H:%M"); params = list(args) + [date]; c.execute("INSERT INTO services (booking_id, room_number, service_name, price, date) VALUES (%s,%s,%s,%s,%s)", params); self.conn.commit(); c.close()
    def delete_service(self, sid):
        c = self.get_cursor(); c.execute("DELETE FROM services WHERE id=%s", (sid,)); self.conn.commit(); c.close()
    def get_payments(self):
        c = self.get_cursor(); c.execute("SELECT * FROM payments"); return c.fetchall()
    def add_payment(self, *args):
        c = self.get_cursor(); date = datetime.now().strftime("%Y-%m-%d %H:%M"); params = list(args) + [date]; c.execute("INSERT INTO payments (booking_id, customer_name, room_total, service_total, grand_total, method, date_paid) VALUES (%s,%s,%s,%s,%s,%s,%s)", params); self.conn.commit(); c.close()
    def get_housekeeping_logs(self):
        c = self.get_cursor(); c.execute("SELECT * FROM housekeeping_logs ORDER BY id DESC"); return c.fetchall()
    def get_unassigned_bookings(self):
        c = self.get_cursor()
        c.execute("SELECT booking_id FROM transactions")
        # ✅ FIX: booking_id is INT now
        assigned = {row[0] for row in c.fetchall()}
        c.execute("SELECT id, room_type FROM bookings")
        all_b = c.fetchall()
        return [(f"B{b[0]:05d}", b[1]) for b in all_b if b[0] not in assigned]
    def assign_room(self, bid, room):
        c = self.get_cursor()
        # ✅ FIX: Store booking_id as integer
        bid_int = int(str(bid).replace("B", ""))
        c.execute("UPDATE rooms SET status='Occupied' WHERE room_number=%s", (room,))
        date = datetime.now().strftime("%Y-%m-%d %H:%M")
        c.execute("INSERT INTO transactions (booking_id, room_number, date_confirmed) VALUES (%s,%s,%s)", (bid_int, room, date))
        self.conn.commit(); c.close()
    def get_room_booking_history(self, room):
        c = self.get_cursor(); history = []
        try:
            c.execute("SELECT booking_id FROM transactions WHERE room_number=%s", (room,))
            # ✅ FIX: booking_id is INT - no need to strip 'B'
            bids = [row[0] for row in c.fetchall()]
            for bid_int in bids:
                c.execute("SELECT * FROM bookings WHERE id=%s", (bid_int,))
                res = c.fetchone()
                if res: history.append(res)
            return history
        finally: c.close()
    def get_transactions(self):
        c = self.get_cursor(); c.execute("SELECT booking_id, room_number FROM transactions"); return c.fetchall()
    def get_total_paid(self, bid):
        c = self.get_cursor(); c.execute("SELECT SUM(grand_total) FROM payments WHERE booking_id=%s", (bid,)); res = c.fetchone(); return res[0] if res and res[0] else 0
    def add_housekeeping_log(self, room, action):
        c = self.get_cursor(); date = datetime.now().strftime("%Y-%m-%d %H:%M"); c.execute("INSERT INTO housekeeping_logs (room_number, action, date_time) VALUES (%s,%s,%s)", (room, action, date)); self.conn.commit(); c.close()