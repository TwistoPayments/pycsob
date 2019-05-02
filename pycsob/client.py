# coding: utf-8
from base64 import b64encode, b64decode
import json
import logging
import requests
import requests.adapters
from collections import OrderedDict

from . import conf, utils

log = logging.getLogger('pycsob')


class HTTPAdapter(requests.adapters.HTTPAdapter):
    """
    HTTP adapter with default timeout
    """

    def send(self, request, **kwargs):
        kwargs.setdefault('timeout', conf.HTTP_TIMEOUT)
        return super(HTTPAdapter, self).send(request, **kwargs)


class CsobClient(object):

    def __init__(self, merchant_id, base_url, private_key_file, csob_pub_key_file):
        """
        Initialize Client

        :param merchant_id: Your Merchant ID (you can find it in POSMerchant)
        :param base_url: Base API url development / production
        :param private_key_file: Path to generated private key file
        :param csob_pub_key_file: Path to CSOB public key
        """
        self.merchant_id = merchant_id
        self.base_url = base_url
        self.f_key = private_key_file
        self.f_pubkey = csob_pub_key_file

        session = requests.Session()
        session.headers = conf.HEADERS
        session.mount('https://', HTTPAdapter())
        session.mount('http://', HTTPAdapter())

        self._client = session

    def payment_init(self, order_no, total_amount, return_url, description, cart=None,
                     customer_id=None, currency='CZK', language='CZ', close_payment=True,
                     return_method='POST', pay_operation='payment', ttl_sec=600,
                     logo_version=None, color_scheme_version=None, merchant_data=None):
        """
        Initialize transaction, sum of cart items must be equal to total amount
        If cart is None, we create it for you from total_amount and description values.

        Cart example::

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

        :param order_no: order number
        :param total_amount:
        :param return_url: URL to be returned to from payment gateway
        :param cart: items in cart, currently min one item, max two as mentioned in CSOB spec
        :param description: order description
        :param customer_id: optional customer id
        :param language: supported languages: 'CZ', 'EN', 'DE', 'SK', 'HU', 'IT', 'JP', 'PL', 'PT', 'RO', 'RU', 'SK', 'ES', 'TR' or 'VN'
        :param currency: supported currencies: 'CZK', 'EUR', 'USD', 'GBP'
        :param close_payment:
        :param return_method: method which be used for return to shop from gateway POST (default) or GET
        :param pay_operation: `payment` or `oneclickPayment`
        :param ttl_sec: number of seconds to the timeout
        :param logo_version: Logo version number
        :param color_scheme_version: Color scheme version number
        :param merchant_data: bytearray of merchant data
        :return: response from gateway as OrderedDict
        """

        if len(description) > 255:
            raise ValueError('Description length is over 255 chars')

        if merchant_data:
            merchant_data = b64encode(merchant_data).decode("UTF-8")
            if len(merchant_data) > 255:
                raise ValueError('Merchant data length encoded to BASE64 is over 255 chars')

        # fill cart if not set
        if not cart:
            cart = [
                OrderedDict([
                    ('name', description[:20]),
                    ('quantity', 1),
                    ('amount', total_amount)
                ])
            ]

        # Fix invalid language code type (country code).
        lang_code = language.upper()[:2]
        language = {'CS': 'CZ'}.get(lang_code, lang_code)

        payload = utils.mk_payload(self.f_key, pairs=(
            ('merchantId', self.merchant_id),
            ('orderNo', str(order_no)),
            ('dttm', utils.dttm()),
            ('payOperation', pay_operation),
            ('payMethod', 'card'),
            ('totalAmount', total_amount),
            ('currency', currency),
            ('closePayment', close_payment),
            ('returnUrl', return_url),
            ('returnMethod', return_method),
            ('cart', cart),
            ('description', description),
            ('merchantData', merchant_data),
            ('customerId', customer_id),
            ('language', language),
            ('ttlSec', ttl_sec),
            ('logoVersion', logo_version),
            ('colorSchemeVersion', color_scheme_version),
        ))
        url = utils.mk_url(base_url=self.base_url, endpoint_url='payment/init')
        r = self._client.post(url, data=json.dumps(payload))
        return utils.validate_response(r, self.f_pubkey)

    def get_payment_process_url(self, pay_id):
        """
        :param pay_id: pay_id obtained from payment_init()
        :return: url to process payment
        """
        return utils.mk_url(
            base_url=self.base_url,
            endpoint_url='payment/process/',
            payload=self.req_payload(pay_id=pay_id)
        )

    def gateway_return(self, datadict):
        """
        Return from gateway as OrderedDict

        :param datadict: data from request in dict
        :return: verified data or raise error
        """
        o = OrderedDict()
        for k in conf.RESPONSE_KEYS:
            if k in datadict:
                o[k] = int(datadict[k]) if k in ('resultCode', 'paymentStatus') else datadict[k]
        if not utils.verify(o, datadict['signature'], self.f_pubkey):
            raise utils.CsobVerifyError('Unverified gateway return data')
        if "dttm" in o:
            o["dttime"] = utils.dttm_decode(o["dttm"])
        if 'merchantData' in o:
            o['merchantData'] = b64decode(o['merchantData'])
        return o

    def payment_status(self, pay_id):
        url = utils.mk_url(
            base_url=self.base_url,
            endpoint_url='payment/status/',
            payload=self.req_payload(pay_id=pay_id)
        )
        r = self._client.get(url=url)
        return utils.validate_response(r, self.f_pubkey)

    def payment_reverse(self, pay_id):
        url = utils.mk_url(
            base_url=self.base_url,
            endpoint_url='payment/reverse/'
        )
        payload = self.req_payload(pay_id)
        r = self._client.put(url, data=json.dumps(payload))
        return utils.validate_response(r, self.f_pubkey)

    def payment_close(self, pay_id, total_amount=None):
        url = utils.mk_url(
            base_url=self.base_url,
            endpoint_url='payment/close/'
        )
        payload = self.req_payload(pay_id, totalAmount=total_amount)
        r = self._client.put(url, data=json.dumps(payload))
        return utils.validate_response(r, self.f_pubkey)

    def payment_refund(self, pay_id, amount=None):
        url = utils.mk_url(
            base_url=self.base_url,
            endpoint_url='payment/refund/'
        )

        payload = self.req_payload(pay_id, amount=amount)
        r = self._client.put(url, data=json.dumps(payload))
        return utils.validate_response(r, self.f_pubkey)

    def customer_info(self, customer_id):
        """
        :param customer_id: e-shop customer ID
        :return: data from JSON response or raise error
        """
        url = utils.mk_url(
            base_url=self.base_url,
            endpoint_url='customer/info/',
            payload=utils.mk_payload(self.f_key, pairs=(
                ('merchantId', self.merchant_id),
                ('customerId', customer_id),
                ('dttm', utils.dttm())
            ))
        )
        r = self._client.get(url)
        return utils.validate_response(r, self.f_pubkey)

    def oneclick_init(self, orig_pay_id, order_no, total_amount, currency='CZK', description=None):
        """
        Initialize one-click payment. Before this, you need to call payment_init(..., pay_operation='oneclickPayment')
        It will create payment template for you. Use pay_id returned from payment_init as orig_pay_id in this method.
        """

        payload = utils.mk_payload(self.f_key, pairs=(
            ('merchantId', self.merchant_id),
            ('origPayId', orig_pay_id),
            ('orderNo', str(order_no)),
            ('dttm', utils.dttm()),
            ('totalAmount', total_amount),
            ('currency', currency),
            ('description', description),
        ))
        url = utils.mk_url(base_url=self.base_url, endpoint_url='payment/oneclick/init')
        r = self._client.post(url, data=json.dumps(payload))
        return utils.validate_response(r, self.f_pubkey)

    def oneclick_start(self, pay_id):
        """
        Start one-click payment. After 2 - 3 seconds it is recommended to call payment_status().

        :param pay_id: use pay_id returned by oneclick_init()
        """

        payload = utils.mk_payload(self.f_key, pairs=(
            ('merchantId', self.merchant_id),
            ('payId', pay_id),
            ('dttm', utils.dttm()),
        ))
        url = utils.mk_url(base_url=self.base_url, endpoint_url='payment/oneclick/start')
        r = self._client.post(url, data=json.dumps(payload))
        return utils.validate_response(r, self.f_pubkey)

    def echo(self, method='POST'):
        """
        Echo call for development purposes/gateway tests

        :param method: request method (GET/POST), default is POST
        :return: data from JSON response or raise error
        """
        payload = utils.mk_payload(self.f_key, pairs=(
            ('merchantId', self.merchant_id),
            ('dttm', utils.dttm())
        ))
        if method.lower() == 'post':
            url = utils.mk_url(
                base_url=self.base_url,
                endpoint_url='echo/'
            )
            r = self._client.post(url, data=json.dumps(payload))
        else:
            url = utils.mk_url(
                base_url=self.base_url,
                endpoint_url='echo/',
                payload=payload
            )
            r = self._client.get(url)

        return utils.validate_response(r, self.f_pubkey)

    def req_payload(self, pay_id, **kwargs):
        pairs = (
            ('merchantId', self.merchant_id),
            ('payId', pay_id),
            ('dttm', utils.dttm()),
        )
        for k, v in kwargs.items():
            if v not in conf.EMPTY_VALUES:
                pairs += ((k, v),)
        return utils.mk_payload(keyfile=self.f_key, pairs=pairs)

    def button(self, pay_id, brand):
        "Get url to the button."
        payload = utils.mk_payload(self.f_key, pairs=(
            ('merchantId', self.merchant_id),
            ('payId', pay_id),
            ('brand', brand),
            ('dttm', utils.dttm()),
        ))
        url = utils.mk_url(base_url=self.base_url, endpoint_url='payment/button/')
        r = self._client.post(url, data=json.dumps(payload))
        return utils.validate_response(r, self.f_pubkey)
