import datetime
import logging
import re
import requests
from base64 import b64encode, b64decode
from collections import OrderedDict
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5

from . import conf

from urllib.parse import urljoin, quote_plus

LOGGER = logging.getLogger('pycsob')


class CsobVerifyError(Exception):
    pass


class PyscobSession(requests.Session):
    """Request session with logging requests."""

    def post(self, url, data=None, json=None, **kwargs):
        LOGGER.info("Pycsob request POST: {}; Data: {}; Json: {}; {}".format(url, data, json, kwargs))
        return super().post(url, data, json, **kwargs)

    def get(self, url, **kwargs):
        LOGGER.info("Pycsob request GET: {}; {}".format(url, kwargs))
        return super().get(url, **kwargs)

    def put(self, url, data=None, **kwargs):
        LOGGER.info("Pycsob request PUT: {}; Data: {}; {}".format(url, data, kwargs))
        return super().put(url, data, **kwargs)

    def send(self, request, **kwargs):
        LOGGER.debug("Pycsob request headers: {}".format(request.headers))
        return super().send(request, **kwargs)


def sign(payload, keyfile):
    msg = mk_msg_for_sign(payload)
    with open(keyfile, "rb") as f:
        key = RSA.importKey(f.read())
    h = SHA256.new(msg)
    signer = PKCS1_v1_5.new(key)
    return b64encode(signer.sign(h)).decode()


def verify(payload, signature, pubkeyfile):
    msg = mk_msg_for_sign(payload)
    with open(pubkeyfile, "rb") as f:
        key = RSA.importKey(f.read())
    h = SHA256.new(msg)
    verifier = PKCS1_v1_5.new(key)
    return verifier.verify(h, b64decode(signature))


def mk_msg_for_sign(payload):
    payload = payload.copy()
    if 'cart' in payload and payload['cart'] not in conf.EMPTY_VALUES:
        cart_msg = []
        for one in payload['cart']:
            cart_msg.extend(one.values())
        payload['cart'] = '|'.join(map(str_or_jsbool, cart_msg))
    msg = '|'.join(map(str_or_jsbool, payload.values()))
    return msg.encode('utf-8')


def mk_payload(keyfile, pairs):
    payload = OrderedDict([(k, v) for k, v in pairs if v not in conf.EMPTY_VALUES])
    payload['signature'] = sign(payload, keyfile)
    return payload


def mk_url(base_url, endpoint_url, payload=None):
    url = urljoin(base_url, endpoint_url)
    if payload is None:
        return url
    return urljoin(url, '/'.join(map(quote_plus, payload.values())))


def str_or_jsbool(v):
    if type(v) == bool:
        return str(v).lower()
    return str(v)


def dttm(format_='%Y%m%d%H%M%S'):
    return datetime.datetime.now().strftime(format_)


def dttm_decode(value):
    """Decode dttm value '20190404091926' to the datetime object."""
    return datetime.datetime.strptime(value, "%Y%m%d%H%M%S")


def validate_response(response, key):
    LOGGER.info("Pycsob response: [{}] {}".format(response.status_code, response.text))
    LOGGER.debug("Pycsob response headers: {}".format(response.headers))

    response.raise_for_status()

    data = response.json()
    signature = data.pop('signature')
    payload = OrderedDict()

    for k in conf.RESPONSE_KEYS:
        if k in data:
            payload[k] = data[k]

    if not verify(payload, signature, key):
        raise CsobVerifyError('Cannot verify response')

    if "dttm" in payload:
        payload["dttime"] = dttm_decode(payload["dttm"])

    response.extensions = []
    response.payload = payload

    # extensions
    if 'extensions' in data:
        maskclnrp_keys = 'extension', 'dttm', 'maskedCln', 'expiration', 'longMaskedCln'
        for one in data['extensions']:
            if one['extension'] == 'maskClnRP':
                o = OrderedDict()
                for k in maskclnrp_keys:
                    if k in one:
                        o[k] = one[k]
                if verify(o, one['signature'], key):
                    response.extensions.append(o)
                else:
                    raise CsobVerifyError('Cannot verify masked card extension response')

    return response


PROVIDERS = (
    (conf.CARD_PROVIDER_VISA, re.compile(r'^4\d{5}$')),
    (conf.CARD_PROVIDER_AMEX, re.compile(r'^3[47]\d{4}$')),
    (conf.CARD_PROVIDER_DINERS, re.compile(r'^3(?:0[0-5]|[68][0-9])[0-9]{4}$')),
    (conf.CARD_PROVIDER_JCB, re.compile(r'^(?:2131|1800|35[0-9]{2})[0-9]{2}$')),
    (conf.CARD_PROVIDER_MC, re.compile(r'^5[1-5][0-9]{4}|222[1-9][0-9]{2}|22[3-9][0-9]{4}|2[3-6][0-9]{5}|27[01][0-9]{4}|2720[0-9]{2}$')),
)


def get_card_provider(long_masked_number):
    for provider_id, rx in PROVIDERS:
        if rx.match(long_masked_number[:6]):
            return provider_id, conf.CARD_PROVIDERS[provider_id]
    return None, None
