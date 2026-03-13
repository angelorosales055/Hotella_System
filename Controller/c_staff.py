from Model.m_staff import StaffModel
from datetime import datetime, date, timedelta
from PyQt6.QtWidgets import QFileDialog
import os

# ── Receipt imports ────────────────────────────────────────────────────────────
from reportlab.lib.pagesizes import A5
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as rl_canvas

# Receipt palette
_DARK  = colors.HexColor("#1A1A2E")
_GOLD  = colors.HexColor("#D4AF37")
_LIGHT = colors.HexColor("#F5F6FA")
_MID   = colors.HexColor("#7F8C8D")
_RED   = colors.HexColor("#C0392B")
_GREEN = colors.HexColor("#27AE60")
_WHITE = colors.white
_RW, _RH = A5


class StaffController:
    def __init__(self):
        self.model = StaffModel()
        self.current_staff = "Staff"

    MAX_OCCUPANCY = {"Single": 1, "Double": 2, "Queen": 3, "King": 4, "Suite": 6}

    # Official services with prices
    SERVICES = [
        ("Breakfast Set",     150),
        ("Lunch Set",         250),
        ("Dinner Set",        250),
        ("Laundry (Per kg)",  100),
        ("Cleaning Service",  500),
    ]

    def set_user(self, name):
        self.current_staff = name if name else "Staff"

    # ── Services catalogue ────────────────────────────────────────────────────

    def get_available_services(self):

        current_hour = datetime.now().hour
        result = []
        for svc, price in self.SERVICES:
            available = True
            note = ""
            if "Breakfast" in svc and current_hour >= 11:
                available = False
                note = "Ended"
            result.append({'name': svc, 'price': price, 'available': available, 'note': note})
        return result

    def get_service_staff_list(self):
        return self.model.get_service_staff()

    # ── Billing & Checkout ────────────────────────────────────────────────────

    def calculate_bill(self, bid):
        data = self.model.get_booking_details_for_bill(bid)
        if not data:
            return None
        try:
            fmt        = "%Y-%m-%d"
            start_d    = datetime.strptime(data['start_date'], fmt).date()
            today_d    = datetime.now().date()
            expected_end = start_d + timedelta(days=data['days'])

            penalty      = 0
            penalty_desc = ""

            if today_d < expected_end:
                daily_rate   = data['room_cost'] / data['days']
                penalty      = daily_rate * 0.5
                penalty_desc = "Early Departure Fee (0.5 Night)"
            elif today_d > expected_end:
                overstay_days = (today_d - expected_end).days
                daily_rate    = data['room_cost'] / data['days']
                penalty       = daily_rate * overstay_days * 1.5
                penalty_desc  = f"Overstay Penalty ({overstay_days} days @ 150%)"

            data['penalty']       = int(penalty)
            data['penalty_desc']  = penalty_desc
            data['final_total']   = data['total'] + int(penalty)
            data['final_balance'] = data['final_total'] - data['paid']
            return data
        except Exception as e:
            print("Calc Error:", e)
            return data

    def get_checkout_cards(self):
        raw_data  = self.model.get_checkout_candidates()
        card_list = []
        for row in raw_data:
            financials = self.calculate_bill(row[1])
            if financials:
                financials['room'] = row[0]
                financials['bid']  = row[1]
                card_list.append(financials)
        return card_list

    def process_checkout(self, data, tendered_amount, method):
        try:
            bid         = data['bid']
            guest_name  = data.get('guest', data.get('name', 'Guest'))
            total_bill  = data['final_total']
            paid_prev   = data['paid']
            balance     = total_bill - paid_prev
            revenue_rec = min(tendered_amount, balance) if tendered_amount > 0 else 0

            remark = "Checkout Settlement"
            if data.get('penalty', 0) > 0:
                remark += f" (Inc. {data['penalty_desc']})"

            pay_id = None
            if revenue_rec > 0:
                pay_id = self.model.add_payment(
                    bid, guest_name, data['room_cost'], data['svc_cost'],
                    data['final_total'], method, revenue_rec,
                    self.current_staff, remark, None
                )

            self.model.update_booking_status(bid, 'Checked Out')
            self.model.update_room_status(data['room'], 'Dirty')
            self.model.add_booking_log(bid, guest_name, 'Checked Out', self.current_staff)

            receipt_data             = data.copy()
            receipt_data['guest']    = guest_name
            receipt_data['staff']    = self.current_staff
            receipt_data['paid_prev'] = paid_prev
            receipt_data['remark']   = remark

            return True, "Checkout Complete", receipt_data, pay_id
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"Checkout failed: {str(e)}", None, None

    # ── Receipt generation ────────────────────────────────────────────────────

    def generate_receipt(self, data, paid_now, method, payment_id):
        """Generate a styled A5 PDF receipt using ReportLab."""
        if not payment_id:
            return
        try:
            now       = datetime.now()
            serial    = f"OR-{now.strftime('%Y%m')}-{payment_id:06d}"
            save_dir  = os.path.join("receipts", now.strftime("%Y-%m-%d"))
            os.makedirs(save_dir, exist_ok=True)
            filename  = f"{serial}_{now.strftime('%Y%m%d_%H%M%S')}.pdf"
            full_path = os.path.abspath(os.path.join(save_dir, filename))

            room_cost  = int(data.get('room_cost',   0))
            svc_cost   = int(data.get('svc_cost',    0))
            penalty    = int(data.get('penalty',     0))
            total      = int(data.get('final_total', room_cost + svc_cost + penalty))
            prev_paid  = int(data.get('paid_prev',   data.get('paid', 0)))
            paid_now   = int(paid_now)
            balance    = max(0, total - prev_paid - paid_now)
            change     = max(0, prev_paid + paid_now - total)
            remarks    = str(data.get('remark', data.get('remarks', 'Payment')))

            raw_bid    = data.get('bid', 0)
            bid_int    = int(str(raw_bid).replace("B", "")) if raw_bid else 0
            bid_str    = f"B{bid_int:05d}"
            guest      = str(data.get('guest', data.get('name', 'Guest'))).title()
            room       = str(data.get('room', 'N/A'))
            staff      = data.get('staff', self.current_staff)

            c = rl_canvas.Canvas(full_path, pagesize=A5)

            def hline(y, x1=12*mm, x2=_RW-12*mm, color=colors.HexColor("#DDDDDD"), width=0.5):
                c.setStrokeColor(color); c.setLineWidth(width); c.line(x1, y, x2, y)

            band_h = 38 * mm
            c.setFillColor(_DARK)
            c.rect(0, _RH - band_h, _RW, band_h, fill=1, stroke=0)

            c.setFillColor(_GOLD); c.setFont("Helvetica-Bold", 22)
            c.drawCentredString(_RW / 2, _RH - 14*mm, "HOTELLA")
            c.setFillColor(_WHITE); c.setFont("Helvetica", 7.5)
            c.drawCentredString(_RW / 2, _RH - 21*mm, "Hotel & Services  |  Davao City, Philippines")
            c.setFillColor(_GOLD); c.setFont("Helvetica-Bold", 9)
            c.drawCentredString(_RW / 2, _RH - 29*mm, "OFFICIAL RECEIPT")
            c.setFillColor(_WHITE); c.setFont("Helvetica", 7)
            c.drawCentredString(_RW / 2, _RH - 35*mm, f"Serial No: {serial}")

            y    = _RH - band_h - 5*mm
            meta = [
                ("Date & Time",  now.strftime("%Y-%m-%d  %I:%M %p")),
                ("Booking Ref",  bid_str),
                ("Guest Name",   guest),
                ("Room Number",  room),
                ("Processed By", staff),
                ("Method",       method),
            ]
            for label, value in meta:
                c.setFillColor(_MID);  c.setFont("Helvetica", 7.5)
                c.drawString(14*mm, y, label)
                c.setFillColor(_DARK); c.setFont("Helvetica-Bold", 7.5)
                c.drawRightString(_RW - 14*mm, y, value)
                y -= 6.5 * mm

            hline(y + 2*mm, color=_GOLD, width=1); y -= 4 * mm

            c.setFillColor(_DARK)
            c.rect(12*mm, y - 5*mm, _RW - 24*mm, 8*mm, fill=1, stroke=0)
            c.setFillColor(_WHITE); c.setFont("Helvetica-Bold", 8)
            c.drawString(15*mm, y - 1.5*mm, "DESCRIPTION")
            c.drawRightString(_RW - 15*mm, y - 1.5*mm, "AMOUNT")
            y -= 11 * mm

            def item_row(desc, amt):
                nonlocal y
                c.setFillColor(_DARK); c.setFont("Helvetica", 8)
                c.drawString(15*mm, y, desc)
                c.setFont("Helvetica-Bold", 8)
                c.drawRightString(_RW - 15*mm, y, f"PHP {amt:,.2f}")
                y -= 6.5 * mm

            item_row("Room Charge", room_cost)
            svc_details = data.get('svc_details', [])
            if svc_details:
                for s in svc_details:
                    lbl = f"  {s.get('name', 'Service')}"
                    if s.get('qty', 1) > 1:
                        lbl += f" x{s['qty']}"
                    item_row(lbl, s.get('total', s.get('price', 0)))
            elif svc_cost > 0:
                item_row("Services", svc_cost)
            if penalty > 0:
                item_row(data.get('penalty_desc', 'Penalty'), penalty)

            hline(y + 2*mm); y -= 4 * mm

            def total_row(label, value_str, bold=False, highlight=False, val_color=_DARK):
                nonlocal y
                if highlight:
                    c.setFillColor(_LIGHT)
                    c.rect(12*mm, y - 3.5*mm, _RW - 24*mm, 8*mm, fill=1, stroke=0)
                c.setFillColor(_DARK)
                c.setFont("Helvetica-Bold" if bold else "Helvetica", 8.5 if bold else 8)
                c.drawString(15*mm, y, label)
                c.setFillColor(val_color)
                c.setFont("Helvetica-Bold", 8.5 if bold else 8)
                c.drawRightString(_RW - 15*mm, y, value_str)
                y -= 8 * mm

            total_row("Grand Total",     f"PHP {total:,.2f}",    bold=True, highlight=True, val_color=_GOLD)
            total_row("Previously Paid", f"PHP {prev_paid:,.2f}")
            total_row("Paid Now",        f"PHP {paid_now:,.2f}")

            hline(y + 3*mm, color=_GOLD, width=1); y -= 3 * mm

            if change > 0:
                b_label, b_value, b_color = "CHANGE",      f"PHP {change:,.2f}",  _GREEN
            else:
                b_label, b_value, b_color = "BALANCE DUE", f"PHP {balance:,.2f}", _RED if balance > 0 else _GREEN

            c.setFillColor(_DARK);  c.setFont("Helvetica-Bold", 9)
            c.drawString(15*mm, y, b_label)
            c.setFillColor(b_color); c.setFont("Helvetica-Bold", 9)
            c.drawRightString(_RW - 15*mm, y, b_value)
            y -= 6 * mm

            hline(y + 2*mm); y -= 5 * mm
            c.setFillColor(_GOLD);  c.setFont("Helvetica-Bold", 7.5)
            c.drawString(15*mm, y, "REMARKS:")
            c.setFillColor(_DARK);  c.setFont("Helvetica", 7.5)
            c.drawString(38*mm, y, remarks)
            y -= 10 * mm

            hline(y + 3*mm, color=_GOLD, width=0.8)
            c.setFillColor(_MID); c.setFont("Helvetica-Oblique", 7)
            c.drawCentredString(_RW / 2, y - 2*mm,  "Thank you for staying with us at Hotella!")
            c.drawCentredString(_RW / 2, y - 8*mm,  "This is a computer-generated receipt and is valid without signature.")
            c.setFont("Helvetica", 6.5)
            c.drawCentredString(_RW / 2, y - 14*mm, "\u00a9 2026 Hotella. All rights reserved.")

            c.save()
            print(f"[Receipt] Saved → {full_path}")
        except Exception as e:
            import traceback
            print(f"[Receipt] Generation failed (non-critical): {e}")
            traceback.print_exc()

    # ── Services ─────────────────────────────────────────────────────────────

    def add_service_charge(self, bid, room_number, service_name, price, quantity, employee_name):
        emp_data = self.model.get_employee_metadata(employee_name)
        if not emp_data:
            return False, "Invalid staff member."
        emp_id, role = emp_data
        if role in ("Manager", "Receptionist", "Cleaner"):
            return False, f"Permission Denied: {role}s cannot perform Room Service."
        total = price * quantity
        svc_date = datetime.now().strftime("%Y-%m-%d")
        if self.model.add_service(bid, room_number, service_name, total, svc_date, emp_id, quantity):
            try:
                _, guest_name = self.model.get_active_guest(room_number)
                guest_name = guest_name or "Guest"
                self.model.add_booking_log(
                    bid, guest_name,
                    f"Added Service: {service_name} (x{quantity})",
                    self.current_staff
                )
            except Exception as e:
                print(f"Failed to log service: {e}")
            return True, "Service added successfully."
        return False, "Database error."

    # ── Rooms ─────────────────────────────────────────────────────────────────

    def get_active_room_details(self, room_number):
        return self.model.get_active_guest(room_number)

    def get_stats(self):
        return self.model.get_room_counts()

    def get_map_data(self):
        return self.model.get_all_rooms_data()

    def search_rooms(self, d_in, d_out):
        return self.model.get_available_rooms(d_in, d_out)

    def get_room_prices(self):
        return {"Single": 1500, "Double": 2500, "Queen": 3500, "King": 4500, "Suite": 6000}

    # ── Bookings ──────────────────────────────────────────────────────────────

    def get_todays_arrivals(self):
        return self.model.get_todays_bookings()

    def cancel_booking_today(self, bid, name):
        if self.model.update_booking_status(bid, 'Cancelled'):
            self.model.add_booking_log(bid, name, "Cancelled", self.current_staff)
            return True, "Booking Cancelled"
        return False, "Error"

    def create_booking_final(self, data, room_id, payment_data):
        selected_date = datetime.strptime(data['date'], "%Y-%m-%d").date()
        if selected_date < datetime.now().date():
            return False, "You cannot book for a past date."

        total    = data['total_price']
        paid     = payment_data['amount']
        method   = payment_data['method']
        card_num = payment_data.get('card_number', None)
        guests   = data.get('guests', 1)
        limit    = self.MAX_OCCUPANCY.get(data.get('room_type'), 2)

        if guests > limit:
            return False, f"Maximum occupancy for {data.get('room_type')} is {limit} guest(s)."
        if "Credit Card" not in method:
            min_req = int(total * 0.20)
            if paid < min_req:
                return False, f"Minimum 20% downpayment (₱{min_req:,}) is required."

        bid = self.model.create_booking_final(data, room_id, self.current_staff)
        if bid:
            guest_name  = data.get('name') or data.get('Name', 'Guest')
            remark_text = "Downpayment"
            pay_id = self.model.add_payment(
                bid, guest_name, total, 0, total, method, paid,
                self.current_staff, remark_text, card_num
            )

            receipt_data = None
            if pay_id and paid > 0:
                receipt_data = {
                    'bid': bid, 'guest': guest_name, 'room': room_id,
                    'type': data.get('room_type'), 'staff': self.current_staff,
                    'room_cost': total, 'svc_cost': 0, 'svc_details': [],
                    'final_total': total, 'paid_prev': 0,
                    'remark': remark_text, 'penalty': 0, 'penalty_desc': '',
                }

            self.model.add_booking_log(bid, guest_name, "Booking Created", self.current_staff)
            return True, (bid, receipt_data, paid, method, pay_id)

        return False, "Database Error"

    def get_all_bookings(self):
        return self.model.get_all_bookings()

    def get_overdue_guests(self):
        today  = datetime.now().date()
        result = []
        for b in self.model.get_all_bookings():
            if b.get('status') == 'Checked In':
                try:
                    start_date       = datetime.strptime(str(b.get('date', '')), "%Y-%m-%d").date()
                    expected_checkout = start_date + timedelta(days=int(b.get('days', 0)))
                    if today > expected_checkout:
                        b['overdue_by'] = (today - expected_checkout).days
                        result.append(b)
                except Exception:
                    continue
        return result

    # ── Housekeeping ──────────────────────────────────────────────────────────

    def get_available_cleaners(self):
        return self.model.get_available_cleaners()

    def assign_cleaner(self, room_num, emp_name):
        cleaners = self.model.get_available_cleaners()
        emp_id   = next((c[0] for c in cleaners if c[1] == emp_name), None)
        if emp_id and self.model.assign_cleaner_to_room(room_num, emp_id):
            try:
                self.model.add_booking_log(
                    0, f"Room {room_num}",
                    f"Assigned Cleaner: {emp_name}",
                    self.current_staff
                )
            except Exception:
                pass
            return True, "Cleaner assigned!"
        return False, "Assignment failed."

    def finish_cleaning(self, room_num):
        if self.model.finish_cleaning_room(room_num):
            try:
                self.model.add_booking_log(
                    0, f"Room {room_num}", "Marked Room as Clean", self.current_staff
                )
            except Exception:
                pass
            return True, "Room is now clean."
        return False, "Failed."

    def mark_arrived(self, bid, name):
        room_data = self.model.get_room_status_by_booking(bid)
        if room_data and room_data[0] in ('Dirty', 'Cleaning'):
            return False, f"Room {room_data[1]} is {room_data[0]}."
        if self.model.update_booking_status(bid, "Checked In"):
            self.model.add_booking_log(bid, name, "Checked In", self.current_staff)
            if room_data:
                self.model.update_room_status(room_data[1], 'Occupied')
            return True, "Guest Checked In"
        return False, "Error"
