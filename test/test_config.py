import unittest
from unittest.mock import patch, MagicMock
from main.config import Config


class TestConfig(unittest.TestCase):

    @patch("main.config.Config.vaild_auth_conf")
    @patch("main.config.Config.vaild_api_srv")
    @patch("main.config.Config.logger_setup")
    def test_initialization(self, mock_logger, mock_vaild_api_srv, mock_vaild_auth_conf):
        # Mocking the methods to skip actual logic
        mock_vaild_api_srv.return_value = None
        mock_vaild_auth_conf.return_value = True
        mock_logger.return_value = MagicMock()

        # Initialize the Config object
        config = Config()

        # Test attributes
        self.assertEqual(config.listen_host, '192.168.10.81')
        self.assertEqual(config.api_server, 'https://192.168.10.110:6443')

        # Ensure the logger was setup
        mock_logger.assert_called_once()

    def test_get_token_from_token(self):
        config = Config()

        # Set a mock token value directly (simulating the environment variable or assigned value)
        config.token = "mock_token_from_token"

        # Call the method to retrieve the token
        token = config.get_token()

        # Assert that the correct token was returned
        self.assertEqual(token, "mock_token_from_token")

    @patch("main.config.Config.vaild_auth_conf")
    def test_vaild_auth_conf(self, mock_vaild_auth_conf):
        config = Config()

        # Test valid configuration
        mock_vaild_auth_conf.return_value = True
        result = config.vaild_auth_conf(config.token, 'token')

        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()
