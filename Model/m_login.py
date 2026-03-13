from Model.m_database import Database


class LoginModel:
    """Model responsible solely for authentication data access."""

    def __init__(self):
        self.db = Database()

    def authenticate(self, username, password):
        """Returns (username, role, employee_name) tuple or None."""
        return self.db.auth(username, password)