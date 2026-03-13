from Model.m_login import LoginModel


class LoginController:
    def __init__(self):
        self.model = LoginModel()

    def login(self, username, password):
        user_record = self.model.authenticate(username, password)
        if user_record:
            # user_record: (username, role, employee_name)
            return True, user_record[1], user_record[2]
        return False, None, None
