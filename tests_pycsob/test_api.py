# coding: utf-8
import os
import datetime
import json
import pytest
from collections import OrderedDict
from freezegun import freeze_time
from requests.exceptions import HTTPError
from unittest import TestCase
from urllib3_mock import Responses

from pycsob import conf, utils
from pycsob.client import CsobClient

KEY_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'fixtures', 'test.key'))
PAY_ID = '34ae55eb69e2cBF'

responses = Responses(package='requests.packages.urllib3')


@freeze_time("2019-05-02 16:14:26")
class CsobClientTests(TestCase):

    dttm = "20190502161426"
    dttime = datetime.datetime(2019, 5, 2, 16, 14, 26)

    def setUp(self):
        self.c = CsobClient(merchant_id='MERCHANT',
                            base_url='https://gw.cz',
                            private_key_file=KEY_PATH,
                            csob_pub_key_file=KEY_PATH)

    @responses.activate
    def test_echo_post(self):
        resp_payload = utils.mk_payload(KEY_PATH, pairs=(
            ('dttm', utils.dttm()),
            ('resultCode', conf.RETURN_CODE_OK),
            ('resultMessage', 'OK'),
        ))
        responses.add(responses.POST, '/echo/', body=json.dumps(resp_payload),
                      status=200, content_type='application/json')
        out = self.c.echo().payload
        self.assertEqual(out['dttm'], self.dttm)
        self.assertEqual(out['dttime'], self.dttime)
        self.assertEqual(out['resultCode'], conf.RETURN_CODE_OK)

    @responses.activate
    def test_echo_get(self):
        payload = utils.mk_payload(KEY_PATH, pairs=(
            ('merchantId', self.c.merchant_id),
            ('dttm', utils.dttm()),
        ))
        resp_payload = utils.mk_payload(KEY_PATH, pairs=(
            ('dttm', utils.dttm()),
            ('resultCode', conf.RETURN_CODE_OK),
            ('resultMessage', 'OK'),
        ))
        url = utils.mk_url('/', 'echo/', payload)
        responses.add(responses.GET, url, body=json.dumps(resp_payload),
                      status=200, content_type='application/json')
        out = self.c.echo(method='GET').payload
        self.assertEqual(out['dttm'], self.dttm)
        self.assertEqual(out['dttime'], self.dttime)
        self.assertEqual(out['resultCode'], conf.RETURN_CODE_OK)

    def test_sign_message(self):
        msg = 'Příliš žluťoučký kůň úpěl ďábelské ódy.'
        payload = utils.mk_payload(KEY_PATH, pairs=(
            ('merchantId', self.c.merchant_id),
            ('dttm', utils.dttm()),
            ('description', msg)
        ))
        assert payload['description'] == msg
        sig = payload.pop('signature')
        assert utils.verify(payload, sig, KEY_PATH)

    @responses.activate
    def test_payment_init_success(self):
        resp_url = '/payment/init'
        resp_payload = utils.mk_payload(KEY_PATH, pairs=(
            ('payId', PAY_ID),
            ('dttm', utils.dttm()),
            ('resultCode', conf.RETURN_CODE_OK),
            ('resultMessage', 'OK'),
            ('paymentStatus', 1)
        ))
        responses.add(responses.POST, resp_url, body=json.dumps(resp_payload), status=200)
        out = self.c.payment_init(order_no=666, total_amount='66600', return_url='http://example.com',
                                  description='Nějaký popis').payload

        assert out['paymentStatus'] == conf.PAYMENT_STATUS_INIT
        assert out['resultCode'] == conf.RETURN_CODE_OK
        assert len(responses.calls) == 1

    @responses.activate
    def test_payment_init_bad_cart(self):
        cart = [
            OrderedDict([
                ('name', 'Order in sho XYZ'),
                ('quantity', 5),
                ('amount', 12345),
            ]),
            OrderedDict([
                ('name', 'Postage'),
                ('quantity', 1),
                ('amount', 0),
            ])
        ]
        resp_payload = utils.mk_payload(KEY_PATH, pairs=(
            ('payId', PAY_ID),
            ('dttm', utils.dttm()),
            ('resultCode', conf.RETURN_CODE_PARAM_INVALID),
            ('resultMessage', "Invalid 'cart' amounts, does not sum to totalAmount"),
            ('paymentStatus', conf.PAYMENT_STATUS_REJECTED)
        ))
        resp_url = '/payment/init'
        responses.add(responses.POST, resp_url, body=json.dumps(resp_payload), status=200)
        out = self.c.payment_init(order_no=666, total_amount='2200000', return_url='http://',
                                  description='X', cart=cart).payload

        assert out['paymentStatus'] == conf.PAYMENT_STATUS_REJECTED
        assert out['resultCode'] == conf.RETURN_CODE_PARAM_INVALID

    @responses.activate
    def test_payment_status_extension(self):

        payload = utils.mk_payload(KEY_PATH, pairs=(
            ('merchantId', self.c.merchant_id),
            ('payId', PAY_ID),
            ('dttm', utils.dttm()),
        ))

        resp_payload = utils.mk_payload(KEY_PATH, pairs=(
            ('payId', PAY_ID),
            ('dttm', utils.dttm()),
            ('resultCode', conf.RETURN_CODE_PARAM_INVALID),
            ('resultMessage', "OK"),
            ('paymentStatus', conf.PAYMENT_STATUS_WAITING),
            ('authCode', 'F7A23E')
        ))
        ext_payload = utils.mk_payload(KEY_PATH, pairs=(
            ('extension', 'maskClnRP'),
            ('dttm', utils.dttm()),
            ('maskedCln', '****1234'),
            ('expiration', '12/20'),
            ('longMaskedCln', 'PPPPPP****XXXX')
        ))
        resp_payload['extensions'] = [ext_payload]
        resp_url = utils.mk_url('/', 'payment/status/', payload)
        responses.add(responses.GET, resp_url, body=json.dumps(resp_payload), status=200)
        out = self.c.payment_status(PAY_ID)

        assert hasattr(out, 'extensions')
        assert len(out.extensions) == 1
        assert out.extensions[0]['longMaskedCln'] == ext_payload['longMaskedCln']

    @responses.activate
    def test_http_status_raised(self):
        responses.add(responses.POST, '/echo/', status=500)
        with pytest.raises(HTTPError) as excinfo:
            self.c.echo(method='POST')
        assert '500 Server Error' in str(excinfo.value)

    def test_gateway_return_retype(self):
        resp_payload = utils.mk_payload(KEY_PATH, pairs=(
            ('resultCode', str(conf.RETURN_CODE_PARAM_INVALID)),
            ('paymentStatus', str(conf.PAYMENT_STATUS_WAITING)),
            ('authCode', 'F7A23E')
        ))
        r = self.c.gateway_return(dict(resp_payload))
        assert type(r['paymentStatus']) == int
        assert type(r['resultCode']) == int

    def test_gateway_return_merchant_data(self):
        resp_payload = utils.mk_payload(KEY_PATH, pairs=(
            ('resultCode', str(conf.RETURN_CODE_PARAM_INVALID)),
            ('paymentStatus', str(conf.PAYMENT_STATUS_WAITING)),
            ('merchantData', 'Rm9v')
        ))
        r = self.c.gateway_return(dict(resp_payload))
        self.assertEqual(r, OrderedDict([
            ('resultCode', 110),
            ('paymentStatus', 7),
            ('merchantData', b'Foo')
        ]))

    def test_get_card_provider(self):
        fn = utils.get_card_provider

        assert fn('423451****111')[0] == conf.CARD_PROVIDER_VISA

    @responses.activate
    def test_payment_init_with_merchant_data(self):
        resp_url = '/payment/init'
        resp_payload = utils.mk_payload(KEY_PATH, pairs=(
            ('payId', PAY_ID),
            ('dttm', utils.dttm()),
            ('resultCode', conf.RETURN_CODE_OK),
            ('resultMessage', 'OK'),
            ('paymentStatus', 1),
        ))
        responses.add(responses.POST, resp_url, body=json.dumps(resp_payload), status=200)
        out = self.c.payment_init(order_no=666, total_amount='66600', return_url='http://example.com',
                                  description='Fooo', merchant_data=b'Foo').payload

        assert out['paymentStatus'] == conf.PAYMENT_STATUS_INIT
        assert out['resultCode'] == conf.RETURN_CODE_OK
        assert len(responses.calls) == 1

    @responses.activate
    def test_payment_init_with_too_long_merchant_data(self):
        resp_url = '/payment/init'
        resp_payload = utils.mk_payload(KEY_PATH, pairs=(
            ('payId', PAY_ID),
            ('dttm', utils.dttm()),
            ('resultCode', conf.RETURN_CODE_OK),
            ('resultMessage', 'OK'),
            ('paymentStatus', 1),
        ))
        responses.add(responses.POST, resp_url, body=json.dumps(resp_payload), status=200)
        with self.assertRaisesRegex(ValueError, 'Merchant data length encoded to BASE64 is over 255 chars'):
            self.c.payment_init(order_no=666, total_amount='66600', return_url='http://example.com',
                                description='Fooo', merchant_data=b'Foo' * 80).payload

    @responses.activate
    def test_payment_init_language_with_locale_cs(self):
        resp_url = '/payment/init'
        resp_payload = utils.mk_payload(KEY_PATH, pairs=(
            ('payId', PAY_ID),
            ('dttm', utils.dttm()),
            ('resultCode', conf.RETURN_CODE_OK),
            ('resultMessage', 'OK'),
            ('paymentStatus', 1),
        ))
        responses.add(responses.POST, resp_url, body=json.dumps(resp_payload), status=200)
        out = self.c.payment_init(order_no=666, total_amount='66600', return_url='http://example.com',
                                  description='Fooo', language='cs_CZ.utf8').payload

        assert out['paymentStatus'] == conf.PAYMENT_STATUS_INIT
        assert out['resultCode'] == conf.RETURN_CODE_OK
        assert len(responses.calls) == 1

    @responses.activate
    def test_button(self):
        resp_url = '/payment/button/'
        resp_payload = utils.mk_payload(KEY_PATH, pairs=(
            ('payId', PAY_ID),
            ('dttm', utils.dttm()),
            ('resultCode', conf.RETURN_CODE_OK),
            ('resultMessage', 'OK'),
        ))
        responses.add(responses.POST, resp_url, body=json.dumps(resp_payload), status=200)
        out = self.c.button(PAY_ID, 'csob').payload
        self.assertEqual(out, OrderedDict([
            ('payId', '34ae55eb69e2cBF'),
            ('dttm', self.dttm),
            ('resultCode', 0),
            ('resultMessage', 'OK'),
            ('dttime', self.dttime),
        ]))

    def test_dttm_decode(self):
        self.assertEqual(utils.dttm_decode("20190502161426"), self.dttime)
