import unittest
from unittest.mock import patch, MagicMock
from main.np_operator import Tools, init_fn
from kubernetes import client
import kopf


class TestOperator(unittest.TestCase):

    # 测试命名空间保护功能
    @patch("main.np_operator.api.patch_namespace")
    def test_sub_np_fn(self, mock_patch_namespace):
        mock_logger = MagicMock()
        ns = 'test-namespace'

        # Initialize api using init_fn
        api, tools = init_fn(None)

        # Call the method to add the protection annotation
        tools.sub_np_fn(ns, mock_logger)

        # Check if patch_namespace was called with correct parameters
        mock_patch_namespace.assert_called_once_with(ns, {
            'metadata': {'annotations': {'namespaceprotect.hj.com/protect': 'true'}}})
        mock_logger.info.assert_called_once_with(f'Protected namespace {ns}.')

    # 测试命名空间更新保护功能
    @patch("main.np_operator.api.patch_namespace")
    @patch("main.np_operator.Tools.get_all_ns")
    def test_sub_update_fn(self, mock_get_all_ns, mock_patch_namespace):
        mock_logger = MagicMock()
        ns = 'test-namespace'
        new = ['new-namespace']

        # Mock the behavior of get_all_ns to return a valid namespace list
        mock_get_all_ns.return_value = ['test-namespace', 'other-namespace']

        # Initialize api using init_fn
        api, tools = init_fn(None)

        # Call the method to unprotect the namespace
        result = tools.sub_update_fn(ns, new, mock_logger)

        # Check the returned message and if patch_namespace was called correctly
        self.assertEqual(result['message'], f'old namespace: {ns} is unprotected')
        mock_patch_namespace.assert_called_once_with(ns, {
            'metadata': {'annotations': {'namespaceprotect.hj.com/protect': None}}})
        mock_logger.info.assert_called_once_with(f'old namespace: {ns} is unprotected')

    # 测试命名空间删除验证：确保已保护的命名空间不能被删除
    @patch("main.np_operator.kopf.AdmissionError")
    @patch("main.np_operator.api.read_namespace")
    def test_validate_namespace_protection(self, mock_read_namespace, mock_AdmissionError):
        mock_body = MagicMock()
        mock_body.metadata.name = 'test-namespace'
        mock_body.metadata.annotations = {'namespaceprotect.hj.com/protect': 'true'}

        # Simulate the read_namespace call to return a protected namespace
        mock_read_namespace.return_value = mock_body

        # Test validate_namespace raises an AdmissionError if the namespace is protected
        with self.assertRaises(kopf.AdmissionError):
            # Call the validation function (simulate DELETE operation)
            mock_AdmissionError("Namespace: test-namespace is protected and cannot be deleted.")

    # 测试命名空间的 CRD 参数验证
    @patch("main.np_operator.Tools.get_all_ns")
    def test_validate_np_params(self, mock_get_all_ns):
        mock_body = MagicMock()

        # Test case where both namespaces and selectors are provided
        mock_body.spec = {'namespaces': ['ns1'], 'selectors': {'labels': {}}}

        # Simulate the validation failure (only one of them should be configured)
        with self.assertRaises(kopf.PermanentError):
            # Call the validate_np_params method
            kopf.on.validate_np_params(mock_body)

        # Test case where neither namespaces nor selectors are provided
        mock_body.spec = {}

        with self.assertRaises(kopf.PermanentError):
            # Call the validate_np_params method
            kopf.on.validate_np_params(mock_body)

    # 测试 np_fn 的命名空间保护应用
    @patch("main.np_operator.Tools.sub_np_fn")
    def test_np_fn(self, mock_sub_np_fn):
        spec = {
            'namespaces': ['ns1', 'ns2'],
            'selectors': {}
        }

        mock_logger = MagicMock()
        # Initialize api using init_fn
        api, tools = init_fn(None)

        # Call np_fn to apply protection
        result = tools.np_fn(spec, mock_logger)

        # Ensure that sub_np_fn was called for each namespace
        mock_sub_np_fn.assert_any_call('ns1', mock_logger)
        mock_sub_np_fn.assert_any_call('ns2', mock_logger)

        self.assertEqual(result['message'], 'Namespace protection applied successfully')

    # 测试命名空间保护功能（模拟命名空间保护）
    @patch("main.np_operator.api.list_namespace")
    def test_get_all_ns(self, mock_list_namespace):
        # Mock the response of list_namespace
        mock_namespace = MagicMock()
        mock_namespace.metadata.name = 'test-namespace'
        mock_list_namespace.return_value.items = [mock_namespace]

        # Mock settings to avoid passing None to init_fn
        mock_settings = MagicMock()
        mock_settings.posting.level = logging.WARNING  # Mock posting.level

        # Initialize api using init_fn
        api, tools = init_fn(mock_settings)

        # Test retrieving all namespaces
        result = list(tools.get_all_ns(ns='name'))

        # Assert the returned namespace list
        self.assertEqual(result, ['test-namespace'])

    # 测试命名空间的 CRD 参数验证：确保只有一个配置项被设置
    @patch("main.np_operator.api.read_namespace")
    def test_validate_np_params(self, mock_read_namespace):
        mock_body = MagicMock()

        # Simulate missing namespaces and selectors
        mock_body.spec = {}

        with self.assertRaises(kopf.PermanentError):
            # Call validate_np_params
            kopf.on.validate_np_params(mock_body)


if __name__ == '__main__':
    unittest.main()
