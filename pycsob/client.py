from base64 import b64encode, b64decode
import json
import logging
from datetime import datetime

import requests
import requests.adapters
from collections import OrderedDict

from requests import Response

from . import conf, utils

log = logging.getLogger("pycsob")


class HTTPAdapter(requests.adapters.HTTPAdapter):
    """
    HTTP adapter with default timeout
    """

    def send(self, request, **kwargs):
        kwargs.setdefault("timeout", conf.HTTP_TIMEOUT)
        return super().send(request, **kwargs)


class CsobClient:
    def __init__(
        self,
        merchant_id: str,
        base_url: str,
        private_key_file: str,
        csob_pub_key_file: str,
    ) -> None:
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
        session.mount("https://", HTTPAdapter())
        session.mount("http://", HTTPAdapter())

        self._client = session

    def payment_init(
        self,
        order_no: str,
        total_amount: str | int,
        return_url: str,
        description: str,
        cart: dict | None = None,
        customer: dict | None = None,
        order: dict | None = None,
        customer_id: str | None = None,
        currency: str | conf.CURRENCIES = conf.CURRENCIES.CZK,
        language: str | conf.LANGUAGES = conf.LANGUAGES.CZ,
        close_payment: bool = True,
        return_method: str = "POST",
        pay_operation: str = "payment",
        ttl_sec: int = 600,
        logo_version: int | None = None,
        color_scheme_version: int | None = None,
        merchant_data: bytes | None = None,
        custom_expiry: str | datetime | None = None,
    ):
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
        :param customer: additional data about customer https://github.com/csob/platebnibrana/wiki/Dodate%C4%8Dn%C3%A1-data-o-n%C3%A1kupu#customer
        :param order: additional data about order https://github.com/csob/platebnibrana/wiki/Dodate%C4%8Dn%C3%A1-data-o-n%C3%A1kupu#order
        :param description: order description
        :param customer_id: optional customer id
        :param language: supported languages: 'cs' ,'en' ,'de' ,'fr' ,'hu' ,'it' ,'ja' ,'pl' ,'pt' ,'ro' ,'ru' ,'sk' ,'es' ,'tr' ,'vi' ,'hr' ,'sl' ,'sv'
        :param currency: supported currencies: 'CZK', 'EUR', 'USD', 'GBP', 'HUF', 'PLN', 'HRK', 'RON', 'NOK', 'SEK'
        :param close_payment:
        :param return_method: method which be used for return to shop from gateway POST (default) or GET
        :param pay_operation: `payment` or `oneclickPayment` or `customPayment`
        :param ttl_sec: number of seconds to the timeout. Min 300 and max 1800 (5-30 min). If pay_operation is `customPayment` then ttl_sec is ingnored and can be set up to 60 days via `custom_expiry`
        :param logo_version: Logo version number
        :param color_scheme_version: Color scheme version number
        :param merchant_data: bytearray of merchant data
        :param custom_expiry: should be datetime or str with format `YYYYMMDDHHMMSS`. Can be up to 60 days from now. Default value is 60 days
        :return: response from gateway as OrderedDict
        """

        if len(description) > 255:
            raise ValueError("Description length is over 255 chars")

        if merchant_data:
            merchant_data = b64encode(merchant_data).decode("UTF-8")
            if len(merchant_data) > 255:
                raise ValueError(
                    "Merchant data length encoded to BASE64 is over 255 chars"
                )

        if not language:
            raise ValueError("Language is not provided")

        if not currency:
            raise ValueError("Currency is not provided")

        if isinstance(language, conf.LANGUAGES):
            language = language.value

        if isinstance(currency, conf.CURRENCIES):
            currency = currency.value

        if language not in conf.LANGUAGES:
            raise ValueError(
                f"Language '{language}' is not supported. Use any of {', '.join(conf.LANGUAGES.__members__)}"
            )

        if currency not in conf.CURRENCIES:
            raise ValueError(
                f"Currency '{currency}' is not supported. Use any of {', '.join(conf.CURRENCIES.__members__)}"
            )

        # fill cart if not set
        if not cart:
            cart = [
                OrderedDict(
                    [
                        ("name", description[:20].strip()),
                        ("quantity", 1),
                        ("amount", total_amount),
                    ]
                )
            ]

        if isinstance(custom_expiry, datetime):
            custom_expiry = utils.dttm_format(custom_expiry)

        payload = utils.mk_payload(
            self.f_key,
            pairs=(
                ("merchantId", self.merchant_id),
                ("orderNo", str(order_no)),
                ("dttm", utils.dttm()),
                ("payOperation", pay_operation),
                ("payMethod", "card"),
                ("totalAmount", total_amount),
                ("currency", currency),
                ("closePayment", close_payment),
                ("returnUrl", return_url),
                ("returnMethod", return_method),
                ("cart", cart),
                ("customer", customer),
                ("order", order),
                ("description", description),
                ("merchantData", merchant_data),
                ("customerId", customer_id),
                ("language", language),
                ("ttlSec", ttl_sec),
                ("logoVersion", logo_version),
                ("colorSchemeVersion", color_scheme_version),
                ("customExpiry", custom_expiry),
            ),
        )
        url = utils.mk_url(base_url=self.base_url, endpoint_url="payment/init")
        r = self._client.post(url, data=json.dumps(payload))
        return utils.validate_response(r, self.f_pubkey)

    def get_payment_process_url(self, pay_id: str) -> str:
        """
        :param pay_id: pay_id obtained from payment_init()
        :return: url to process payment
        """
        return utils.mk_url(
            base_url=self.base_url,
            endpoint_url="payment/process/",
            payload=self.req_payload(pay_id=pay_id),
        )

    def gateway_return(self, datadict: OrderedDict | dict):
        """
        Return from gateway as OrderedDict

        :param datadict: data from request in dict
        :return: verified data or raise error
        """
        o = OrderedDict()
        for k in conf.RESPONSE_KEYS:
            if k in datadict:
                o[k] = (
                    int(datadict[k])
                    if k in ("resultCode", "paymentStatus")
                    else datadict[k]
                )
        if not utils.verify(o, datadict["signature"], self.f_pubkey):
            raise utils.CsobVerifyError("Unverified gateway return data")
        if "dttm" in o:
            o["dttime"] = utils.dttm_decode(o["dttm"])
        if "merchantData" in o:
            o["merchantData"] = b64decode(o["merchantData"])
        return o

    def payment_status(self, pay_id: str) -> Response:
        url = utils.mk_url(
            base_url=self.base_url,
            endpoint_url="payment/status/",
            payload=self.req_payload(pay_id=pay_id),
        )
        r = self._client.get(url=url)
        return utils.validate_response(r, self.f_pubkey)

    def payment_reverse(self, pay_id: str) -> Response:
        url = utils.mk_url(base_url=self.base_url, endpoint_url="payment/reverse/")
        payload = self.req_payload(pay_id)
        r = self._client.put(url, data=json.dumps(payload))
        return utils.validate_response(r, self.f_pubkey)

    def payment_close(
        self, pay_id: str, total_amount: int | str | None = None
    ) -> Response:
        url = utils.mk_url(base_url=self.base_url, endpoint_url="payment/close/")
        payload = self.req_payload(pay_id, totalAmount=total_amount)
        r = self._client.put(url, data=json.dumps(payload))
        return utils.validate_response(r, self.f_pubkey)

    def payment_refund(self, pay_id: str, amount: int | str | None = None) -> Response:
        url = utils.mk_url(base_url=self.base_url, endpoint_url="payment/refund/")

        payload = self.req_payload(pay_id, amount=amount)
        r = self._client.put(url, data=json.dumps(payload))
        return utils.validate_response(r, self.f_pubkey)

    def customer_info(self, customer_id: str) -> Response:
        """
        :param customer_id: e-shop customer ID
        :return: data from JSON response or raise error
        """
        url = utils.mk_url(
            base_url=self.base_url,
            endpoint_url="customer/info/",
            payload=utils.mk_payload(
                self.f_key,
                pairs=(
                    ("merchantId", self.merchant_id),
                    ("customerId", customer_id),
                    ("dttm", utils.dttm()),
                ),
            ),
        )
        r = self._client.get(url)
        return utils.validate_response(r, self.f_pubkey)

    def oneclick_init(
        self,
        orig_pay_id: str,
        order_no: str,
        total_amount: int | str,
        currency: str = "CZK",
        description: str | None = None,
    ) -> Response:
        """
        Initialize one-click payment. Before this, you need to call payment_init(..., pay_operation='oneclickPayment')
        It will create payment template for you. Use pay_id returned from payment_init as orig_pay_id in this method.
        """

        payload = utils.mk_payload(
            self.f_key,
            pairs=(
                ("merchantId", self.merchant_id),
                ("origPayId", orig_pay_id),
                ("orderNo", str(order_no)),
                ("dttm", utils.dttm()),
                ("totalAmount", total_amount),
                ("currency", currency),
                ("description", description),
            ),
        )
        url = utils.mk_url(base_url=self.base_url, endpoint_url="payment/oneclick/init")
        r = self._client.post(url, data=json.dumps(payload))
        return utils.validate_response(r, self.f_pubkey)

    def oneclick_start(self, pay_id: str) -> Response:
        """
        Start one-click payment. After 2 - 3 seconds it is recommended to call payment_status().

        :param pay_id: use pay_id returned by oneclick_init()
        """

        payload = utils.mk_payload(
            self.f_key,
            pairs=(
                ("merchantId", self.merchant_id),
                ("payId", pay_id),
                ("dttm", utils.dttm()),
            ),
        )
        url = utils.mk_url(
            base_url=self.base_url, endpoint_url="payment/oneclick/start"
        )
        r = self._client.post(url, data=json.dumps(payload))
        return utils.validate_response(r, self.f_pubkey)

    def echo(self, method: str = "POST") -> Response:
        """
        Echo call for development purposes/gateway tests

        :param method: request method (GET/POST), default is POST
        :return: data from JSON response or raise error
        """
        payload = utils.mk_payload(
            self.f_key, pairs=(("merchantId", self.merchant_id), ("dttm", utils.dttm()))
        )
        if method.lower() == "post":
            url = utils.mk_url(base_url=self.base_url, endpoint_url="echo/")
            r = self._client.post(url, data=json.dumps(payload))
        else:
            url = utils.mk_url(
                base_url=self.base_url, endpoint_url="echo/", payload=payload
            )
            r = self._client.get(url)

        return utils.validate_response(r, self.f_pubkey)

    def req_payload(self, pay_id: str, **kwargs) -> OrderedDict:
        pairs = (
            ("merchantId", self.merchant_id),
            ("payId", pay_id),
            ("dttm", utils.dttm()),
        )
        for k, v in kwargs.items():
            if v not in conf.EMPTY_VALUES:
                pairs += ((k, v),)
        return utils.mk_payload(keyfile=self.f_key, pairs=pairs)

    def button(self, pay_id: str, brand: str) -> Response:
        """
        Get url to the button.
        """
        payload = utils.mk_payload(
            self.f_key,
            pairs=(
                ("merchantId", self.merchant_id),
                ("payId", pay_id),
                ("brand", brand),
                ("dttm", utils.dttm()),
            ),
        )
        url = utils.mk_url(base_url=self.base_url, endpoint_url="payment/button/")
        r = self._client.post(url, data=json.dumps(payload))
        return utils.validate_response(r, self.f_pubkey)
