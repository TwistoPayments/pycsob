from . import __versionstr__

# app conf
HEADERS = {
    'content-type': 'application/json',
    'user-agent': 'py-csob/%s' % __versionstr__,
}
EMPTY_VALUES = ('', None, [], (), {})
RESPONSE_KEYS = ('payId', 'customerId', 'dttm', 'resultCode', 'resultMessage', 'paymentStatus', 'authCode',
                 'merchantData')

# available languages and currencies
LANGUAGES = 'CZ', 'EN', 'DE', 'SK', 'HU', 'IT', 'JP', 'PL', 'PT', 'RO', 'RU', 'SK', 'ES', 'TR', 'VN'
CURRENCIES = 'CZK', 'EUR', 'USD', 'GBP'

# CSOB gw statuses
PAYMENT_STATUS_INIT = 1
PAYMENT_STATUS_PROCESS = 2
PAYMENT_STATUS_CANCELLED = 3
PAYMENT_STATUS_CONFIRMED = 4
PAYMENT_STATUS_REVERSED = 5
PAYMENT_STATUS_REJECTED = 6
PAYMENT_STATUS_WAITING = 7
PAYMENT_STATUS_RECOGNIZED = 8
PAYMENT_STATUS_RETURN_WAITING = 9
PAYMENT_STATUS_RETURNED = 10

RETURN_CODE_OK = 0
RETURN_CODE_PARAM_MISSING = 100
RETURN_CODE_PARAM_INVALID = 110
RETURN_CODE_MERCHANT_BLOCKED = 120
RETURN_CODE_SESSION_EXPIRED = 130
RETURN_CODE_PAYMENT_NOT_FOUND = 140
RETURN_CODE_PAYMENT_NOT_IN_VALID_STATE = 150
RETURN_CODE_OPERATION_NOT_ALLOWED = 180
RETURN_CODE_CUSTOMER_NOT_FOUND = 800
RETURN_CODE_NO_SAVED_CARDS = 810
RETURN_CODE_FOUND_SAVED_CARDS = 820
RETURN_CODE_INTERNAL_ERROR = 900

RESULT_STATUSES = {
    RETURN_CODE_OK: 'OK',
    RETURN_CODE_PARAM_MISSING: 'Missing parameter',
    RETURN_CODE_PARAM_INVALID: 'Invalid parameter',
    RETURN_CODE_MERCHANT_BLOCKED: 'Merchant blocked',
    RETURN_CODE_SESSION_EXPIRED: 'Session expired',
    RETURN_CODE_PAYMENT_NOT_FOUND: 'Payment not found',
    RETURN_CODE_PAYMENT_NOT_IN_VALID_STATE: 'Payment not in valid state',
    RETURN_CODE_OPERATION_NOT_ALLOWED: 'Operation not allowed',
    RETURN_CODE_CUSTOMER_NOT_FOUND: 'Customer not found',
    RETURN_CODE_NO_SAVED_CARDS: 'Customer found, no saved card(s)',
    RETURN_CODE_FOUND_SAVED_CARDS: 'Customer found, found saved card(s)',
    RETURN_CODE_INTERNAL_ERROR: 'Internal error',
}

PAYMENT_STATUSES = {
    PAYMENT_STATUS_INIT: 'Initialized',
    PAYMENT_STATUS_PROCESS: 'In process',
    PAYMENT_STATUS_CANCELLED: 'Cancelled',
    PAYMENT_STATUS_CONFIRMED: 'Confirmed',
    PAYMENT_STATUS_REVERSED: 'Reversed',
    PAYMENT_STATUS_REJECTED: 'Rejected',
    PAYMENT_STATUS_WAITING: 'Waiting',
    PAYMENT_STATUS_RECOGNIZED: 'Recognized',
    PAYMENT_STATUS_RETURN_WAITING: 'Return waiting',
    PAYMENT_STATUS_RETURNED: 'Returned'
}

HTTP_STATUSES = {
    200: 'OK',
    400: 'Bad Request',
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    429: 'Too Many Requests',
    503: 'Service Unavailable'
}

HTTP_TIMEOUT = (3.05, 12)  # http://docs.python-requests.org/en/master/user/advanced/#timeouts

# CARD PROVIDERS
CARD_PROVIDER_VISA = 4
CARD_PROVIDER_MC = 5
CARD_PROVIDER_AMEX = 3
CARD_PROVIDER_DINERS = 30
CARD_PROVIDER_JCB = 21

CARD_PROVIDERS = {
    CARD_PROVIDER_VISA: 'Visa',
    CARD_PROVIDER_MC: 'MasterCard',
    CARD_PROVIDER_DINERS: 'Diners Club',
    CARD_PROVIDER_AMEX: 'American Express',
    CARD_PROVIDER_JCB: 'JCB'
}
