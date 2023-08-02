# coding: utf-8
import datetime
import json
import os
from collections import OrderedDict
from unittest import TestCase
from unittest.mock import call, patch

import pytest
from freezegun import freeze_time
from pycsob import __version__, conf, utils
from pycsob.client import CsobClient
from requests.exceptions import HTTPError
from testfixtures import LogCapture
from urllib3_mock import Responses

KEY_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'fixtures', 'test.key'))
PAY_ID = '34ae55eb69e2cBF'
USER_AGENT = "'py-csob/%s'" % __version__

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
        self.log_handler = LogCapture()
        self.addCleanup(self.log_handler.uninstall)

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
        self.log_handler.check((
            'pycsob', 'INFO', 'Pycsob request POST: https://gw.cz/echo/; Data: {"merchantId": "MERCHANT", '
            '"dttm": "20190502161426", "signature": '
            '"C9puGaxsYLEIazy04hVtCx5sMu8/eg6F2l17UfIUgCKFP4XvHIYA3xbIplbv1HbbQlGKgmw3FhD+FEYwq/E0bg=="}; '
            'Json: None; {}'), (
            'pycsob', 'DEBUG', "Pycsob request headers: {'content-type': 'application/json', 'user-agent': "
            + USER_AGENT + ", 'Content-Length': '157'}"), (
            'pycsob', 'INFO', 'Pycsob response: [200] {"dttm": "20190502161426", "resultCode": 0, '
            '"resultMessage": "OK", "signature": '
            '"hEyfa8OBR+eQIeqxBFB1SA9SHdhNkKBlM37IEizZ6z+2Bb4VSu1qldcpJEzARHOHJAgUOmwVXZC9v0MYcMg0TQ=="}'), (
            'pycsob', 'DEBUG', "Pycsob response headers: {'Content-Type': 'application/json'}"
        ))

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
        self.log_handler.check((
            'pycsob', 'INFO', 'Pycsob request GET: '
            'https://gw.cz/echo/MERCHANT/20190502161426/C9puGaxsYLEIazy04hVtCx5sMu8%2Feg6F2l17UfIUgCKFP4XvHIYA3xbIplbv'
            '1HbbQlGKgmw3FhD%2BFEYwq%2FE0bg%3D%3D; {}'), (
            'pycsob', 'DEBUG', "Pycsob request headers: {'content-type': 'application/json', 'user-agent': "
            + USER_AGENT + "}"), (
            'pycsob', 'INFO', 'Pycsob response: [200] {"dttm": "20190502161426", "resultCode": 0, '
            '"resultMessage": "OK", "signature": '
            '"hEyfa8OBR+eQIeqxBFB1SA9SHdhNkKBlM37IEizZ6z+2Bb4VSu1qldcpJEzARHOHJAgUOmwVXZC9v0MYcMg0TQ=="}'), (
            'pycsob', 'DEBUG', "Pycsob response headers: {'Content-Type': 'application/json'}"
        ))

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
        self.log_handler.check(
            ('pycsob', 'INFO', 'Pycsob request POST: https://gw.cz/payment/init; Data: {"merchantId": '
            '"MERCHANT", "orderNo": "666", "dttm": "20190502161426", "payOperation": '
            '"payment", "payMethod": "card", "totalAmount": "66600", "currency": "CZK", '
            '"closePayment": true, "returnUrl": "http://example.com", "returnMethod": '
            '"POST", "cart": [{"name": "N\\u011bjak\\u00fd popis", "quantity": 1, '
            '"amount": "66600"}], "language": "cs", "ttlSec": 600, "signature": '
            '"KMLqDJs+vSFqLaEG66i6MtkRZEL6U9HwqT3dPrYh237agzlkPnkXHHrCF2p+Sntzq/UWN03HfDhL5IHSsHvp6Q=="}; '
            'Json: None; {}'),
            ('pycsob', 'DEBUG', "Pycsob request headers: {'content-type': 'application/json', 'user-agent': "
            + USER_AGENT + ", 'Content-Length': '460'}"),
            ('pycsob', 'INFO', 'Pycsob response: [200] {"payId": "34ae55eb69e2cBF", "dttm": "20190502161426", '
            '"resultCode": 0, "resultMessage": "OK", "paymentStatus": 1, "signature": '
            '"Zd+PKspUEkrsEyxTmXAwrX3pgfS45Sg35dhMo5Oi0aoI8LoLs3dlyPS9vEXw80fxKyduAl5ws8D0Fu2mXLy9bA=="}'),
            ('pycsob', 'DEBUG', "Pycsob response headers: {'Content-Type': 'text/plain'}"),
        )

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
        self.log_handler.check(
            ('pycsob', 'INFO', 'Pycsob request POST: https://gw.cz/payment/init; Data: {"merchantId": "MERCHANT", '
            '"orderNo": "666", "dttm": "20190502161426", "payOperation": "payment", "payMethod": "card", '
            '"totalAmount": "2200000", "currency": "CZK", "closePayment": true, '
            '"returnUrl": "http://", "returnMethod": "POST", "cart": [{"name": "Order in sho XYZ", "quantity": 5, '
            '"amount": 12345}, {"name": "Postage", "quantity": 1, "amount": 0}], "language": "cs", "ttlSec": 600, '
            '"signature": "FcfTzD5ChQXyWAgBMZX+d/QOBbaGKXRusHwpiOaX+Aticygm1D8EzH+MtnMFq+Gp3dcQMTUg0bQKaCXfcQBeiA=="}; '
            'Json: None; {}'),
            ('pycsob', 'DEBUG', "Pycsob request headers: {'content-type': 'application/json', 'user-agent': "
            + USER_AGENT + ", 'Content-Length': '492'}"),
            ('pycsob', 'INFO', 'Pycsob response: [200] {"payId": "34ae55eb69e2cBF", "dttm": "20190502161426", '
            '"resultCode": 110, "resultMessage": "Invalid \'cart\' amounts, does not sum to totalAmount", '
            '"paymentStatus": 6, "signature": '
            '"GeQaDJ9nxY0f1g5T1j0JOgTY+fW/qvbtHRrXJ4Os6wWwjGOUmYy4sa8sHcOkffNfSJxmSZOoja/DFgC+fXnRbA=="}'),
            ('pycsob', 'DEBUG', "Pycsob response headers: {'Content-Type': 'text/plain'}")
        )

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
        self.log_handler.check(
            ('pycsob', 'INFO', 'Pycsob request GET: https://gw.cz/payment/status/MERCHANT/34ae55eb69e2cBF/201905021614'
            '26/hi0fi1sF0BL0SLWagZ9QJ4aLe7B3I0MN0rr0ocRb75ZP7wZunTLdrbFkALs1rUQYe1sJaKaoo%2B%2BoVs6grd%2F0WA%3D%3D;'
            ' {}'),
            ('pycsob', 'DEBUG', "Pycsob request headers: {'content-type': 'application/json', 'user-agent': "
            + USER_AGENT + "}"),
            ('pycsob', 'INFO', 'Pycsob response: [200] {"payId": "34ae55eb69e2cBF", "dttm": "20190502161426", '
            '"resultCode": 110, "resultMessage": "OK", "paymentStatus": 7, "authCode": "F7A23E", "signature": '
            '"FFXfpqhazvXVKEMckHw+Y2tRDespTUp62NQ6kAwA4T0LNT6LDKj70d5XBJrrx3XNs92JGUT6wIJZR25MFmibFA==", '
            '"extensions": [{"extension": "maskClnRP", "dttm": "20190502161426", "maskedCln": "****1234", '
            '"expiration": "12/20", "longMaskedCln": "PPPPPP****XXXX", "signature": '
            '"lDm8A+GvTbozSinFf1b3mqjjhXa7eZrOd6F9HQ0hE4eEozk7HdBWyNOPp/OieKofQFURDwzf8gJqQQT01xSD3w=="}]}'),
            ('pycsob', 'DEBUG', "Pycsob response headers: {'Content-Type': 'text/plain'}")
        )

    @responses.activate
    def test_http_status_raised(self):
        responses.add(responses.POST, '/echo/', status=500)
        with pytest.raises(HTTPError) as excinfo:
            self.c.echo(method='POST')
        assert '500 Server Error' in str(excinfo.value)
        self.log_handler.check(
            ('pycsob', 'INFO', 'Pycsob request POST: https://gw.cz/echo/; Data: {"merchantId": "MERCHANT", '
            '"dttm": "20190502161426", "signature": '
            '"C9puGaxsYLEIazy04hVtCx5sMu8/eg6F2l17UfIUgCKFP4XvHIYA3xbIplbv1HbbQlGKgmw3FhD+FEYwq/E0bg=="}; '
            'Json: None; {}'),
            ('pycsob', 'DEBUG', "Pycsob request headers: {'content-type': 'application/json', 'user-agent': "
            + USER_AGENT + ", 'Content-Length': '157'}"),
            ('pycsob', 'INFO', 'Pycsob response: [500] '),
            ('pycsob', 'DEBUG', "Pycsob response headers: {'Content-Type': 'text/plain'}")
        )

    def test_gateway_return_retype(self):
        resp_payload = utils.mk_payload(KEY_PATH, pairs=(
            ('resultCode', str(conf.RETURN_CODE_PARAM_INVALID)),
            ('paymentStatus', str(conf.PAYMENT_STATUS_WAITING)),
            ('authCode', 'F7A23E')
        ))
        r = self.c.gateway_return(dict(resp_payload))
        assert type(r['paymentStatus']) == int
        assert type(r['resultCode']) == int
        self.log_handler.check()

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
        self.log_handler.check()

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
        self.log_handler.check(
            ('pycsob', 'INFO', 'Pycsob request POST: https://gw.cz/payment/init; Data: {"merchantId": "MERCHANT", '
            '"orderNo": "666", "dttm": "20190502161426", "payOperation": "payment", "payMethod": "card", '
            '"totalAmount": "66600", "currency": "CZK", "closePayment": true, "returnUrl": "http://example.com", '
            '"returnMethod": "POST", "cart": [{"name": "Fooo", "quantity": 1, "amount": "66600"}], '
            '"merchantData": "Rm9v", "language": "cs", "ttlSec": 600, "signature": '
            '"a5jKBePOpjgX0CjUkKFTe3UzedHzFgrvSsVf3NnSZ7uzuFyBIs5QEVxN9QZ8y7LKKRiigEzU8r6GZ3MiEFf9RA=="}; '
            'Json: None; {}'),
            ('pycsob', 'DEBUG', "Pycsob request headers: {'content-type': 'application/json', "
            "'user-agent': " + USER_AGENT + ", 'Content-Length': '466'}"),
            ('pycsob', 'INFO', 'Pycsob response: [200] {"payId": "34ae55eb69e2cBF", "dttm": "20190502161426", '
            '"resultCode": 0, "resultMessage": "OK", "paymentStatus": 1, "signature": '
            '"Zd+PKspUEkrsEyxTmXAwrX3pgfS45Sg35dhMo5Oi0aoI8LoLs3dlyPS9vEXw80fxKyduAl5ws8D0Fu2mXLy9bA=="}'),
            ('pycsob', 'DEBUG', "Pycsob response headers: {'Content-Type': 'text/plain'}")
        )

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
        self.log_handler.check()

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
        self.log_handler.check(
            ('pycsob', 'INFO', 'Pycsob request POST: https://gw.cz/payment/init; Data: {"merchantId": "MERCHANT", '
            '"orderNo": "666", "dttm": "20190502161426", "payOperation": "payment", "payMethod": "card", '
            '"totalAmount": "66600", "currency": "CZK", "closePayment": true, "returnUrl": "http://example.com", '
            '"returnMethod": "POST", "cart": [{"name": "Fooo", "quantity": 1, "amount": "66600"}], "language": "cs", '
            '"ttlSec": 600, "signature": '
            '"XH4RdW0dXrDh81dUHNKMrF+LVfZZtIOKJXzVUSxB/RVKK2Sb59SJvl8jonujNZC78GJkr5THLCbnMJNUfXpQag=="}; '
            'Json: None; {}'),
            ('pycsob', 'DEBUG', "Pycsob request headers: {'content-type': 'application/json', 'user-agent': "
            + USER_AGENT + ", 'Content-Length': '442'}"),
            ('pycsob', 'INFO', 'Pycsob response: [200] {"payId": "34ae55eb69e2cBF", "dttm": "20190502161426", '
            '"resultCode": 0, "resultMessage": "OK", "paymentStatus": 1, "signature": '
            '"Zd+PKspUEkrsEyxTmXAwrX3pgfS45Sg35dhMo5Oi0aoI8LoLs3dlyPS9vEXw80fxKyduAl5ws8D0Fu2mXLy9bA=="}'),
            ('pycsob', 'DEBUG', "Pycsob response headers: {'Content-Type': 'text/plain'}")
        )

    @responses.activate
    def test_payment_init_custom_payment(self):
        resp_url = '/payment/init'
        resp_payload = utils.mk_payload(KEY_PATH, pairs=(
            ('payId', PAY_ID),
            ('dttm', utils.dttm()),
            ('resultCode', conf.RETURN_CODE_OK),
            ('resultMessage', 'OK'),
            ('paymentStatus', 1),
            ('customerCode', 'E61EC8'),
        ))
        responses.add(responses.POST, resp_url, body=json.dumps(resp_payload), status=200)
        out = self.c.payment_init(order_no=666, total_amount='66600', return_url='http://example.com',
                                  description='Fooo', pay_operation='customPayment', custom_expiry='20190531120000'
                                  ).payload

        assert out['paymentStatus'] == conf.PAYMENT_STATUS_INIT
        assert out['resultCode'] == conf.RETURN_CODE_OK
        assert len(responses.calls) == 1
        self.log_handler.check(
            ('pycsob', 'INFO', 'Pycsob request POST: https://gw.cz/payment/init; Data: {"merchantId": "MERCHANT", '
            '"orderNo": "666", "dttm": "20190502161426", "payOperation": "customPayment", "payMethod": "card", '
            '"totalAmount": "66600", "currency": "CZK", "closePayment": true, "returnUrl": "http://example.com", '
            '"returnMethod": "POST", "cart": [{"name": "Fooo", "quantity": 1, "amount": "66600"}], "language": "cs", '
            '"ttlSec": 600, "customExpiry": "20190531120000", "signature": '
            '"H+eKbex5KdHUtZ/fxB5vfMlgEkH3H6RfDj3oR9i/R/8HYInmyP0tz6+lqzF8EztHmpA/vxevW9qvNTgV535eZw=="}; '
            'Json: None; {}'),
            ('pycsob', 'DEBUG', "Pycsob request headers: {'content-type': 'application/json', 'user-agent': "
            + USER_AGENT + ", 'Content-Length': '482'}"),
            ('pycsob', 'INFO', 'Pycsob response: [200] {"payId": "34ae55eb69e2cBF", "dttm": "20190502161426", '
            '"resultCode": 0, "resultMessage": "OK", "paymentStatus": 1, "customerCode": "E61EC8", "signature": '
            '"KmqB9foNOz7aJuyujNcHDpD7rmPZzkN/AePWw62h5xYxowrd1Jb5o6JdF1S76USHaPn4yc+iOIM+pw601l3PxQ=="}'),
            ('pycsob', 'DEBUG', "Pycsob response headers: {'Content-Type': 'text/plain'}")
        )

    @responses.activate
    def test_button_init(self):
        resp_payload = utils.mk_payload(KEY_PATH, pairs=(
            ('payId', PAY_ID),
            ('dttm', utils.dttm()),
            ('resultCode', conf.RETURN_CODE_OK),
            ('resultMessage', 'OK'),
        ))
        responses.add(responses.POST, '/button/init', body=json.dumps(resp_payload), status=200)
        out = self.c.button_init(PAY_ID, 10000, '127.0.0.1', 'https://web.foo/').payload
        self.assertEqual(out, OrderedDict([
            ('payId', '34ae55eb69e2cBF'),
            ('dttm', self.dttm),
            ('resultCode', 0),
            ('resultMessage', 'OK'),
            ('dttime', self.dttime),
        ]))
        self.log_handler.check(
            ('pycsob', 'INFO', 'Pycsob request POST: https://gw.cz/button/init; Data: {"merchantId": '
             '"MERCHANT", "orderNo": "34ae55eb69e2cBF", "dttm": "20190502161426", '
             '"clientIp": "127.0.0.1", "totalAmount": 10000, "currency": "CZK", '
             '"returnUrl": "https://web.foo/", "returnMethod": "POST", "brand": "csob", '
             '"language": "cs", "signature": '
             '"D3rppiWK7zp1B9ra94cxQczOwfUVrRnyd8oLRTd4guC+qXALRXKHgqc7AVPnM3kuMG6fRY9B4X9+10n/603C9Q=="}; '
             'Json: None; {}'),
            ('pycsob', 'DEBUG', "Pycsob request headers: {'content-type': 'application/json', 'user-agent': "
             + USER_AGENT + ", 'Content-Length': '345'}"),
            ('pycsob', 'INFO', 'Pycsob response: [200] {"payId": "34ae55eb69e2cBF", "dttm": '
             '"20190502161426", "resultCode": 0, "resultMessage": "OK", "signature": '
             '"mMvfLq/SzhagYKkJp/PnQ+Y9zoMJIGt1OznlxQLqq+gsyhOjUd4ghDtJtFt8bQkpr+jwj6kd/y8R5RyxZ7qgag=="}'),
            ('pycsob', 'DEBUG', "Pycsob response headers: {'Content-Type': 'text/plain'}")
        )

    def test_dttm_decode(self):
        self.assertEqual(utils.dttm_decode("20190502161426"), self.dttime)

    @responses.activate
    def test_description_strip(self):
        resp_url = '/payment/init'
        resp_payload = utils.mk_payload(KEY_PATH, pairs=(
            ('payId', PAY_ID),
            ('dttm', utils.dttm()),
            ('resultCode', conf.RETURN_CODE_OK),
            ('resultMessage', 'OK'),
            ('paymentStatus', 1),
        ))
        responses.add(responses.POST, resp_url, body=json.dumps(resp_payload), status=200)

        with patch('pycsob.utils.mk_payload', return_value=resp_payload) as mock_mk_payload:
            self.c.payment_init(42, '100', 'http://example.com', 'Konference Internet a Technologie 19')

        self.assertEqual(mock_mk_payload.mock_calls, [
            call(KEY_PATH, pairs=(
                ('merchantId', 'MERCHANT'),
                ('orderNo', '42'),
                ('dttm', '20190502161426'),
                ('payOperation', 'payment'),
                ('payMethod', 'card'),
                ('totalAmount', '100'),
                ('currency', 'CZK'),
                ('closePayment', True),
                ('returnUrl', 'http://example.com'),
                ('returnMethod', 'POST'),
                ('cart', [OrderedDict([
                    ('name', 'Konference Internet'),
                    ('quantity', 1),
                    ('amount', '100')])]),
                ('customer', None),
                ('order', None),
                ('merchantData', None),
                ('customerId', None),
                ('language', 'cs'),
                ('ttlSec', 600),
                ('logoVersion', None),
                ('colorSchemeVersion', None),
                ('customExpiry', None),
            ))
        ])
        self.log_handler.check(
            ('pycsob', 'INFO', 'Pycsob request POST: https://gw.cz/payment/init; Data: {"payId": "34ae55eb69e2cBF", '
            '"dttm": "20190502161426", "resultCode": 0, "resultMessage": "OK", "paymentStatus": 1, "signature": '
            '"Zd+PKspUEkrsEyxTmXAwrX3pgfS45Sg35dhMo5Oi0aoI8LoLs3dlyPS9vEXw80fxKyduAl5ws8D0Fu2mXLy9bA=="}; '
            'Json: None; {}'),
            ('pycsob', 'DEBUG', "Pycsob request headers: {'content-type': 'application/json', 'user-agent': "
            + USER_AGENT + ", 'Content-Length': '219'}"),
            ('pycsob', 'INFO', 'Pycsob response: [200] {"payId": "34ae55eb69e2cBF", "dttm": "20190502161426", '
            '"resultCode": 0, "resultMessage": "OK", "paymentStatus": 1, "signature": '
            '"Zd+PKspUEkrsEyxTmXAwrX3pgfS45Sg35dhMo5Oi0aoI8LoLs3dlyPS9vEXw80fxKyduAl5ws8D0Fu2mXLy9bA=="}'),
            ('pycsob', 'DEBUG', "Pycsob response headers: {'Content-Type': 'text/plain'}")
        )
