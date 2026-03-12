from Model.m_database import Database

class LoginController:
    def __init__(self):
        self.db = Database()

    def login(self, username, password):
        user_record = self.db.auth(username, password)
        if user_record:
            # user_record is now: (username, role, employee_name)
            return True, user_record[1], user_record[2]
        return False, None, None