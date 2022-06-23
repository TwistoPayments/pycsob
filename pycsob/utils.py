import datetime
import re
from base64 import b64encode, b64decode
from collections import OrderedDict

from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from requests import Response

from . import conf

from urllib.parse import urljoin, quote_plus


class CsobVerifyError(Exception):
    pass


def sign(payload: OrderedDict | dict, keyfile: str):
    msg = mk_msg_for_sign(payload)
    with open(keyfile, "rb") as f:
        key = RSA.importKey(f.read())
    h = SHA.new(msg)
    signer = PKCS1_v1_5.new(key)
    return b64encode(signer.sign(h)).decode()


def verify(payload: OrderedDict | dict, signature: bytes, pubkeyfile: str):
    msg = mk_msg_for_sign(payload)
    with open(pubkeyfile, "rb") as f:
        key = RSA.importKey(f.read())
    h = SHA.new(msg)
    verifier = PKCS1_v1_5.new(key)
    return verifier.verify(h, b64decode(signature))


def mk_msg_for_sign(payload: OrderedDict | dict) -> bytes:
    payload = payload.copy()
    possible_objects = ["cart", "customer", "order"]
    for po in possible_objects:
        if po in payload and payload[po] not in conf.EMPTY_VALUES:
            object_msg = []
            for one in payload[po]:
                object_msg.extend(one.values())
            payload[po] = "|".join(map(str_or_jsbool, object_msg))
    msg = "|".join(map(str_or_jsbool, payload.values()))
    return msg.encode("utf-8")


def mk_payload(keyfile: str, pairs: tuple) -> OrderedDict:
    payload = OrderedDict([(k, v) for k, v in pairs if v not in conf.EMPTY_VALUES])
    payload["signature"] = sign(payload, keyfile)
    return payload


def mk_url(base_url: str, endpoint_url: str, payload=None):
    url = urljoin(base_url, endpoint_url)
    if payload is None:
        return url
    return urljoin(url, "/".join(map(quote_plus, payload.values())))


def str_or_jsbool(v: str | bool) -> str:
    if type(v) == bool:
        return str(v).lower()
    return str(v)


def dttm(format_: str = "%Y%m%d%H%M%S") -> str:
    return datetime.datetime.now().strftime(format_)


def dttm_format(datetime_: datetime.datetime, format_: str = "%Y%m%d%H%M%S") -> str:
    return datetime_.strftime(format_)


def dttm_decode(value: str) -> datetime.datetime:
    """Decode dttm value '20190404091926' to the datetime object."""
    return datetime.datetime.strptime(value, "%Y%m%d%H%M%S")


def validate_response(response: Response, key: str) -> Response:
    response.raise_for_status()

    data = response.json()
    signature = data.pop("signature")
    payload = OrderedDict((k, data[k]) for k in conf.RESPONSE_KEYS if k in data)

    if not verify(payload, signature, key):
        raise CsobVerifyError("Cannot verify response")

    if "dttm" in payload:
        payload["dttime"] = dttm_decode(payload["dttm"])

    response.extensions = []
    response.payload = payload

    # extensions
    if "extensions" in data:
        maskclnrp_keys = "extension", "dttm", "maskedCln", "expiration", "longMaskedCln"
        for one in data["extensions"]:
            if one["extension"] == "maskClnRP":
                o = OrderedDict((k, one[k]) for k in maskclnrp_keys if k in one)
                if verify(o, one["signature"], key):
                    response.extensions.append(o)
                else:
                    raise CsobVerifyError(
                        "Cannot verify masked card extension response"
                    )

    return response


PROVIDERS = (
    (conf.CARD_PROVIDER_VISA, re.compile(r"^4\d{5}$")),
    (conf.CARD_PROVIDER_AMEX, re.compile(r"^3[47]\d{4}$")),
    (conf.CARD_PROVIDER_DINERS, re.compile(r"^3(?:0[0-5]|[68][0-9])[0-9]{4}$")),
    (conf.CARD_PROVIDER_JCB, re.compile(r"^(?:2131|1800|35[0-9]{2})[0-9]{2}$")),
    (
        conf.CARD_PROVIDER_MC,
        re.compile(
            r"^5[1-5][0-9]{4}|222[1-9][0-9]{2}|22[3-9][0-9]{4}|2[3-6][0-9]{5}|27[01][0-9]{4}|2720[0-9]{2}$"
        ),
    ),
)


def get_card_provider(long_masked_number: str) -> tuple[int, str] | tuple[None, None]:
    for provider_id, rx in PROVIDERS:
        if rx.match(long_masked_number[:6]):
            return provider_id, conf.CARD_PROVIDERS[provider_id]
    return None, None
