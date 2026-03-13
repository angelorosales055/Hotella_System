from Model.m_database import Database
from datetime import datetime


class StaffModel:
    """
    Container / facade for staff-domain operations.
    NO SQL, NO cursors, NO c.execute anywhere in this file.
    Every method is a named delegation to Database.
    """

    def __init__(self):
        self.db = Database()

    # ── Employees ─────────────────────────────────────────────────────────────

    def get_service_staff(self):
        return self.db.fetch_service_staff()

    def get_available_cleaners(self):
        return self.db.fetch_available_cleaners()

    def get_employee_metadata(self, name):
        return self.db.fetch_employee_metadata(name)

    # ── Billing ───────────────────────────────────────────────────────────────

    def get_booking_details_for_bill(self, bid):
        """
        Return a dict of billing data for a booking.
        Service cost aggregation is done here because it is
        domain assembly (not SQL), and it belongs in the model layer.
        """
        bid_int = int(str(bid).replace("B", ""))

        row = self.db.fetch_booking_details_for_bill(bid_int)
        if not row:
            return None

        name, price, rtype, start_date_str, duration = row

        services_data = self.db.fetch_services_by_booking(bid_int)
        svc_cost = sum(s[1] * s[2] for s in services_data)
        svc_details = [
            {'name': s[0], 'price': s[1], 'qty': s[2], 'total': s[1] * s[2]}
            for s in services_data
        ]

        paid = self.db.fetch_total_amount_paid(bid_int)

        return {
            'guest':       name,
            'type':        rtype,
            'room_cost':   price,
            'svc_cost':    svc_cost,
            'svc_details': svc_details,
            'total':       price + svc_cost,
            'paid':        paid,
            'start_date':  start_date_str,
            'days':        duration,
        }

    # ── Housekeeping ──────────────────────────────────────────────────────────

    def assign_cleaner_to_room(self, room_num, emp_id):
        return self.db.assign_cleaner_to_room(room_num, emp_id)

    def finish_cleaning_room(self, room_num):
        return self.db.finish_cleaning_room(room_num)

    # ── Rooms ─────────────────────────────────────────────────────────────────

    def get_room_status_by_booking(self, bid):
        bid_int = int(str(bid).replace("B", ""))
        return self.db.fetch_room_status_by_booking(bid_int)

    def get_available_rooms(self, d_in, d_out):
        return self.db.fetch_available_rooms(d_in, d_out)

    def get_room_counts(self):
        return self.db.fetch_room_counts()

    def get_all_rooms_data(self):
        return self.db.fetch_all_rooms_full()

    def get_dirty_rooms(self):
        return self.db.fetch_dirty_rooms()

    def update_room_status(self, room_number, status):
        return self.db.update_room_status(room_number, status)

    # ── Bookings ──────────────────────────────────────────────────────────────

    def get_checkout_candidates(self):
        return self.db.fetch_checkout_candidates()

    def get_todays_bookings(self):
        today = datetime.now().strftime("%Y-%m-%d")
        rows = self.db.fetch_todays_bookings(today)
        return [
            {'bid': f"B{r[0]:05d}", 'name': r[1], 'type': r[2],
             'room': r[3] or 'N/A', 'price': r[4], 'status': r[5]}
            for r in rows
        ]

    def get_all_bookings(self):
        rows = self.db.fetch_all_bookings_staff()
        return [
            {'bid': f"B{r[0]:05d}", 'name': r[1], 'room_type': r[2],
             'room': r[3] or 'N/A', 'price': r[4], 'status': r[5],
             'date': r[6], 'days': r[7]}
            for r in rows
        ]

    def update_booking_status(self, bid, new_status):
        bid_int = int(str(bid).replace("B", ""))
        return self.db.update_booking_status(bid_int, new_status)

    def create_booking_final(self, d, room_id, staff_name):
        # 🟢 FIX: Check for both lowercase and capitalized keys from the UI
        name = d.get('name') or d.get('Name', '')
        email = d.get('email') or d.get('Email', '')
        phone = d.get('phone') or d.get('Phone', '')
        address = d.get('address') or d.get('Address', '')

        raw_bid = self.db.insert_booking_full(
            name, email, phone, address,
            d['room_type'], d['date'], d['days'], d['total_price'],
            d['guests'], staff_name
        )
        if not raw_bid:
            return False
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.db.insert_transaction(raw_bid, room_id, now)
        return f"B{raw_bid:05d}"

    # ── Active guest ──────────────────────────────────────────────────────────

    def get_active_guest(self, room_num):
        row = self.db.fetch_active_guest_by_room(room_num)
        return (f"B{row[0]:05d}", row[1]) if row else (None, None)

    # ── Services ──────────────────────────────────────────────────────────────

    def add_service(self, bid, room, name, total_cost, date, emp_id, quantity):
        bid_int = int(str(bid).replace("B", ""))
        return self.db.insert_service(bid_int, room, name, total_cost, date, emp_id, quantity)

    # ── Payments ──────────────────────────────────────────────────────────────

    def add_payment(self, bid, name, r, s, g, m, a, staff_name, remarks, card_num=None):
        bid_int = int(str(bid).replace("B", ""))
        date = datetime.now().strftime("%Y-%m-%d %H:%M")
        return self.db.insert_payment(
            bid_int, str(name), int(r), int(s), int(g),
            str(m), date, int(a),
            str(card_num) if card_num else None,
            str(staff_name), str(remarks)
        )

    # ── Booking logs ──────────────────────────────────────────────────────────

    def add_booking_log(self, bid, guest, action, staff_name="---"):
        bid_int = int(str(bid).replace("B", ""))
        return self.db.insert_booking_log(bid_int, guest, action, staff_name)