import sys
import calendar as _calendar
from datetime import datetime

try:
    import mysql.connector
except ImportError:
    print("CRITICAL ERROR: 'mysql-connector-python' is not installed.")
    sys.exit(1)


class Database:
    """
    The ONLY class allowed to open cursors and run SQL.
    Every c.execute / c.fetchone / c.fetchall / c.close lives here.
    All model and controller files call methods on this class instead.
    """

    def __init__(self):
        self.conn = None
        try:
            srv = mysql.connector.connect(host="localhost", user="root", password="")
            cur = srv.cursor()
            cur.execute("CREATE DATABASE IF NOT EXISTS hotella")
            srv.commit()
            cur.close()
            srv.close()

            self.conn = mysql.connector.connect(
                host="localhost", user="root", password="", database="hotella"
            )
            self.create_tables()
            print("Successfully connected to MySQL database: 'hotella'")
        except mysql.connector.Error as err:
            print(f"\n[DB ERROR] Could not connect: {err}")

    # ── Internal cursor factory ───────────────────────────────────────────────

    def _cursor(self):
        if self.conn and self.conn.is_connected():
            return self.conn.cursor(buffered=True)
        return None

    # Public alias kept so nothing outside breaks
    def get_cursor(self):
        return self._cursor()

    # ═══════════════════════════════════════════════════════════════════════════
    # SCHEMA
    # ═══════════════════════════════════════════════════════════════════════════

    def create_tables(self):
        c = self._cursor()
        if not c:
            return
        try:
            ddl = [
                "CREATE TABLE IF NOT EXISTS users (username VARCHAR(50) PRIMARY KEY, password VARCHAR(255), role VARCHAR(20), employee_id INT)",
                "CREATE TABLE IF NOT EXISTS bookings (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(100), email VARCHAR(100), phone VARCHAR(20), address VARCHAR(255), room_type VARCHAR(50), date VARCHAR(20), days INT, price INT, status VARCHAR(50), guests_count INT DEFAULT 1, created_by VARCHAR(100) DEFAULT '---')",
                "CREATE TABLE IF NOT EXISTS rooms (id INT AUTO_INCREMENT PRIMARY KEY, room_number VARCHAR(10) UNIQUE, description VARCHAR(100), status VARCHAR(20) DEFAULT 'Vacant', assigned_employee_id INT)",
                "CREATE TABLE IF NOT EXISTS services (id INT AUTO_INCREMENT PRIMARY KEY, booking_id INT, room_number VARCHAR(10), service_name VARCHAR(100), price INT, date VARCHAR(20), employee_id INT, quantity INT DEFAULT 1)",
                "CREATE TABLE IF NOT EXISTS transactions (id INT AUTO_INCREMENT PRIMARY KEY, booking_id INT, room_number VARCHAR(10), date_confirmed VARCHAR(20))",
                "CREATE TABLE IF NOT EXISTS payments (id INT AUTO_INCREMENT PRIMARY KEY, booking_id INT, customer_name VARCHAR(100), room_total INT, service_total INT, grand_total INT, method VARCHAR(50), date_paid VARCHAR(20), amount_paid INT DEFAULT 0, card_number VARCHAR(50), processed_by VARCHAR(100) DEFAULT '---', remarks VARCHAR(50) DEFAULT 'Payment')",
                "CREATE TABLE IF NOT EXISTS housekeeping_logs (id INT AUTO_INCREMENT PRIMARY KEY, room_number VARCHAR(10), action VARCHAR(100), date_time VARCHAR(20))",
                "CREATE TABLE IF NOT EXISTS booking_logs (id INT AUTO_INCREMENT PRIMARY KEY, booking_id INT, guest_name VARCHAR(100), action_type VARCHAR(50), timestamp VARCHAR(30), performed_by VARCHAR(100) DEFAULT '---')",
                "CREATE TABLE IF NOT EXISTS employees (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(100), role VARCHAR(50), contact VARCHAR(50), status VARCHAR(20) DEFAULT 'Available')",
            ]
            for sql in ddl:
                c.execute(sql)
            c.execute("INSERT IGNORE INTO users (username, password, role) VALUES ('admin','admin123','admin')")
            self.conn.commit()
            self._migrate_booking_id_columns(c)
        finally:
            c.close()

    def _migrate_booking_id_columns(self, c):
        for table in ['transactions', 'services', 'payments', 'booking_logs']:
            try:
                c.execute(
                    f"SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
                    f"WHERE TABLE_SCHEMA='hotella' AND TABLE_NAME='{table}' "
                    f"AND COLUMN_NAME='booking_id'"
                )
                row = c.fetchone()
                if row and row[0].lower() in ('varchar', 'char', 'text'):
                    print(f"[Migration] Converting {table}.booking_id VARCHAR -> INT...")
                    c.execute(
                        f"UPDATE {table} SET booking_id = "
                        f"CAST(REPLACE(booking_id,'B','') AS UNSIGNED) "
                        f"WHERE booking_id REGEXP '^B[0-9]+$'"
                    )
                    c.execute(f"ALTER TABLE {table} MODIFY COLUMN booking_id INT")
                    self.conn.commit()
                    print(f"[Migration] {table}.booking_id migrated.")
            except Exception as e:
                print(f"[Migration] Warning for {table}: {e}")
                try:
                    self.conn.rollback()
                except Exception:
                    pass

    # ═══════════════════════════════════════════════════════════════════════════
    # AUTH
    # ═══════════════════════════════════════════════════════════════════════════

    def auth(self, username, password):
        """Return (username, role, employee_name) or None."""
        c = self._cursor()
        if not c:
            return None
        try:
            c.execute(
                "SELECT u.username, u.role, e.name "
                "FROM users u "
                "LEFT JOIN employees e ON u.employee_id = e.id "
                "WHERE u.username=%s AND u.password=%s "
                "AND (e.status IS NULL OR e.status != 'Inactive')",
                (username, password)
            )
            return c.fetchone()
        finally:
            c.close()

    # ═══════════════════════════════════════════════════════════════════════════
    # EMPLOYEES
    # ═══════════════════════════════════════════════════════════════════════════

    def fetch_all_employees(self):
        c = self._cursor()
        try:
            c.execute(
                "SELECT e.id, e.name, e.role, e.contact, e.status, u.username "
                "FROM employees e LEFT JOIN users u ON e.id = u.employee_id "
                "WHERE e.role != 'Manager' ORDER BY e.id DESC"
            )
            return c.fetchall()
        finally:
            c.close()

    def fetch_employee_count(self):
        c = self._cursor()
        try:
            c.execute("SELECT COUNT(*) FROM employees WHERE status != 'Inactive'")
            res = c.fetchone()[0]
            return res if res else 0
        finally:
            c.close()

    def fetch_employee_metadata(self, name):
        """Return (id, role) for an employee by name."""
        c = self._cursor()
        try:
            c.execute("SELECT id, role FROM employees WHERE name=%s", (name,))
            return c.fetchone()
        finally:
            c.close()

    def fetch_service_staff(self):
        """Return names of active Room Service / Waiter / Kitchen employees."""
        c = self._cursor()
        try:
            c.execute(
                "SELECT name FROM employees "
                "WHERE role IN ('Room Service','Waiter','Kitchen') AND status='Active'"
            )
            return [row[0] for row in c.fetchall()]
        finally:
            c.close()

    def fetch_available_cleaners(self):
        """Return (id, name) of active Cleaner employees."""
        c = self._cursor()
        try:
            c.execute("SELECT id, name FROM employees WHERE role='Cleaner' AND status='Active'")
            return c.fetchall()
        finally:
            c.close()

    def insert_employee(self, name, role, contact):
        """Insert employee; return new id or None."""
        c = self._cursor()
        try:
            c.execute(
                "INSERT INTO employees (name, role, contact, status) VALUES (%s,%s,%s,'Active')",
                (name, role, contact)
            )
            c.execute("SELECT LAST_INSERT_ID()")
            emp_id = c.fetchone()[0]
            self.conn.commit()
            return emp_id
        except Exception:
            self.conn.rollback()
            return None
        finally:
            c.close()

    def insert_user_account(self, username, password, role, emp_id):
        """Create login account for an employee; return True/False."""
        c = self._cursor()
        try:
            c.execute(
                "INSERT INTO users (username, password, role, employee_id) VALUES (%s,%s,%s,%s)",
                (username, password, role, emp_id)
            )
            self.conn.commit()
            return True
        except Exception:
            self.conn.rollback()
            return False
        finally:
            c.close()

    def update_employee_status(self, emp_id, status):
        """Set employee status field; return True/False."""
        c = self._cursor()
        try:
            c.execute("UPDATE employees SET status=%s WHERE id=%s", (status, emp_id))
            self.conn.commit()
            return True
        except Exception:
            return False
        finally:
            c.close()

    def delete_employee(self, emp_id):
        """Delete employee and linked user account; return True/False."""
        c = self._cursor()
        try:
            c.execute("DELETE FROM users WHERE employee_id=%s", (emp_id,))
            c.execute("DELETE FROM employees WHERE id=%s", (emp_id,))
            self.conn.commit()
            return True
        except Exception:
            self.conn.rollback()
            return False
        finally:
            c.close()

    # ═══════════════════════════════════════════════════════════════════════════
    # ROOMS
    # ═══════════════════════════════════════════════════════════════════════════

    def fetch_all_rooms(self):
        """Return (room_number, description, status) for all rooms."""
        c = self._cursor()
        try:
            c.execute("SELECT room_number, description, status FROM rooms ORDER BY room_number")
            return c.fetchall()
        finally:
            c.close()

    def fetch_all_rooms_full(self):
        """Return (room_number, status, description, assigned_employee_id)."""
        c = self._cursor()
        try:
            c.execute("SELECT room_number, status, description, assigned_employee_id FROM rooms")
            return c.fetchall()
        finally:
            c.close()

    def fetch_dirty_rooms(self):
        c = self._cursor()
        try:
            c.execute(
                "SELECT room_number, description, status "
                "FROM rooms WHERE status IN ('Dirty','Housekeeping')"
            )
            return c.fetchall()
        finally:
            c.close()

    def fetch_available_rooms(self, d_in, d_out):
        c = self._cursor()
        try:
            c.execute(
                "SELECT room_number, description, status FROM rooms "
                "WHERE room_number NOT IN ("
                "  SELECT t.room_number FROM transactions t "
                "  JOIN bookings b ON t.booking_id = b.id "
                "  WHERE b.status NOT IN ('Cancelled','Checked Out') "
                "  AND NOT ("
                "    DATE_ADD(STR_TO_DATE(b.date,'%%Y-%%m-%%d'), INTERVAL b.days DAY) <= %s "
                "    OR STR_TO_DATE(b.date,'%%Y-%%m-%%d') >= %s"
                "  )"
                ") AND status NOT IN ('Maintenance','Occupied','Cleaning','Dirty') "
                "ORDER BY room_number",
                (d_in, d_out)
            )
            return c.fetchall()
        except Exception as e:
            print(f"[fetch_available_rooms] {e}")
            return []
        finally:
            c.close()

    def fetch_room_counts(self):
        """Return (active_bookings, vacant, occupied, dirty)."""
        c = self._cursor()
        try:
            c.execute(
                "SELECT COUNT(*) FROM bookings "
                "WHERE status IN ('Confirmed','Arrived','Checked In')"
            )
            total = c.fetchone()[0]
            c.execute("SELECT status, COUNT(*) FROM rooms GROUP BY status")
            stats = dict(c.fetchall())
            return total, stats.get('Vacant', 0), stats.get('Occupied', 0), stats.get('Dirty', 0)
        finally:
            c.close()

    def fetch_room_has_active_bookings(self, room_number):
        c = self._cursor()
        try:
            c.execute(
                "SELECT COUNT(*) FROM transactions t "
                "JOIN bookings b ON t.booking_id = b.id "
                "WHERE t.room_number=%s AND b.status IN ('Confirmed','Arrived','Checked In')",
                (room_number,)
            )
            return c.fetchone()[0] > 0
        finally:
            c.close()

    def fetch_room_history(self, room_number):
        c = self._cursor()
        try:
            c.execute(
                "SELECT b.id, b.name, b.date, b.days, b.status, b.created_by "
                "FROM transactions t JOIN bookings b ON t.booking_id = b.id "
                "WHERE t.room_number=%s ORDER BY b.date DESC",
                (room_number,)
            )
            return c.fetchall()
        finally:
            c.close()

    def fetch_all_room_history(self):
        c = self._cursor()
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
            c.close()

    def update_room_status(self, room_number, status):
        c = self._cursor()
        try:
            c.execute("UPDATE rooms SET status=%s WHERE room_number=%s", (status, room_number))
            self.conn.commit()
            return True
        finally:
            c.close()

    def update_room_type(self, room_number, room_type):
        c = self._cursor()
        try:
            c.execute("UPDATE rooms SET description=%s WHERE room_number=%s", (room_type, room_number))
            self.conn.commit()
            return True
        finally:
            c.close()

    def add_room(self, room_number, description, status):
        c = self._cursor()
        try:
            c.execute(
                "INSERT INTO rooms (room_number, description, status) VALUES (%s,%s,%s)",
                (room_number, description, status)
            )
            self.conn.commit()
        finally:
            c.close()

    def update_room(self, old_room_number, room_number, description, status):
        c = self._cursor()
        try:
            c.execute(
                "UPDATE rooms SET room_number=%s, description=%s, status=%s "
                "WHERE room_number=%s",
                (room_number, description, status, old_room_number)
            )
            self.conn.commit()
        finally:
            c.close()

    def delete_room(self, room_number):
        c = self._cursor()
        try:
            c.execute("DELETE FROM rooms WHERE room_number=%s", (room_number,))
            self.conn.commit()
        finally:
            c.close()

    def get_active_booking_by_room(self, room_num):
        c = self._cursor()
        try:
            c.execute(
                "SELECT booking_id FROM transactions "
                "WHERE room_number=%s ORDER BY id DESC LIMIT 1",
                (room_num,)
            )
            res = c.fetchone()
            return f"B{res[0]:05d}" if res and res[0] else "-"
        finally:
            c.close()

    def get_room_booking_history(self, room):
        c = self._cursor()
        history = []
        try:
            c.execute("SELECT booking_id FROM transactions WHERE room_number=%s", (room,))
            for (bid_int,) in c.fetchall():
                c.execute("SELECT * FROM bookings WHERE id=%s", (bid_int,))
                row = c.fetchone()
                if row:
                    history.append(row)
            return history
        finally:
            c.close()

    # ═══════════════════════════════════════════════════════════════════════════
    # BOOKINGS
    # ═══════════════════════════════════════════════════════════════════════════

    def fetch_all_bookings_admin(self):
        """Return booking rows for admin management table."""
        c = self._cursor()
        try:
            c.execute(
                "SELECT id, name, email, phone, address, room_type, date, days, price "
                "FROM bookings ORDER BY id DESC"
            )
            return c.fetchall()
        finally:
            c.close()

    def fetch_all_bookings_staff(self):
        """Return enriched booking rows (with room number) for staff view."""
        c = self._cursor()
        try:
            c.execute(
                "SELECT b.id, b.name, b.room_type, t.room_number, "
                "b.price, b.status, b.date, b.days "
                "FROM bookings b "
                "LEFT JOIN transactions t ON t.booking_id = b.id "
                "ORDER BY b.date DESC"
            )
            return c.fetchall()
        finally:
            c.close()

    def fetch_todays_bookings(self, today_str):
        c = self._cursor()
        try:
            c.execute(
                "SELECT b.id, b.name, b.room_type, t.room_number, b.price, b.status "
                "FROM bookings b "
                "LEFT JOIN transactions t ON t.booking_id = b.id "
                "WHERE b.date=%s AND b.status IN ('Confirmed','Checked In','Arrived')",
                (today_str,)
            )
            return c.fetchall()
        except Exception as e:
            print(f"[fetch_todays_bookings] {e}")
            return []
        finally:
            c.close()

    def fetch_checkout_candidates(self):
        """Return (room_number, 'B00001', price, name) for checkable bookings."""
        c = self._cursor()
        try:
            c.execute(
                "SELECT IFNULL(t.room_number,'N/A'), b.id, b.price, b.name "
                "FROM bookings b "
                "LEFT JOIN transactions t ON t.booking_id = b.id "
                "WHERE b.status IN ('Checked In','Confirmed','Arrived') "
                "ORDER BY b.id DESC"
            )
            return [(row[0], f"B{row[1]:05d}", row[2], row[3]) for row in c.fetchall()]
        except Exception as e:
            print(f"[fetch_checkout_candidates] {e}")
            return []
        finally:
            c.close()

    def fetch_booking_details_for_bill(self, bid_int):
        """Return (name, price, room_type, date, days) for one booking."""
        c = self._cursor()
        try:
            c.execute(
                "SELECT name, price, room_type, date, days FROM bookings WHERE id=%s",
                (bid_int,)
            )
            return c.fetchone()
        finally:
            c.close()

    def update_booking_status(self, bid_int, new_status):
        """Update booking status; auto-dirty room on checkout/cancel."""
        c = self._cursor()
        try:
            c.execute("UPDATE bookings SET status=%s WHERE id=%s", (new_status, bid_int))
            if new_status in ('Checked Out', 'Cancelled'):
                c.execute(
                    "SELECT room_number FROM transactions WHERE booking_id=%s", (bid_int,)
                )
                res = c.fetchone()
                if res and res[0]:
                    c.execute(
                        "UPDATE rooms SET status='Dirty' WHERE room_number=%s", (res[0],)
                    )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"[update_booking_status] {e}")
            self.conn.rollback()
            return False
        finally:
            c.close()

    def insert_booking_full(self, name, email, phone, address, room_type,
                            date, days, total_price, guests, staff_name):
        """Insert a full booking record; return new booking int id or False."""
        c = self._cursor()
        try:
            c.execute(
                "INSERT INTO bookings "
                "(name,email,phone,address,room_type,date,days,price,status,guests_count,created_by) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'Confirmed',%s,%s)",
                (name, email, phone, address, room_type, date, days, total_price, guests, staff_name)
            )
            c.execute("SELECT LAST_INSERT_ID()")
            raw_id = c.fetchone()[0]
            self.conn.commit()
            return raw_id
        except Exception as e:
            print(f"[insert_booking_full] {e}")
            self.conn.rollback()
            return False
        finally:
            c.close()

    def add_booking(self, name, email, phone, address, room_type, date, days, price):
        c = self._cursor()
        try:
            c.execute(
                "INSERT INTO bookings (name,email,phone,address,room_type,date,days,price) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (name, email, phone, address, room_type, date, days, price)
            )
            self.conn.commit()
        finally:
            c.close()

    def update_booking(self, old_email, name, email, phone, address, room_type):
        c = self._cursor()
        try:
            c.execute(
                "UPDATE bookings SET name=%s,email=%s,phone=%s,address=%s,room_type=%s "
                "WHERE email=%s",
                (name, email, phone, address, room_type, old_email)
            )
            self.conn.commit()
        finally:
            c.close()

    def delete_booking(self, email):
        c = self._cursor()
        try:
            c.execute("DELETE FROM bookings WHERE email=%s", (email,))
            self.conn.commit()
        finally:
            c.close()

    def get_booking_by_id(self, bid_str):
        c = self._cursor()
        try:
            bid = int(str(bid_str).replace("B", ""))
            c.execute("SELECT * FROM bookings WHERE id=%s", (bid,))
            return c.fetchone()
        except Exception:
            return None
        finally:
            c.close()

    def get_unassigned_bookings(self):
        c = self._cursor()
        try:
            c.execute("SELECT booking_id FROM transactions")
            assigned = {row[0] for row in c.fetchall()}
            c.execute("SELECT id, room_type FROM bookings")
            return [(f"B{b[0]:05d}", b[1]) for b in c.fetchall() if b[0] not in assigned]
        finally:
            c.close()

    def bookings(self):
        c = self._cursor()
        try:
            c.execute("SELECT * FROM bookings")
            return c.fetchall()
        finally:
            c.close()

    # ═══════════════════════════════════════════════════════════════════════════
    # TRANSACTIONS
    # ═══════════════════════════════════════════════════════════════════════════

    def insert_transaction(self, bid_int, room_number, date_confirmed):
        c = self._cursor()
        try:
            c.execute(
                "INSERT INTO transactions (booking_id,room_number,date_confirmed) VALUES (%s,%s,%s)",
                (bid_int, room_number, date_confirmed)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"[insert_transaction] {e}")
            self.conn.rollback()
            return False
        finally:
            c.close()

    def fetch_room_status_by_booking(self, bid_int):
        """Return (status, room_number) for the room linked to a booking."""
        c = self._cursor()
        try:
            c.execute(
                "SELECT r.status, r.room_number "
                "FROM transactions t JOIN rooms r ON t.room_number = r.room_number "
                "WHERE t.booking_id=%s",
                (bid_int,)
            )
            return c.fetchone()
        except Exception as e:
            print(f"[fetch_room_status_by_booking] {e}")
            return None
        finally:
            c.close()

    def fetch_active_guest_by_room(self, room_num):
        """Return (booking_id_int, guest_name) for the active guest in a room."""
        c = self._cursor()
        try:
            c.execute(
                "SELECT b.id, b.name "
                "FROM transactions t JOIN bookings b ON t.booking_id = b.id "
                "WHERE t.room_number=%s "
                "AND b.status IN ('Confirmed','Arrived','Checked In') "
                "ORDER BY b.id DESC LIMIT 1",
                (room_num,)
            )
            return c.fetchone()
        except Exception as e:
            print(f"[fetch_active_guest_by_room] {e}")
            return None
        finally:
            c.close()

    def get_transactions(self):
        c = self._cursor()
        try:
            c.execute("SELECT booking_id, room_number FROM transactions")
            return c.fetchall()
        finally:
            c.close()

    def assign_room(self, bid, room):
        c = self._cursor()
        try:
            bid_int = int(str(bid).replace("B", ""))
            c.execute("UPDATE rooms SET status='Occupied' WHERE room_number=%s", (room,))
            c.execute(
                "INSERT INTO transactions (booking_id,room_number,date_confirmed) VALUES (%s,%s,%s)",
                (bid_int, room, datetime.now().strftime("%Y-%m-%d %H:%M"))
            )
            self.conn.commit()
        finally:
            c.close()

    # ═══════════════════════════════════════════════════════════════════════════
    # SERVICES
    # ═══════════════════════════════════════════════════════════════════════════

    def fetch_all_services(self):
        c = self._cursor()
        try:
            c.execute("SELECT * FROM services ORDER BY date DESC")
            return c.fetchall()
        finally:
            c.close()

    def fetch_services_by_booking(self, bid_int):
        """Return (service_name, price, quantity) rows for one booking."""
        c = self._cursor()
        try:
            c.execute(
                "SELECT service_name, price, quantity FROM services WHERE booking_id=%s",
                (bid_int,)
            )
            return c.fetchall()
        finally:
            c.close()

    def insert_service(self, bid_int, room_number, service_name, total_cost, date, emp_id, quantity):
        c = self._cursor()
        try:
            c.execute(
                "INSERT INTO services "
                "(booking_id,room_number,service_name,price,date,employee_id,quantity) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (bid_int, room_number, service_name, total_cost, date, emp_id, quantity)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"[insert_service] {e}")
            self.conn.rollback()
            return False
        finally:
            c.close()

    def delete_service(self, service_id):
        c = self._cursor()
        try:
            c.execute("DELETE FROM services WHERE id=%s", (service_id,))
            self.conn.commit()
        finally:
            c.close()

    def get_services_by_booking_id(self, bid_int):
        c = self._cursor()
        try:
            c.execute("SELECT service_name, price FROM services WHERE booking_id=%s", (bid_int,))
            return c.fetchall()
        finally:
            c.close()

    def add_service(self, booking_id, room_number, service_name, price):
        c = self._cursor()
        try:
            date = datetime.now().strftime("%Y-%m-%d %H:%M")
            c.execute(
                "INSERT INTO services (booking_id,room_number,service_name,price,date) "
                "VALUES (%s,%s,%s,%s,%s)",
                (booking_id, room_number, service_name, price, date)
            )
            self.conn.commit()
        finally:
            c.close()

    # ═══════════════════════════════════════════════════════════════════════════
    # PAYMENTS
    # ═══════════════════════════════════════════════════════════════════════════

    def fetch_all_payments(self):
        c = self._cursor()
        try:
            c.execute("SELECT * FROM payments ORDER BY date_paid DESC")
            return c.fetchall()
        finally:
            c.close()

    def fetch_total_revenue_year(self, year):
        c = self._cursor()
        try:
            c.execute(
                "SELECT SUM(amount_paid) FROM payments WHERE date_paid LIKE %s",
                (f"{year}%",)
            )
            res = c.fetchone()[0]
            return res if res else 0
        finally:
            c.close()

    def fetch_payment_dates(self):
        c = self._cursor()
        try:
            c.execute("SELECT date_paid FROM payments")
            return [row[0] for row in c.fetchall()]
        finally:
            c.close()

    def fetch_total_amount_paid(self, bid_int):
        c = self._cursor()
        try:
            c.execute(
                "SELECT COALESCE(SUM(amount_paid),0) FROM payments WHERE booking_id=%s",
                (bid_int,)
            )
            return c.fetchone()[0] or 0
        finally:
            c.close()

    def insert_payment(self, bid_int, customer_name, room_total, service_total,
                       grand_total, method, date_paid, amount_paid,
                       card_number, processed_by, remarks):
        """Insert a payment record; return new payment id or None."""
        c = self._cursor()
        if not c:
            return None
        try:
            c.execute(
                "INSERT INTO payments "
                "(booking_id,customer_name,room_total,service_total,grand_total,"
                "method,date_paid,amount_paid,card_number,processed_by,remarks) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (bid_int, customer_name, room_total, service_total, grand_total,
                 method, date_paid, amount_paid, card_number, processed_by, remarks)
            )
            c.execute("SELECT LAST_INSERT_ID()")
            payment_id = c.fetchone()[0]
            self.conn.commit()
            return payment_id
        except Exception as e:
            print(f"[insert_payment] {e}")
            self.conn.rollback()
            return None
        finally:
            c.close()

    def get_payments(self):
        c = self._cursor()
        try:
            c.execute("SELECT * FROM payments")
            return c.fetchall()
        finally:
            c.close()

    def add_payment(self, booking_id, customer_name, room_total, service_total, grand_total, method):
        c = self._cursor()
        try:
            date = datetime.now().strftime("%Y-%m-%d %H:%M")
            c.execute(
                "INSERT INTO payments "
                "(booking_id,customer_name,room_total,service_total,grand_total,method,date_paid) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (booking_id, customer_name, room_total, service_total, grand_total, method, date)
            )
            self.conn.commit()
        finally:
            c.close()

    def get_total_paid(self, bid_int):
        c = self._cursor()
        try:
            c.execute("SELECT SUM(grand_total) FROM payments WHERE booking_id=%s", (bid_int,))
            res = c.fetchone()
            return res[0] if res and res[0] else 0
        finally:
            c.close()

    # ═══════════════════════════════════════════════════════════════════════════
    # ANALYTICS
    # ═══════════════════════════════════════════════════════════════════════════

    def fetch_analytics_raw(self):
        """Return (payments, bookings, services) full rows for in-memory filtering."""
        c = self._cursor()
        try:
            c.execute("SELECT * FROM payments")
            payments = c.fetchall()
            c.execute("SELECT room_type, date FROM bookings WHERE status != 'Cancelled'")
            bookings = c.fetchall()
            c.execute("SELECT service_name, date, price, quantity FROM services")
            services = c.fetchall()
            return payments, bookings, services
        finally:
            c.close()

    def fetch_daily_revenue(self, year, month):
        """Return list of per-day revenue dicts for one month."""
        last_day = _calendar.monthrange(int(year), int(month))[1]
        start = f"{year}-{month:02d}-01"
        end = f"{year}-{month:02d}-{last_day}"
        c = self._cursor()
        try:
            c.execute(
                "SELECT DATE(date_paid), SUM(room_total), SUM(service_total), "
                "COUNT(DISTINCT booking_id) "
                "FROM payments WHERE DATE(date_paid) BETWEEN %s AND %s "
                "GROUP BY DATE(date_paid) ORDER BY DATE(date_paid)",
                (start, end)
            )
            results = c.fetchall()
            daily = {
                f"{year}-{month:02d}-{d:02d}": {
                    'room_rev': 0, 'service_rev': 0, 'total_rev': 0, 'bookings': 0, 'day': d
                }
                for d in range(1, last_day + 1)
            }
            for row in results:
                key = str(row[0])
                if key in daily:
                    daily[key].update({
                        'room_rev':    float(row[1] or 0),
                        'service_rev': float(row[2] or 0),
                        'total_rev':   float(row[1] or 0) + float(row[2] or 0),
                        'bookings':    int(row[3] or 0),
                    })
            return list(daily.values())
        finally:
            c.close()

    def fetch_monthly_revenue(self, year):
        """Return list of per-month revenue dicts for one year."""
        c = self._cursor()
        try:
            monthly = []
            for month in range(1, 13):
                start = f"{year}-{month:02d}-01"
                last_day = _calendar.monthrange(int(year), month)[1]
                end = f"{year}-{month:02d}-{last_day}"
                c.execute(
                    "SELECT COALESCE(SUM(room_total),0), "
                    "COALESCE(SUM(service_total),0), "
                    "COUNT(DISTINCT booking_id) "
                    "FROM payments WHERE DATE(date_paid) BETWEEN %s AND %s",
                    (start, end)
                )
                row = c.fetchone()
                monthly.append({
                    'month':       month,
                    'month_name':  _calendar.month_abbr[month],
                    'room_rev':    float(row[0] or 0),
                    'service_rev': float(row[1] or 0),
                    'total_rev':   float(row[0] or 0) + float(row[1] or 0),
                    'bookings':    int(row[2] or 0),
                })
            return monthly
        finally:
            c.close()

    def fetch_report_data_comprehensive(self):
        """Return all table data needed for PDF report generation."""
        c = self._cursor()
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
                "SELECT room_number, action, date_time "
                "FROM housekeeping_logs ORDER BY date_time DESC"
            )
            data['housekeeping'] = c.fetchall()

            c.execute(
                "SELECT guest_name, action_type, timestamp, booking_id, performed_by "
                "FROM booking_logs ORDER BY timestamp DESC"
            )
            data['logs'] = c.fetchall()

            return data
        finally:
            c.close()

    def get_analytics(self):
        """Legacy aggregate analytics used by older callers."""
        c = self._cursor()
        if not c:
            return {0: 0, 1: 0, 2: 0}, "N/A", "N/A", [], 0, 0, 0
        try:
            c.execute("SELECT SUM(grand_total), SUM(room_total), SUM(service_total) FROM payments")
            rev = c.fetchone()
            revenue = {'total': rev[0] or 0, 'room': rev[1] or 0, 'service': rev[2] or 0}
            c.execute(
                "SELECT room_type, COUNT(*) as cnt FROM bookings "
                "GROUP BY room_type ORDER BY cnt DESC LIMIT 1"
            )
            pop = c.fetchone()
            top_room = f"{pop[0]} ({pop[1]})" if pop else "N/A"
            c.execute(
                "SELECT service_name, COUNT(*) as cnt FROM services "
                "GROUP BY service_name ORDER BY cnt DESC LIMIT 1"
            )
            svc = c.fetchone()
            best_svc = f"{svc[0]} ({svc[1]})" if svc else "N/A"
            c.execute(
                "SELECT customer_name, SUM(grand_total) as s FROM payments "
                "GROUP BY customer_name ORDER BY s DESC LIMIT 5"
            )
            vips = c.fetchall()
            c.execute("SELECT COUNT(*) FROM rooms")
            total_rooms = c.fetchone()[0] or 1
            c.execute("SELECT COUNT(*) FROM rooms WHERE status='Occupied'")
            occupied = c.fetchone()[0] or 0
            c.execute("SELECT COUNT(*) FROM rooms WHERE status='Maintenance'")
            maintenance = c.fetchone()[0] or 0
            occupancy_rate = int((occupied / total_rooms) * 100) if total_rooms > 0 else 0
            return revenue, top_room, best_svc, vips, occupancy_rate, maintenance, total_rooms
        except Exception:
            return {0: 0, 1: 0, 2: 0}, "N/A", "N/A", [], 0, 0, 0
        finally:
            c.close()

    # ═══════════════════════════════════════════════════════════════════════════
    # HOUSEKEEPING
    # ═══════════════════════════════════════════════════════════════════════════

    def assign_cleaner_to_room(self, room_num, emp_id):
        """Set room → Cleaning, employee → Busy, log action."""
        c = self._cursor()
        try:
            c.execute(
                "UPDATE rooms SET status='Cleaning', assigned_employee_id=%s "
                "WHERE room_number=%s",
                (emp_id, room_num)
            )
            c.execute("UPDATE employees SET status='Busy' WHERE id=%s", (emp_id,))
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            c.execute(
                "INSERT INTO housekeeping_logs (room_number,action,date_time) VALUES (%s,%s,%s)",
                (room_num, "Cleaning Started", now)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"[assign_cleaner_to_room] {e}")
            self.conn.rollback()
            return False
        finally:
            c.close()

    def finish_cleaning_room(self, room_num):
        """Set room → Vacant, release cleaner → Active, log action."""
        c = self._cursor()
        try:
            c.execute(
                "SELECT assigned_employee_id FROM rooms WHERE room_number=%s", (room_num,)
            )
            row = c.fetchone()
            emp_id = row[0] if row else None
            c.execute(
                "UPDATE rooms SET status='Vacant', assigned_employee_id=NULL "
                "WHERE room_number=%s",
                (room_num,)
            )
            if emp_id:
                c.execute("UPDATE employees SET status='Active' WHERE id=%s", (emp_id,))
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            c.execute(
                "INSERT INTO housekeeping_logs (room_number,action,date_time) VALUES (%s,%s,%s)",
                (room_num, "Cleaning Finished", now)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"[finish_cleaning_room] {e}")
            self.conn.rollback()
            return False
        finally:
            c.close()

    def fetch_housekeeping_logs(self):
        c = self._cursor()
        try:
            c.execute("SELECT * FROM housekeeping_logs ORDER BY date_time DESC")
            return c.fetchall()
        finally:
            c.close()

    def get_housekeeping_logs(self):
        c = self._cursor()
        try:
            c.execute("SELECT * FROM housekeeping_logs ORDER BY id DESC")
            return c.fetchall()
        finally:
            c.close()

    def add_housekeeping_log(self, room, action):
        c = self._cursor()
        try:
            date = datetime.now().strftime("%Y-%m-%d %H:%M")
            c.execute(
                "INSERT INTO housekeeping_logs (room_number,action,date_time) VALUES (%s,%s,%s)",
                (room, action, date)
            )
            self.conn.commit()
        finally:
            c.close()

    # ═══════════════════════════════════════════════════════════════════════════
    # BOOKING LOGS
    # ═══════════════════════════════════════════════════════════════════════════

    def fetch_all_activity_logs(self):
        c = self._cursor()
        try:
            c.execute("SELECT * FROM booking_logs ORDER BY timestamp DESC LIMIT 200")
            return c.fetchall()
        finally:
            c.close()

    def insert_booking_log(self, bid_int, guest_name, action_type, staff_name="---"):
        """Append one entry to booking_logs; return True/False."""
        c = self._cursor()
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute(
                "INSERT INTO booking_logs "
                "(booking_id,guest_name,action_type,timestamp,performed_by) "
                "VALUES (%s,%s,%s,%s,%s)",
                (bid_int, guest_name, action_type, now, staff_name)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"[insert_booking_log] {e}")
            self.conn.rollback()
            return False
        finally:
            c.close()