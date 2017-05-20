import os
import tempfile
import unittest

from pybel.constants import PYBEL_CONNECTION
from pybel_tools.web.application import create_application
from pybel_tools.web.security import build_security_service

TEST_USER_USERNAME = 'test@example.com'
TEST_USER_PASSWORD = 'password'
TEST_SECRET_KEY = 'pybel_web_tests'


class WebTest(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_file = tempfile.mkstemp()

        config = {
            'SECRET_KEY': TEST_SECRET_KEY,
            PYBEL_CONNECTION: 'sqlite:///' + self.db_file
        }

        self.app_instance = create_application(config)

        self.user_datastore = build_security_service(self.app_instance)
        self.user_datastore.create_user(email=TEST_USER_USERNAME, password=TEST_USER_PASSWORD)

        self.app = self.app_instance.test_client()

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_file)

    def login(self, username, password):
        return self.app.post('/login', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    def logout(self):
        return self.app.get('/logout', follow_redirects=True)

    def test_login(self):
        self.login(TEST_USER_USERNAME, TEST_USER_PASSWORD)


if __name__ == '__main__':
    unittest.main()
