# coding: utf-8
import os
import datetime
import json
import pytest
from testfixtures import LogCapture
from collections import OrderedDict
from freezegun import freeze_time
from requests.exceptions import HTTPError
from unittest import TestCase
from unittest.mock import call, patch
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
            '"J7By3O+CBZeIsOFganhzQhXpB54ijT9xqD/lZSTsU6aty9B1DF7fSaQqYNaV8dBY7fT1C9oK06y7Zbf6jMHmZQ=="}; '
            'Json: None; {}'), (
            'pycsob', 'DEBUG', "Pycsob request headers: {'content-type': 'application/json', 'user-agent': "
            "'py-csob/0.7.0', 'Content-Length': '157'}"), (
            'pycsob', 'INFO', 'Pycsob response: [200] {"dttm": "20190502161426", "resultCode": 0, '
            '"resultMessage": "OK", "signature": '
            '"fHau/UrTzN6RtU3hLwRO7jkLHfxJMBjHOuJIQih6rDRfNWEnehpBmfbvCAjwpHiisr0Od5OhrZaFj/24ohbMTQ=="}'), (
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
            'https://gw.cz/echo/MERCHANT/20190502161426/J7By3O%2BCBZeIsOFganhzQhXpB54ijT9xqD%2FlZSTsU6aty9B1DF7fSaQqYN'
            'aV8dBY7fT1C9oK06y7Zbf6jMHmZQ%3D%3D; {}'), (
            'pycsob', 'DEBUG', "Pycsob request headers: {'content-type': 'application/json', 'user-agent': "
            "'py-csob/0.7.0'}"), (
            'pycsob', 'INFO', 'Pycsob response: [200] {"dttm": "20190502161426", "resultCode": 0, '
            '"resultMessage": "OK", "signature": '
            '"fHau/UrTzN6RtU3hLwRO7jkLHfxJMBjHOuJIQih6rDRfNWEnehpBmfbvCAjwpHiisr0Od5OhrZaFj/24ohbMTQ=="}'), (
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
        self.log_handler.check((
            'pycsob', 'INFO', 'Pycsob request POST: https://gw.cz/payment/init; Data: {"merchantId": '
            '"MERCHANT", "orderNo": "666", "dttm": "20190502161426", "payOperation": '
            '"payment", "payMethod": "card", "totalAmount": "66600", "currency": "CZK", '
            '"closePayment": true, "returnUrl": "http://example.com", "returnMethod": '
            '"POST", "cart": [{"name": "N\\u011bjak\\u00fd popis", "quantity": 1, '
            '"amount": "66600"}], "description": "N\\u011bjak\\u00fd popis", "language": '
            '"CZ", "ttlSec": 600, "signature": '
            '"f233WiVk3qr2z4re0uVJUDwNDP0Q57cBHbXGpoMZGE3wUAlpYys1z03EIKIPj5A6nTPAANfNmqRQrormcLvf7A=="}; '
            'Json: None; {}'), (
            'pycsob', 'DEBUG', "Pycsob request headers: {'content-type': 'application/json', 'user-agent': "
            "'py-csob/0.7.0', 'Content-Length': '501'}"), (
            'pycsob', 'INFO', 'Pycsob response: [200] {"payId": "34ae55eb69e2cBF", "dttm": "20190502161426", '
            '"resultCode": 0, "resultMessage": "OK", "paymentStatus": 1, "signature": '
            '"DtDHJocYFvaIJWGzGL8ETIHNNgaxnSMQHAcUm7m0sF4CQBYEYAMdbnAZUq1wOHwf9sxfOnAJyfCriYW4429u3g=="}'), (
            'pycsob', 'DEBUG', "Pycsob response headers: {'Content-Type': 'text/plain'}"
        ))

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
        self.log_handler.check((
            'pycsob', 'INFO', 'Pycsob request POST: https://gw.cz/payment/init; Data: {"merchantId": '
            '"MERCHANT", "orderNo": "666", "dttm": "20190502161426", "payOperation": '
            '"payment", "payMethod": "card", "totalAmount": "2200000", "currency": '
            '"CZK", "closePayment": true, "returnUrl": "http://", "returnMethod": '
            '"POST", "cart": [{"name": "Order in sho XYZ", "quantity": 5, "amount": '
            '12345}, {"name": "Postage", "quantity": 1, "amount": 0}], "description": '
            '"X", "language": "CZ", "ttlSec": 600, "signature": '
            '"W3n6RcmXskgGeHXd7+VGcATu34xo2N2yOiINMwcAMLnx+D5aYwezg7UNY+MTZjc7jxnf8YOfVVhy8IWOVsIyJg=="}; '
            'Json: None; {}'), (
            'pycsob', 'DEBUG', "Pycsob request headers: {'content-type': 'application/json', 'user-agent': "
            "'py-csob/0.7.0', 'Content-Length': '512'}"), (
            'pycsob', 'INFO', 'Pycsob response: [200] {"payId": "34ae55eb69e2cBF", "dttm": "20190502161426", '
            '"resultCode": 110, "resultMessage": "Invalid \'cart\' amounts, does not sum '
            'to totalAmount", "paymentStatus": 6, "signature": '
            '"aYw7oHwQh7B/wG5/sqKzw7nZWDXH6++dkp3kbPp1U8MWK1dLCsT/BSY1CvDVG234yMBu1LFprSk+g85VJXV26w=="}'), (
            'pycsob', 'DEBUG', "Pycsob response headers: {'Content-Type': 'text/plain'}"
        ))

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
        self.log_handler.check((
            'pycsob', 'INFO', 'Pycsob request GET: '
            'https://gw.cz/payment/status/MERCHANT/34ae55eb69e2cBF/20190502161426/'
            'eAmtHAmMuCx4kQhW6s9fh3AhaRrxweMobxXamNHu8fg3oI78A2qndsHkGPkR1rq8GZ2BVfvgy0E4PiVxomgsSg%3D%3D; {}'), (
            'pycsob', 'DEBUG', "Pycsob request headers: {'content-type': 'application/json', 'user-agent': "
            "'py-csob/0.7.0'}"), (
            'pycsob', 'INFO', 'Pycsob response: [200] {"payId": "34ae55eb69e2cBF", "dttm": "20190502161426", '
            '"resultCode": 110, "resultMessage": "OK", "paymentStatus": 7, "authCode": '
            '"F7A23E", "signature": '
            '"bAtRVLOyNbXdt5YyVlBzCuEVEynmWMFz2bpH9hHYcFDq9StcrvEmyKlmlzyrZdEfWLASKm2WgYZ+nYdYdeyVcg==", '
            '"extensions": [{"extension": "maskClnRP", "dttm": "20190502161426", '
            '"maskedCln": "****1234", "expiration": "12/20", "longMaskedCln": '
            '"PPPPPP****XXXX", "signature": '
            '"mgVUxOqdUG1/RfD5A/2b3bNllmEidssFaJaH+c/pTVxTxil934gWddi1EgTsidbaQN0qgG+MwlRoQXjQIoUSWw=="}]}'), (
            'pycsob', 'DEBUG', "Pycsob response headers: {'Content-Type': 'text/plain'}"
        ))

    @responses.activate
    def test_http_status_raised(self):
        responses.add(responses.POST, '/echo/', status=500)
        with pytest.raises(HTTPError) as excinfo:
            self.c.echo(method='POST')
        assert '500 Server Error' in str(excinfo.value)
        self.log_handler.check((
            'pycsob', 'INFO', 'Pycsob request POST: https://gw.cz/echo/; Data: {"merchantId": "MERCHANT", '
            '"dttm": "20190502161426", "signature": '
            '"J7By3O+CBZeIsOFganhzQhXpB54ijT9xqD/lZSTsU6aty9B1DF7fSaQqYNaV8dBY7fT1C9oK06y7Zbf6jMHmZQ=="}; '
            'Json: None; {}'), (
            'pycsob', 'DEBUG', "Pycsob request headers: {'content-type': 'application/json', 'user-agent': "
            "'py-csob/0.7.0', 'Content-Length': '157'}"), (
            'pycsob', 'INFO', 'Pycsob response: [500] '), (
            'pycsob', 'DEBUG', "Pycsob response headers: {'Content-Type': 'text/plain'}"
        ))

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
        self.log_handler.check((
            'pycsob', 'INFO', 'Pycsob request POST: https://gw.cz/payment/init; Data: {"merchantId": '
            '"MERCHANT", "orderNo": "666", "dttm": "20190502161426", "payOperation": '
            '"payment", "payMethod": "card", "totalAmount": "66600", "currency": "CZK", '
            '"closePayment": true, "returnUrl": "http://example.com", "returnMethod": '
            '"POST", "cart": [{"name": "Fooo", "quantity": 1, "amount": "66600"}], '
            '"description": "Fooo", "merchantData": "Rm9v", "language": "CZ", "ttlSec": '
            '600, "signature": '
            '"G5xVS2YCgiM58ooXK2FMJIinwoWHk65yMtI/CaZ6kORxHaG5QWQntGtYkocFH7S6ce4a3bsKoMbMMrdC1cYZsg=="}; '
            'Json: None; {}'), (
            'pycsob', 'DEBUG', "Pycsob request headers: {'content-type': 'application/json', 'user-agent': "
            "'py-csob/0.7.0', 'Content-Length': '489'}"), (
            'pycsob', 'INFO', 'Pycsob response: [200] {"payId": "34ae55eb69e2cBF", "dttm": "20190502161426", '
            '"resultCode": 0, "resultMessage": "OK", "paymentStatus": 1, "signature": '
            '"DtDHJocYFvaIJWGzGL8ETIHNNgaxnSMQHAcUm7m0sF4CQBYEYAMdbnAZUq1wOHwf9sxfOnAJyfCriYW4429u3g=="}'), (
            'pycsob', 'DEBUG', "Pycsob response headers: {'Content-Type': 'text/plain'}"
        ))

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
        self.log_handler.check((
            'pycsob', 'INFO', 'Pycsob request POST: https://gw.cz/payment/init; Data: {"merchantId": '
            '"MERCHANT", "orderNo": "666", "dttm": "20190502161426", "payOperation": '
            '"payment", "payMethod": "card", "totalAmount": "66600", "currency": "CZK", '
            '"closePayment": true, "returnUrl": "http://example.com", "returnMethod": '
            '"POST", "cart": [{"name": "Fooo", "quantity": 1, "amount": "66600"}], '
            '"description": "Fooo", "language": "CZ", "ttlSec": 600, "signature": '
            '"HJvyHAgAOJcoTO43OS6I68lbJI2tLWv2aPhx+/XMO1Xn4HJkL7UTflvMFjM+LLynYqRV4FxofMu6QqtO52ZfYg=="}; '
            'Json: None; {}'), (
            'pycsob', 'DEBUG', "Pycsob request headers: {'content-type': 'application/json', 'user-agent': "
            "'py-csob/0.7.0', 'Content-Length': '465'}"), (
            'pycsob', 'INFO', 'Pycsob response: [200] {"payId": "34ae55eb69e2cBF", "dttm": "20190502161426", '
            '"resultCode": 0, "resultMessage": "OK", "paymentStatus": 1, "signature": '
            '"DtDHJocYFvaIJWGzGL8ETIHNNgaxnSMQHAcUm7m0sF4CQBYEYAMdbnAZUq1wOHwf9sxfOnAJyfCriYW4429u3g=="}'), (
            'pycsob', 'DEBUG', "Pycsob response headers: {'Content-Type': 'text/plain'}"
        ))

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
        self.log_handler.check((
            'pycsob', 'INFO', 'Pycsob request POST: https://gw.cz/payment/button/; Data: {"merchantId": '
            '"MERCHANT", "payId": "34ae55eb69e2cBF", "brand": "csob", "dttm": '
            '"20190502161426", "signature": '
            '"XN/VXyQsLgQtim+gCLO9bSbaHapaqOaSqUJXPsY1qA1gpb9jY2hgcu4snE+qGD5O6C+rn2rMXg/Hz7zYS/eJHw=="}; '
            'Json: None; {}'), (
            'pycsob', 'DEBUG', "Pycsob request headers: {'content-type': 'application/json', 'user-agent': "
            "'py-csob/0.7.0', 'Content-Length': '202'}"), (
            'pycsob', 'INFO', 'Pycsob response: [200] {"payId": "34ae55eb69e2cBF", "dttm": "20190502161426", '
            '"resultCode": 0, "resultMessage": "OK", "signature": '
            '"ar0NFFzpbXAnjBjzpLg892h/7iDkn8AKXr+0a5oK4oH1cQtvaSaa6nccXJljWinkwQ8yAkIAg14JxZnQDYFHXw=="}'), (
            'pycsob', 'DEBUG', "Pycsob response headers: {'Content-Type': 'text/plain'}"
        ))

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
                ('description', 'Konference Internet a Technologie 19'),
                ('merchantData', None),
                ('customerId', None),
                ('language', 'CZ'),
                ('ttlSec', 600),
                ('logoVersion', None),
                ('colorSchemeVersion', None),
            ))
        ])
        self.log_handler.check((
            'pycsob', 'INFO', 'Pycsob request POST: https://gw.cz/payment/init; Data: {"payId": '
            '"34ae55eb69e2cBF", "dttm": "20190502161426", "resultCode": 0, '
            '"resultMessage": "OK", "paymentStatus": 1, "signature": '
            '"DtDHJocYFvaIJWGzGL8ETIHNNgaxnSMQHAcUm7m0sF4CQBYEYAMdbnAZUq1wOHwf9sxfOnAJyfCriYW4429u3g=="}; '
            'Json: None; {}'), (
            'pycsob', 'DEBUG', "Pycsob request headers: {'content-type': 'application/json', 'user-agent': "
            "'py-csob/0.7.0', 'Content-Length': '219'}"), (
            'pycsob', 'INFO', 'Pycsob response: [200] {"payId": "34ae55eb69e2cBF", "dttm": "20190502161426", '
            '"resultCode": 0, "resultMessage": "OK", "paymentStatus": 1, "signature": '
            '"DtDHJocYFvaIJWGzGL8ETIHNNgaxnSMQHAcUm7m0sF4CQBYEYAMdbnAZUq1wOHwf9sxfOnAJyfCriYW4429u3g=="}'), (
            'pycsob', 'DEBUG', "Pycsob response headers: {'Content-Type': 'text/plain'}"
        ))
