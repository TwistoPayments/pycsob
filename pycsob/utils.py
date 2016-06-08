import sys
import datetime
from base64 import b64encode, b64decode
from collections import OrderedDict
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5

from . import conf

if sys.version_info.major < 3:
    from urlparse import urljoin
    from urllib import quote_plus
    PY2 = True
else:
    from urllib.parse import urljoin, quote_plus
    PY2 = False


def sign(payload, keyfile):
    msg = mk_msg_for_sign(payload)
    key = RSA.importKey(open(keyfile).read())
    h = SHA.new(msg)
    signer = PKCS1_v1_5.new(key)
    return b64encode(signer.sign(h)).decode()


def verify(payload, signature, pubkeyfile):
    msg = mk_msg_for_sign(payload)
    key = RSA.importKey(open(pubkeyfile).read())
    h = SHA.new(msg)
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
    if PY2:
        msg = unicode(bytes(msg), 'utf-8')
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


class Response(object):
    keys = 'payId', 'customerId', 'dttm', 'resultCode', 'resultMessage', 'paymentStatus', 'authCode'
    data = None
    error = None

    def __init__(self, response):
        status = response.status_code
        if status == 200:
            self.data = response.json()
        else:
            self.error = {status: conf.HTTP_STATUSES.get(status, 'Unknown Status')}

    @property
    def payload(self):
        o = OrderedDict()
        for k in self.keys:
            if k in self.data:
                o[k] = self.data[k]
        return o

    def is_valid(self, key):
        if self.error:
            return False

        verified = verify(
            payload=self.payload,
            signature=self.data['signature'],
            pubkeyfile=key
        )
        if not verified:
            self.error = 'Cannot verify response, bad signature'
        return verified
