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


class CsobVerifyError(Exception):
    pass


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


def validate_response(response, key):
    response.raise_for_status()

    data = response.json()
    signature = data.pop('signature')
    payload = OrderedDict()

    for k in conf.RESPONSE_KEYS:
        if k in data:
            payload[k] = data[k]

    if not verify(payload, signature, key):
        raise CsobVerifyError('Cannot verify response')

    # extensions
    if 'extensions' in data:
        response.extensions = []
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
    response.payload = payload
    return response
