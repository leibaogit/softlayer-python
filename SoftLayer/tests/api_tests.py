"""
    SoftLayer.tests.api_tests
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    :copyright: (c) 2013, SoftLayer Technologies, Inc. All rights reserved.
    :license: BSD, see LICENSE for more details.
"""
try:
    import unittest2 as unittest
except ImportError:
    import unittest  # NOQA

from mock import patch, call

import SoftLayer
import SoftLayer.API
from SoftLayer.consts import USER_AGENT


class Inititialization(unittest.TestCase):
    def test_init(self):
        client = SoftLayer.Client(username='doesnotexist',
                                  api_key='issurelywrong', timeout=10)

        self.assertEquals(client.auth.username, 'doesnotexist')
        self.assertEquals(client.auth.api_key, 'issurelywrong')
        self.assertEquals(client._endpoint_url,
                          SoftLayer.API_PUBLIC_ENDPOINT.rstrip('/'))

    @patch.dict('os.environ', {
        'SL_USERNAME': 'test_user', 'SL_API_KEY': 'test_api_key'})
    def test_env(self):
        client = SoftLayer.Client()
        self.assertEquals(client.auth.username, 'test_user')
        self.assertEquals(client.auth.api_key, 'test_api_key')

    @patch('SoftLayer.API.API_USERNAME', 'test_user')
    @patch('SoftLayer.API.API_KEY', 'test_api_key')
    def test_globals(self):
        client = SoftLayer.Client()
        self.assertEquals(client.auth.username, 'test_user')
        self.assertEquals(client.auth.api_key, 'test_api_key')


class ClientMethods(unittest.TestCase):
    def test_help(self):
        help(SoftLayer)
        help(SoftLayer.Client)
        client = SoftLayer.Client(
            username='doesnotexist',
            api_key='issurelywrong'
        )
        help(client)
        help(client['SERVICE'])

    def test_repr(self):
        client = SoftLayer.Client(
            username='doesnotexist',
            api_key='issurelywrong'
        )
        self.assertIn("Client", repr(client))

    def test_service_repr(self):
        client = SoftLayer.Client(
            username='doesnotexist',
            api_key='issurelywrong'
        )
        self.assertIn("Service", repr(client['SERVICE']))


class APIClient(unittest.TestCase):
    def setUp(self):
        self.client = SoftLayer.Client(
            username='doesnotexist', api_key='issurelywrong',
            endpoint_url="ENDPOINT")

    @patch('SoftLayer.API.make_xml_rpc_api_call')
    def test_simple_call(self, make_xml_rpc_api_call):
        self.client['SERVICE'].METHOD()
        make_xml_rpc_api_call.assert_called_with(
            'ENDPOINT/SoftLayer_SERVICE', 'METHOD', (),
            headers={
                'authenticate': {
                    'username': 'doesnotexist', 'apiKey': 'issurelywrong'}},
            timeout=None,
            http_headers={
                'Content-Type': 'application/xml',
                'User-Agent': USER_AGENT,
            })

    @patch('SoftLayer.API.make_xml_rpc_api_call')
    def test_complex(self, make_xml_rpc_api_call):
        self.client['SERVICE'].METHOD(
            1234,
            id=5678,
            mask={'object': {'attribute': ''}},
            raw_headers={'RAW': 'HEADER'},
            filter={
                'TYPE': {'obj': {'attribute': {'operation': '^= prefix'}}}},
            limit=9, offset=10)

        make_xml_rpc_api_call.assert_called_with(
            'ENDPOINT/SoftLayer_SERVICE', 'METHOD', (1234, ),
            headers={
                'SoftLayer_SERVICEObjectMask': {
                    'mask': {'object': {'attribute': ''}}},
                'SoftLayer_SERVICEObjectFilter': {
                    'TYPE': {
                        'obj': {'attribute': {'operation': '^= prefix'}}}},
                'authenticate': {
                    'username': 'doesnotexist', 'apiKey': 'issurelywrong'},
                'SoftLayer_SERVICEInitParameters': {'id': 5678},
                'resultLimit': {'limit': 9, 'offset': 10}},
            timeout=None,
            http_headers={
                'RAW': 'HEADER',
                'Content-Type': 'application/xml',
                'User-Agent': USER_AGENT,
            })

    @patch('SoftLayer.API.make_xml_rpc_api_call')
    def test_mask_call_v2(self, make_xml_rpc_api_call):
        self.client['SERVICE'].METHOD(
            mask="mask[something[nested]]")
        make_xml_rpc_api_call.assert_called_with(
            'ENDPOINT/SoftLayer_SERVICE', 'METHOD', (),
            headers={
                'authenticate': {
                    'username': 'doesnotexist', 'apiKey': 'issurelywrong'},
                'SoftLayer_ObjectMask': {'mask': 'mask[something[nested]]'}},
            timeout=None,
            http_headers={
                'Content-Type': 'application/xml',
                'User-Agent': USER_AGENT,
            })

    @patch('SoftLayer.API.make_xml_rpc_api_call')
    def test_mask_call_v2_dot(self, make_xml_rpc_api_call):
        self.client['SERVICE'].METHOD(
            mask="mask.something.nested")
        make_xml_rpc_api_call.assert_called_with(
            'ENDPOINT/SoftLayer_SERVICE', 'METHOD', (),
            headers={
                'authenticate': {
                    'username': 'doesnotexist', 'apiKey': 'issurelywrong'},
                'SoftLayer_ObjectMask': {'mask': 'mask[something.nested]'}},
            timeout=None,
            http_headers={
                'Content-Type': 'application/xml',
                'User-Agent': USER_AGENT,
            })

    @patch('SoftLayer.API.make_xml_rpc_api_call')
    def test_mask_call_invalid_mask(self, make_xml_rpc_api_call):
        try:
            self.client['SERVICE'].METHOD(mask="mask[something.nested")
        except SoftLayer.SoftLayerError, e:
            self.assertIn('Malformed Mask', str(e))
        else:
            self.fail('No exception raised')

    @patch('SoftLayer.API.Client.iter_call')
    def test_iterate(self, _iter_call):
        self.client['SERVICE'].METHOD(iter=True)
        _iter_call.assert_called_with('SERVICE', 'METHOD')

    @patch('SoftLayer.API.Client.iter_call')
    def test_service_iter_call(self, _iter_call):
        self.client['SERVICE'].iter_call('METHOD')
        _iter_call.assert_called_with('SERVICE', 'METHOD')

    @patch('SoftLayer.API.Client.call')
    def test_iter_call(self, _call):
        # chunk=100, no limit
        _call.side_effect = [range(100), range(100, 125)]
        result = list(self.client.iter_call('SERVICE', 'METHOD', iter=True))

        self.assertEquals(range(125), result)
        _call.assert_has_calls([
            call('SERVICE', 'METHOD', limit=100, iter=False, offset=0),
            call('SERVICE', 'METHOD', limit=100, iter=False, offset=100),
        ])
        _call.reset_mock()

        # chunk=100, no limit. Requires one extra request.
        _call.side_effect = [range(100), range(100, 200), []]
        result = list(self.client.iter_call('SERVICE', 'METHOD', iter=True))
        self.assertEquals(range(200), result)
        _call.assert_has_calls([
            call('SERVICE', 'METHOD', limit=100, iter=False, offset=0),
            call('SERVICE', 'METHOD', limit=100, iter=False, offset=100),
            call('SERVICE', 'METHOD', limit=100, iter=False, offset=200),
        ])
        _call.reset_mock()

        # chunk=25, limit=30
        _call.side_effect = [range(0, 25), range(25, 30)]
        result = list(self.client.iter_call(
            'SERVICE', 'METHOD', iter=True, limit=30, chunk=25))
        self.assertEquals(range(30), result)
        _call.assert_has_calls([
            call('SERVICE', 'METHOD', iter=False, limit=25, offset=0),
            call('SERVICE', 'METHOD', iter=False, limit=5, offset=25),
        ])
        _call.reset_mock()

        # A non-list was returned
        _call.side_effect = ["test"]
        result = list(self.client.iter_call('SERVICE', 'METHOD', iter=True))
        self.assertEquals(["test"], result)
        _call.assert_has_calls([
            call('SERVICE', 'METHOD', iter=False, limit=100, offset=0),
        ])
        _call.reset_mock()

        # chunk=25, limit=30, offset=12
        _call.side_effect = [range(0, 25), range(25, 30)]
        result = list(self.client.iter_call(
            'SERVICE', 'METHOD', iter=True, limit=30, chunk=25, offset=12))
        self.assertEquals(range(30), result)
        _call.assert_has_calls([
            call('SERVICE', 'METHOD', iter=False, limit=25, offset=12),
            call('SERVICE', 'METHOD', iter=False, limit=5, offset=37),
        ])

        # Chunk size of 0 is invalid
        self.assertRaises(
            AttributeError,
            lambda: list(self.client.iter_call(
                'SERVICE', 'METHOD', iter=True, chunk=0)))

    def test_call_invalid_arguments(self):
        self.assertRaises(
            TypeError,
            self.client.call, 'SERVICE', 'METHOD', invalid_kwarg='invalid')


class UnauthenticatedAPIClient(unittest.TestCase):
    def setUp(self):
        self.client = SoftLayer.Client(endpoint_url="ENDPOINT")

    @patch.dict('os.environ', {'SL_USERNAME': '', 'SL_API_KEY': ''})
    def test_init(self):
        client = SoftLayer.Client()
        self.assertIsNone(client.auth)

    @patch('SoftLayer.API.Client.call')
    def test_authenticate_with_password(self, _call):
        _call.return_value = {
            'userId': 12345,
            'hash': 'TOKEN',
        }
        self.client.authenticate_with_password('USERNAME', 'PASSWORD')
        _call.assert_called_with(
            'User_Customer',
            'getPortalLoginToken',
            'USERNAME',
            'PASSWORD',
            None,
            None)
        self.assertIsNotNone(self.client.auth)
        self.assertEquals(self.client.auth.user_id, 12345)
        self.assertEquals(self.client.auth.auth_token, 'TOKEN')
