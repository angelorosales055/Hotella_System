from Model.m_database import Database


class AdminModel:
    """
    Container / facade for admin-domain operations.
    NO SQL, NO cursors, NO c.execute anywhere in this file.
    Every method is a named delegation to Database.
    """

    def __init__(self):
        self.db = Database()

    # ── Dashboard ─────────────────────────────────────────────────────────────

    def get_total_revenue_year(self, year):
        return self.db.fetch_total_revenue_year(year)

    def get_employee_count(self):
        return self.db.fetch_employee_count()

    # ── Analytics ─────────────────────────────────────────────────────────────

    def get_payment_dates(self):
        return self.db.fetch_payment_dates()

    def get_analytics_data(self):
        return self.db.fetch_analytics_raw()

    def get_daily_revenue_data(self, year, month):
        return self.db.fetch_daily_revenue(year, month)

    def get_monthly_revenue_data(self, year):
        return self.db.fetch_monthly_revenue(year)

    def get_detailed_revenue_report(self):
        return self.db.fetch_report_data_comprehensive()

    def get_report_data_comprehensive(self):
        return self.db.fetch_report_data_comprehensive()

    # ── Employee management ───────────────────────────────────────────────────

    def get_all_employees(self):
        return self.db.fetch_all_employees()

    def add_employee(self, name, role, contact):
        return self.db.insert_employee(name, role, contact)

    def create_user_account(self, username, password, role, emp_id):
        return self.db.insert_user_account(username, password, role, emp_id)

    def update_employee_status(self, emp_id, status):
        return self.db.update_employee_status(emp_id, status)

    def delete_employee(self, emp_id):
        return self.db.delete_employee(emp_id)

    # ── Room management ───────────────────────────────────────────────────────

    def get_all_rooms(self):
        return self.db.fetch_all_rooms()

    def check_active_bookings(self, room_number):
        return self.db.fetch_room_has_active_bookings(room_number)

    def update_room_status(self, room_number, status):
        return self.db.update_room_status(room_number, status)

    def update_room_type(self, room_number, room_type):
        return self.db.update_room_type(room_number, room_type)

    def get_room_history_data(self, room_number):
        return self.db.fetch_room_history(room_number)

    def get_all_room_history_data(self):
        return self.db.fetch_all_room_history()

    def add_room(self, data):
        self.db.add_room(*data)

    def update_room(self, old_id, data):
        self.db.update_room(old_id, *data)

    def delete_room(self, room_number):
        self.db.delete_room(room_number)

    # ── Booking management ────────────────────────────────────────────────────

    def get_all_bookings(self):
        return self.db.fetch_all_bookings_admin()

    def add_booking(self, data):
        self.db.add_booking(*data)

    def update_booking(self, old_email, data):
        self.db.update_booking(old_email, *data)

    def delete_booking(self, email):
        self.db.delete_booking(email)

    # ── Services ─────────────────────────────────────────────────────────────

    def get_all_services(self):
        return self.db.fetch_all_services()

    def delete_service(self, service_id):
        self.db.delete_service(service_id)

    # ── Payments ─────────────────────────────────────────────────────────────

    def get_all_payments(self):
        return self.db.fetch_all_payments()

    def get_payments_by_date(self, start_date, end_date):
        # Returns all payments; date filtering is the controller's responsibility
        return self.db.fetch_all_payments()

    # ── Logs ─────────────────────────────────────────────────────────────────

    def get_all_activity_logs(self):
        return self.db.fetch_all_activity_logs()

    def get_housekeeping_logs(self):
        return self.db.fetch_housekeeping_logs()