import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QStackedWidget, QPushButton
from PyQt6.QtCore import pyqtSignal
from Controller.c_login import LoginController
from Controller.c_admin import AdminController
from Controller.c_staff import StaffController
from View.v_login import LoginView
from View.v_sidebar import Sidebar
from View.v_admin_ui import AdminHome, AdminManagement, AdminSummary
from View.v_staff_ui import StaffWindow


class MainWindow(QMainWindow):
    logout_signal = pyqtSignal()  # Custom signal to notify main loop

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hotella - Hotel Management System")
        self.setMinimumSize(1200, 800)
        self.central = QWidget()
        self.setCentralWidget(self.central)
        self.layout = QHBoxLayout(self.central)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

    def perform_logout(self):
        """Hides the main window and emits the logout signal to show login page."""
        self.hide()
        self.logout_signal.emit()

    def load_interface(self, role, display_name="Admin"):
        while self.layout.count(): self.layout.takeAt(0).widget().deleteLater()

        if role == 'admin':
            self.ctrl = AdminController()
            container = QWidget()
            cl = QHBoxLayout(container)
            cl.setContentsMargins(0, 0, 0, 0)

            self.sidebar = Sidebar(role)
            self.stack = QStackedWidget()

            self.admin_home = AdminHome(self.ctrl)
            self.admin_mgmt = AdminManagement(self.ctrl)
            self.admin_summary = AdminSummary(self.ctrl, admin_name=display_name)

            # Stack Indices: 0=Home, 1=Management, 2=Analytics
            self.stack.addWidget(self.admin_home)
            self.stack.addWidget(self.admin_mgmt)
            self.stack.addWidget(self.admin_summary)

            self.sidebar.page.connect(self.stack.setCurrentIndex)

            # Connect sidebar logout to our custom logout method
            self.sidebar.logout.connect(self.perform_logout)

            # CONNECT DASHBOARD CLICKS
            self.admin_home.switch_tab_signal.connect(self.handle_dashboard_redirection)

            cl.addWidget(self.sidebar)
            cl.addWidget(self.stack)
            self.layout.addWidget(container)
        else:
            self.ctrl = StaffController()
            self.staff_ui = StaffWindow(self.ctrl)
            self.layout.addWidget(self.staff_ui)

            # Find the staff logout button and intercept its default close() behavior
            for btn in self.staff_ui.findChildren(QPushButton):
                if btn.text() == "LOG OUT":
                    try:
                        btn.clicked.disconnect()
                    except TypeError:
                        pass  # Ignore if no connections exist
                    btn.clicked.connect(self.perform_logout)
                    break
        self.show()

    # ROUTING LOGIC
    def handle_dashboard_redirection(self, target_name):
        if target_name == "analytics":
            # Switch to Analytics Page (Index 2) and set default view
            self.stack.setCurrentIndex(2)
            self.admin_summary.set_annual_view()
        else:
            # Switch to Management Page (Index 1) and sub-tab
            self.stack.setCurrentIndex(1)
            self.admin_mgmt.navigate_to(target_name)


def main():
    app = QApplication(sys.argv)
    login_ctrl = LoginController()
    main_win = MainWindow()
    login = None

    def start_login():
        nonlocal login
        # Initialize or re-initialize the login view
        login = LoginView(login_ctrl)

        def on_login_success(role, username, real_name):
            print(f"Login Success: {role} - {username}")  # Debug Print
            login.close()
            try:
                display_name = real_name if real_name else username
                main_win.load_interface(role, display_name)
                if role != 'admin' and hasattr(main_win, 'ctrl'):
                    main_win.ctrl.set_user(display_name)
                main_win.show()  # Show main window here
            except Exception as e:
                print(f"CRASH during load_interface: {e}")
                import traceback
                traceback.print_exc()

        login.success.connect(on_login_success)
        login.show()

    # Connect the main window's logout signal back to the login loop
    main_win.logout_signal.connect(start_login)

    # Start the app by showing the login screen
    start_login()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()