# coding: utf-8
from base64 import b64decode
import json
import requests.adapters
from collections import OrderedDict
from dataclasses import Field, dataclass, fields
from datetime import datetime
from enum import Enum, unique
from typing import Any, Dict, Iterable, List, Optional, Union

from . import conf, utils


class HTTPAdapter(requests.adapters.HTTPAdapter):
    """
    HTTP adapter with default timeout
    """

    def send(self, request, **kwargs):
        kwargs.setdefault('timeout', conf.HTTP_TIMEOUT)
        return super(HTTPAdapter, self).send(request, **kwargs)


def reorder_fields(instance: object) -> Iterable[Field]:
    """Reorder fields of dataclass."""
    for name in instance._ordered_fields:
        yield instance.__dataclass_fields__[name]


class ConvertMixin:
    """Convert instance into ordered dict."""

    _max_length: Dict[str, int] = {}  # parameters to string formatting (empty by default)

    def _format_field(self, name: str, value: Any) -> str:
        """Format value - use custom or predefined formatter."""
        if hasattr(self, f"_format_{name}"):
            value = getattr(self, f"_format_{name}")(value)  # custom formatting method
        elif isinstance(value, Enum):
            value = str(value.value)
        elif isinstance(value, datetime):
            value = value.isoformat()
        elif isinstance(value, str) and name in self._max_length:
            value = value[:self._max_length[name]].rstrip()
        return value

    def _to_camel_case(self, name: str) -> str:
        """Convert name to camel case form."""
        parts = name.split("_")
        return parts[0] + "".join(i.title() for i in parts[1:])

    def to_dict(self) -> Dict[str, Union[str, Dict]]:
        """Carry out conversion."""
        data = []
        get_fields = reorder_fields if hasattr(self, '_ordered_fields') else fields
        for field in get_fields(self):
            value = getattr(self, field.name)
            if value in conf.EMPTY_VALUES:
                continue
            if hasattr(value, 'to_dict'):
                value = value.to_dict()
            data.append((self._to_camel_case(field.name), self._format_field(field.name, value)))
        return OrderedDict(data)


@unique
class Currency(Enum):
    """Currencies allowed in card gatewway."""

    CZK = "CZK"
    EUR = "EUR"
    USD = "USD"
    GBP = "GBP"
    HUF = "HUF"
    PLN = "PLN"
    RON = "RON"
    NOK = "NOK"
    SEK = "SEK"


@unique
class PayOperation(Enum):
    """Pay operations allowed on card gateway."""

    PAYMENT = "payment"
    ONECLICK_PAYMENT = "oneclickPayment"
    CUSTOM_PAYMENT = "customPayment"


@unique
class PayMethod(Enum):
    """Pay methods allowed on card gateway."""

    CARD = "card"
    CARD_LVP = "card#LVP"


@unique
class ReturnMethod(Enum):
    """Available HTTP methods."""

    GET = "GET"
    POST = "POST"


@unique
class Language(Enum):
    """Allowed languages in card gateway."""

    CZECH = "cs"
    ENGLISH = "en"
    GERMAN = "de"
    FRENCH = "fr"
    HUNGARIAN = "hu"
    ITALIAN = "it"
    JAPANESE = "jp"
    POLISH = "po"
    PORTUGUESE = "pt"
    ROMANIAN = "ro"
    RUSSIAN = "ru"
    SLOVAK = "sk"
    SPANISH = "es"
    TURKISH = "tu"
    VIETNAMESE = "vt"
    CROATIAN = "hr"
    SLOVENIAN = "sl"
    SWEDISH = "sv"


@dataclass
class CartItem(ConvertMixin):
    """Cart item for creating card payment."""
    # Documentation: https://github.com/csob/paymentgateway/wiki/Basic-methods#item---cart-item-object-cart-

    name: str
    quantity: int
    amount: int
    description: Optional[str] = None

    _max_length = {"name": 20, "description": 40}


@dataclass
class CustomerAccount(ConvertMixin):
    """Customer account data."""
    # Documentation: https://github.com/csob/paymentgateway/wiki/Purchase-metadata#customeraccount-data-

    created_at: Optional[datetime] = None
    changed_at: Optional[datetime] = None
    changed_pwd_at: Optional[datetime] = None
    order_history: Optional[int] = None
    payments_day: Optional[int] = None
    payments_year: Optional[int] = None
    oneclick_adds: Optional[int] = None
    suspicious: Optional[bool] = None


@unique
class CustomerLoginType(Enum):
    """Type of customer login."""
    # Documentation: https://github.com/csob/paymentgateway/wiki/Purchase-metadata#customerlogin-data-

    GUEST = "guest"
    ACCOUNT = "account"
    FEDERATED = "federated"
    ISSUER = "issuer"
    THIRDPARTY = "thirdparty"
    FIDO = "fido"
    FIDO_SIGNED = "fido_signed"
    API = "api"


@dataclass
class CustomerLogin(ConvertMixin):
    """Customer login data."""
    # Documentation: https://github.com/csob/paymentgateway/wiki/Purchase-metadata#customerlogin-data-

    auth: Optional[CustomerLoginType] = None
    auth_at: Optional[datetime] = None
    auth_data: Optional[str] = None


@dataclass
class Customer(ConvertMixin):
    """Customer data for creating card payment."""
    # Documentation: https://github.com/csob/paymentgateway/wiki/Purchase-metadata#customer-data-

    name: str
    email: Optional[str] = None
    home_phone: Optional[str] = None
    work_phone: Optional[str] = None
    mobile_phone: Optional[str] = None
    account: Optional[CustomerAccount] = None
    login: Optional[CustomerLogin] = None

    _max_length = {"name": 45}


@dataclass
class OrderAddress(ConvertMixin):
    """Order address (billing or shipping)."""
    # Documentation: https://github.com/csob/paymentgateway/wiki/Purchase-metadata#orderaddress-data-

    address_1: str
    city: str
    zip: str
    country: str
    address_2: Optional[str] = None
    address_3: Optional[str] = None
    state: Optional[str] = None

    _max_length = {"address_1": 50, "address_2": 50, "address_3": 50, "city": 50, "zip": 16}
    _ordered_fields = ("address_1", "address_2", "address_3", "city", "zip", "country", "state")


@dataclass
class OrderGiftcards(ConvertMixin):
    """Order giftcards data."""
    # Documentation: https://github.com/csob/paymentgateway/wiki/Purchase-metadata#ordergiftcards-data-

    total_amount: Optional[int] = None
    currency: Optional[Currency] = None
    quantity: Optional[int] = None


@unique
class OrderType(Enum):
    """Type of order."""
    # Documentation: https://github.com/csob/paymentgateway/wiki/Purchase-metadata#order-data-

    PURCHASE = "purchase"
    BALANCE = "balance"
    PREPAID = "prepaid"
    CASH = "cash"
    CHECK = "check"


@unique
class OrderAvailability(Enum):
    """Availability of order."""
    # Documentation: https://github.com/csob/paymentgateway/wiki/Purchase-metadata#order-data-

    NOW = "now"
    PREORDER = "preorder"


@unique
class OrderDelivery(Enum):
    """Delivery of order."""
    # Documentation: https://github.com/csob/paymentgateway/wiki/Purchase-metadata#order-data-

    SHIPPING = "shipping"
    SHIPPING_VERIFIED = "shipping_verified"
    INSTORE = "instore"
    DIGITAL = "digital"
    TICKET = "ticket"
    OTHER = "other"


@unique
class OrderDeliveryMode(Enum):
    """Delivery mode of order."""
    # Documentation: https://github.com/csob/paymentgateway/wiki/Purchase-metadata#order-data-

    ELECTRONIC = 0
    SAME_DAY = 1
    NEXT_DAY = 2
    LATER = 3


OrderAvailabilityType = Union[OrderAvailability, datetime]


@dataclass
class Order(ConvertMixin):
    """Order data for creating card payment."""
    # Documentation: https://github.com/csob/paymentgateway/wiki/Purchase-metadata#order-data-

    type: Optional[OrderType] = None
    availability: Optional[OrderAvailabilityType] = None
    delivery: Optional[OrderDelivery] = None
    delivery_mode: Optional[OrderDeliveryMode] = None
    delivery_email: Optional[str] = None
    name_match: Optional[bool] = None
    address_match: Optional[bool] = None
    billing: Optional[OrderAddress] = None
    shipping: Optional[OrderAddress] = None
    shipping_added_at: Optional[datetime] = None
    reorder: Optional[bool] = None
    giftcards: Optional[OrderGiftcards] = None

    _max_length = {"delivery_email": 100}


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

        session = utils.PycsobSession()
        session.headers = conf.HEADERS
        session.mount('https://', HTTPAdapter())
        session.mount('http://', HTTPAdapter())

        self._client = session

    def payment_init(
        self,
        order_no: Union[int, str],
        total_amount: int,
        return_url: str,
        description: str,
        cart: Optional[List[CartItem]] = None,
        customer_id: Optional[str] = None,
        currency: Currency = Currency.CZK,
        language: Language = Language.CZECH,
        close_payment: bool = True,
        return_method: ReturnMethod = ReturnMethod.POST,
        pay_operation: PayOperation = PayOperation.PAYMENT,
        ttl_sec: int = 600,
        logo_version: Optional[int] = None,
        color_scheme_version: Optional[int] = None,
        merchant_data: Optional[bytearray] = None,
        customer: Optional[Customer] = None,
        order: Optional[Order] = None,
        custom_expiry: Optional[str] = None,
        pay_method: PayMethod = PayMethod.CARD,
    ) -> OrderedDict[str, Any]:
        """
        Initialize transaction, sum of cart items must be equal to total amount
        If cart is None, we create it for you from total_amount and description values.

        Cart example::

            cart = [
                CartItem(name='Order in sho XYZ', quantity=5, amount=12345),
                CartItem(name='Postage', quantity=1, amount=0),
            ]

        :param order_no: order number
        :param total_amount:
        :param return_url: URL to be returned to from payment gateway
        :param cart: items in cart, currently min one item, max two as mentioned in CSOB spec
        :param description: product name - it is a part of the cart
        :param customer_id: optional customer id
        :param language: supported languages: cs, en, de, fr, hu, it, ja, pl, pt, ro, ru, sk, es, tr, vi, hr, sl, sv
        :param currency: supported currencies: CZK, EUR, USD, GBP, HUF, PLN, RON, NOK, SEK
        :param close_payment:
        :param return_method: method which be used for return to shop from gateway POST (default) or GET
        :param pay_operation: `payment`, `customPayment` or `oneclickPayment`
        :param ttl_sec: number of seconds to the timeout
        :param logo_version: Logo version number
        :param color_scheme_version: Color scheme version number
        :param merchant_data: bytearray of merchant data
        :param customer: Additional customer purchase data
        :param order: Additional purchase data related to the order
        :param custom_expiry: Custom payment expiration, format YYYYMMDDHHMMSS
        :param pay_method: 'card' = card payment, 'card#LVP' = card payment with low value payment
        :return: response from gateway as OrderedDict
        """

        # fill cart if not set
        if not cart:
            cart = [CartItem(name=description, quantity=1, amount=total_amount)]

        payload = utils.mk_payload(self.f_key, pairs=(
            ('merchantId', self.merchant_id),
            ('orderNo', str(order_no)),
            ('dttm', utils.dttm()),
            ('payOperation', pay_operation.value),
            ('payMethod', pay_method.value),
            ('totalAmount', total_amount),
            ('currency', currency.value),
            ('closePayment', close_payment),
            ('returnUrl', return_url),
            ('returnMethod', return_method.value),
            ('cart', [item.to_dict() for item in cart]),
            ('customer', customer.to_dict() if customer is not None else None),
            ('order', order.to_dict() if order is not None else None),
            ('merchantData', utils.encode_merchant_data(merchant_data)),
            ('customerId', customer_id),
            ('language', language.value),
            ('ttlSec', ttl_sec),
            ('logoVersion', logo_version),
            ('colorSchemeVersion', color_scheme_version),
            ('customExpiry', custom_expiry),
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
            endpoint_url='echo/customer'
        )
        payload = utils.mk_payload(self.f_key, pairs=(
            ('merchantId', self.merchant_id),
            ('customerId', customer_id),
            ('dttm', utils.dttm())
        ))
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

    def button_init(
            self, order_no, total_amount, client_ip, return_url,
            language='cs', return_method='POST', merchant_data=None):
        "Get url to the button."

        payload = utils.mk_payload(self.f_key, pairs=(
            ('merchantId', self.merchant_id),
            ('orderNo', str(order_no)),
            ('dttm', utils.dttm()),
            ('clientIp', client_ip),
            ('totalAmount', total_amount),
            ('currency', 'CZK'),
            ('returnUrl', return_url),
            ('returnMethod', return_method),
            ('brand', 'csob'),
            ('merchantData', utils.encode_merchant_data(merchant_data)),
            ('language', language[:2]),
        ))
        url = utils.mk_url(base_url=self.base_url, endpoint_url='button/init')
        r = self._client.post(url, data=json.dumps(payload))
        return utils.validate_response(r, self.f_pubkey)
