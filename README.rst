pycsob
======

.. image:: https://badge.fury.io/py/pycsob.svg
    :target: https://badge.fury.io/py/pycsob

.. image:: https://img.shields.io/pypi/dm/pycsob.svg
	   :target: https://pypi.python.org/pypi/pycsob

.. image:: https://img.shields.io/pypi/status/pycsob.svg
	   :target: https://pypi.python.org/pypi/pycsob

.. image:: https://img.shields.io/pypi/pyversions/pycsob.svg
	   :target: https://pypi.python.org/pypi/pycsob

.. image:: https://img.shields.io/pypi/l/pycsob.svg
	   :target: https://raw.githubusercontent.com/TwistoPayments/pycsob/master/LICENSE

Install:
--------

.. code-block:: bash

    pip install pycsob

Run tests:
----------

.. code-block:: bash

    python setup.py test


eAPI-v1.9 Wiki
--------------

https://github.com/csob/paymentgateway/wiki/eAPI-v1.9

Caution! This module implements only `Basic Payment <https://github.com/csob/paymentgateway/wiki/Basic-Payment>`_,
`Custom Payment <https://github.com/csob/paymentgateway/wiki/Custom-Payment>`_ and
`Methods for ČSOB Payment Button <https://github.com/csob/paymentgateway/wiki/Methods-for-%C4%8CSOB-Payment-Button>`_ from API v1.9.

Basic usage:
------------
 
.. code-block:: python

    from pycsob.client import CsobClient
    c = CsobClient('MERCHANT_ID', 'https://iapi.iplatebnibrana.csob.cz/api/v1.9/',
                   '/path/to/your/private.key',
                   '/path/to/mips_iplatebnibrana.csob.cz.pub')

Initialize payment. Outputs are requests's responses enriched by some properties
like ``payload`` or ``extensions``.

.. code-block:: python

    r = c.payment_init(14, 1000000, 'http://twisto.dev/', 'Tesovaci nakup', customer_id='a@a.aa',
                       return_method='GET', pay_operation='payment', merchant_data=[1, 2, 3])
    r.payload
    #[Out]# OrderedDict([('payId', 'b627c1e4e60fcBF'),
    #[Out]#              ('dttm', '20160615104254'),
    #[Out]#              ('resultCode', 0),
    #[Out]#              ('resultMessage', 'OK'),
    #[Out]#              ('paymentStatus', 1),
    #[Out]#              ('dttime', datetime.datetime(2016, 6, 15, 10, 42, 54))])

After payment init get URL to redirect to for ``payId`` obtained from previous step.

.. code-block:: python

    c.get_payment_process_url('b627c1e4e60fcBF')
    #[Out]# 'https://iapi.iplatebnibrana.csob.cz/api/v1.9/payment/process/MERCHANT_ID/b627c1e4e60fcBF/20160615104318/bla-bla-bla'

After user have payment processed, browser redirects him to URL provided in ``payment_init()``.
You can check payment status.

.. code-block:: python

    c.payment_status('b627c1e4e60fcBF').payload
    #[Out]# OrderedDict([('payId', 'b627c1e4e60fcBF'),
    #[Out]#              ('dttm', '20160615104501'),
    #[Out]#              ('resultCode', 0),
    #[Out]#              ('resultMessage', 'OK'),
    #[Out]#              ('paymentStatus', 7),
    #[Out]#              ('authCode', '042760'),
    #[Out]#              ('dttime', datetime.datetime(2016, 6, 15, 10, 45, 1))])

Custom payments are initialized with ``c.payment_init(pay_operation='customPayment')``, you can optionally set 
payment validity by ``custom_expiry='YYYYMMDDhhmmss'``.

.. code-block:: python

    r = c.payment_init(14, 1000000, 'http://twisto.dev/', 'Testovaci nakup', return_method='POST',
                       pay_operation='customPayment', custom_expiry='20160630120000')
    r.payload
    #[Out]# OrderedDict([('payId', 'b627c1e4e60fcBF'),
    #[Out]#              ('dttm', '20160615104254'),
    #[Out]#              ('resultCode', 0),
    #[Out]#              ('resultMessage', 'OK'),
    #[Out]#              ('paymentStatus', 1)]),
    #[Out]#              ('customerCode', 'E61EC8'),
    #[Out]#              ('dttime', datetime.datetime(2016, 6, 15, 10, 42, 54))])

Send (by whatever means) obtained ``customerCode`` to customer who can then perform payment anytime within its validity
on URL ``https://platebnibrana.csob.cz/payment/{customerCode}`` (``c.get_payment_process_url`` is not applicable
for custom payments).

You can also use one-click payment methods. For this you need
to call ``c.payment_init(pay_operation='oneclickPayment')``. After this transaction confirmed
you can use obtained ``payId`` as template for one-click payment.

.. code-block:: python

    r = c.oneclick_init('1e058ff1d0d5aBF', 666, 10000)
    r.payload
    #[Out]# OrderedDict([('payId', 'ff7d3e7c6c4fdBF'),
    #[Out]#              ('dttm', '20160615104532'),
    #[Out]#              ('resultCode', 0),
    #[Out]#              ('resultMessage', 'OK'),
    #[Out]#              ('paymentStatus', 1),
    #[Out]#              ('dttime', datetime.datetime(2016, 6, 15, 10, 45, 32))])

    r = c.oneclick_start('ff7d3e7c6c4fdBF')
    r.payload
    #[Out]# OrderedDict([('payId', 'ff7d3e7c6c4fdBF'),
    #[Out]#              ('dttm', '20160615104619'),
    #[Out]#              ('resultCode', 0),
    #[Out]#              ('resultMessage', 'OK'),
    #[Out]#              ('paymentStatus', 2),
    #[Out]#              ('dttime', datetime.datetime(2016, 6, 15, 10, 46, 19))])

    r = c.payment_status('ff7d3e7c6c4fdBF')
    r.payload
    #[Out]# OrderedDict([('payId', 'ff7d3e7c6c4fdBF'),
    #[Out]#              ('dttm', '20160615104643'),
    #[Out]#              ('resultCode', 0),
    #[Out]#              ('resultMessage', 'OK'),
    #[Out]#              ('paymentStatus', 7),
    #[Out]#              ('authCode', '168164'),
    #[Out]#              ('dttime', datetime.datetime(2016, 6, 15, 10, 46, 43))])

Of course you can use standard requests's methods on ``response`` object.

.. code-block:: python

    r.json()
    #[Out]# {'authCode': '047256',
    #[Out]#  'dttm': '20160615104717',
    #[Out]#  'payId': '1e058ff1d0d5aBF',
    #[Out]#  'paymentStatus': 7,
    #[Out]#  'resultCode': 0,
    #[Out]#  'resultMessage': 'OK',
    #[Out]#  'signature': 'foh4asfoxy40QRmwChJQwNkfT+PBmI3a7jQ+g2M75RpE2uJNqWCCmrhF8TPhcJ6rcyKSttB/ZZrd0gh9BQDgByMtyPG/rv0Jn3kQeuAryJfOW4nuFj86tr/queHD8ZZ248PwOkT5Zo2uTz+QRCrv/n4he+TWkFoVsm94AoSTK3O1SBDyLiOi3njv/ZWm+z/Z9iK55xBwuSs0v5lzxNJ9vJpjIwWlAB1qEkrWZuGZHrNtAib9NxytO0ruWyG3U4H+B8ioJOUlWrAbCHhmKvmArmYi23fup2486v/9s5SCl0fS7PQUNdiDJpZHxnRkVZZXwZM2sPyacgayvYb+khlBRg=='}

    r = c.payment_status('1e058ff1d0d5aBF')

    r.request.url
    #[Out]#  'https://iapi.iplatebnibrana.csob.cz/api/v1.9/payment/status/M1E3CB2577/1e058ff1d0d5aBF/20160615111034/HQKDHz7DTHL0lCn6OrAv%2BKQjGEr8KtdF42czAGCngCG0gWbuYTfJfO%2B5rHwAEWCl1XKiClYngLBI7Lu2mCJG8AP2Od7%2BAa5VXWcIjs0mSAsP60irR7M4Xl1NsXPe4bEhXAvAJU4yz3oV2vZ68QRB9vE7mk6OaLQade48yEFmX83FJPDQ4RSBOUqD3JPrKMMZ%2BkNEz0%2FMh94X7Zx3DrtwUVdKEyuX8Zf2MYwqzQh7mNBW6EZKxt7yKwS%2B0108GalXoD1n7ctjbtcyrbFAFKKLDgPNf%2BMlLBt8cwSSQ6J2xigI3P9T32L5YUg25kKr%2B4Dy%2FnwOKDntDszbGXQZdIBnTQ%3D%3D'

    r.status_code
    #[Out]# 200

Logging:
--------

If you need to solve a problem, you can turn on request and response logging.
In the settings, set the logger ``pycsob`` to the ``INFO`` level.
If you set level ``DEBUG``, the response headers will also be displayed.

For Django set site_cfg/settings.py:

.. code-block:: python

    LOGGING = {
        ...
        'loggers': {
            ...
            'pycsob': {
                'level': 'DEBUG',  # or INFO
            }
        ...
        }
    }

Or in general for client logging to the console:

.. code-block:: python

    import logging
    from pycsob.client import CsobClient

    logger = logging.getLogger("pycsob")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())

Then display a communication on the console:

.. code-block:: python

    from pycsob.client import CsobClient

    KEY_PATH = 'tests_pycsob/fixtures/test.key'
    CSOB_PUB_KEY_PATH = 'yourpath/csob-public.key'
    client = CsobClient(merchant_id='MERCHANT', base_url='https://iapi.iplatebnibrana.csob.cz',
                        private_key_file=KEY_PATH, csob_pub_key_file=CSOB_PUB_KEY_PATH)
    client.echo()

.. code-block::

    INFO Pycsob request POST: https://iapi.iplatebnibrana.csob.cz/echo/; Data: {"merchantId": "MERCHANT", "dttm": "20211004143621", "signature": "bOAdjgAdiCV4Eb83cv/Whhkk18+1ZHXyZDTF3qLLalxQQ6RbS5dr3e04TlLut7SZ366wMlCycRm/OcMYtzhuWg=="}; Json: None; {}
    DEBUG Pycsob request headers: {'content-type': 'application/json', 'user-agent': 'py-csob/0.7.0', 'Content-Length': '415'}
    INFO Pycsob response: [404] <html><body>No service was found.</body></html>
    DEBUG Pycsob response headers: {'Date': 'Mon, 04 Oct 2021 12:34:43 GMT', 'Content-Type': 'text/html;charset=utf-8', 'Content-Length': '47', 'Connection': 'keep-alive', 'Strict-Transport-Security': '31536000', 'X-Content-Type-Options': 'nosniff', 'X-XSS-Protection': '1; mode=block', 'Set-Cookie': 'COOKIE=!75Nl7TEDKeDZ7K1WBRXghHdGYkGcpNs67eHiqFqNIhpMvkjn8bZpwV3eFt/NETwOEPOM7MWItRbl0PcBMrVKU3ry41CzfobdNVeS+7zE6Q==; path=/; Secure; HttpOnly, TS0189cac5=0109e0ddfbbb13789e164510c58ee0d90933527dc24d6c0e29c511be545848b36cf506bb150c4e70c563bbbd96568176f61f72bfc8238416e0fde42a90cb18385bda35fd54; Path=/; Secure; HTTPOnly, TS774c8e5c029=08fdf8696aab2800cb7e1ec4cd5e34e549d7daafc75532c101d951da6a0ee591bb5e45a973ba8c2e249dfc6539005ac4; Max-Age=30;Path=/', 'P3P': 'CP="{}"'}

-----

Please look at the code for other available methods and their usage.
