pycsob
======

.. image:: https://circleci.com/gh/TwistoPayments/pycsob.svg?style=svg
   :target: https://circleci.com/gh/TwistoPayments/pycsob

.. image:: https://badge.fury.io/py/pycsob.svg
    :target: https://badge.fury.io/py/pycsob

Install:
--------

.. code-block:: bash

    pip install pycsob

Run tests:
----------

.. code-block:: bash

    python setup.py test

Basic usage:
------------

.. code-block:: python

    from pycsob.client import CsobClient
    c = CsobClient('MERCHANT_ID', 'https://iapi.iplatebnibrana.csob.cz/api/v1.6/',
                   '/path/to/your/private.key',
                   '/path/to/mips_iplatebnibrana.csob.cz.pub')

Initialize payment. Outputs are requests's responses enriched by some properties
like ``payload`` or ``extensions``.

.. code-block:: python

    r = c.payment_init(14, 1000000, 'http://twisto.dev/', 'Tesovaci nakup', customer_id='a@a.aa',
                       return_method='GET', pay_operation='payment')
    r.payload
    #[Out]# OrderedDict([('payId', 'b627c1e4e60fcBF'),
    #[Out]#              ('dttm', '20160615104254'),
    #[Out]#              ('resultCode', 0),
    #[Out]#              ('resultMessage', 'OK'),
    #[Out]#              ('paymentStatus', 1)])

After payment init get URL to redirect to for payId obtained from previous step.

.. code-block:: python

    c.get_payment_process_url('b627c1e4e60fcBF')
    #[Out]# 'https://iapi.iplatebnibrana.csob.cz/api/v1.6/payment/process/MERCHANT_ID/b627c1e4e60fcBF/20160615104318/bla-bla-bla'

After user have payment processed, browser redirects him to URL provided in ``payment_init()``.
You can check payment status.

.. code-block:: python

    c.payment_status('b627c1e4e60fcBF').payload
    #[Out]# OrderedDict([('payId', 'b627c1e4e60fcBF'),
    #[Out]#              ('dttm', '20160615104501'),
    #[Out]#              ('resultCode', 0),
    #[Out]#              ('resultMessage', 'OK'),
    #[Out]#              ('paymentStatus', 7),
    #[Out]#              ('authCode', '042760')])

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
    #[Out]#              ('paymentStatus', 1)])

    r = c.oneclick_start('ff7d3e7c6c4fdBF')
    r.payload
    #[Out]# OrderedDict([('payId', 'ff7d3e7c6c4fdBF'),
    #[Out]#              ('dttm', '20160615104619'),
    #[Out]#              ('resultCode', 0),
    #[Out]#              ('resultMessage', 'OK'),
    #[Out]#              ('paymentStatus', 2)])

    r = c.payment_status('ff7d3e7c6c4fdBF')
    r.payload
    #[Out]# OrderedDict([('payId', 'ff7d3e7c6c4fdBF'),
    #[Out]#              ('dttm', '20160615104643'),
    #[Out]#              ('resultCode', 0),
    #[Out]#              ('resultMessage', 'OK'),
    #[Out]#              ('paymentStatus', 7),
    #[Out]#              ('authCode', '168164')])

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
    #[Out]#  'https://iapi.iplatebnibrana.csob.cz/api/v1.6/payment/status/M1E3CB2577/1e058ff1d0d5aBF/20160615111034/HQKDHz7DTHL0lCn6OrAv%2BKQjGEr8KtdF42czAGCngCG0gWbuYTfJfO%2B5rHwAEWCl1XKiClYngLBI7Lu2mCJG8AP2Od7%2BAa5VXWcIjs0mSAsP60irR7M4Xl1NsXPe4bEhXAvAJU4yz3oV2vZ68QRB9vE7mk6OaLQade48yEFmX83FJPDQ4RSBOUqD3JPrKMMZ%2BkNEz0%2FMh94X7Zx3DrtwUVdKEyuX8Zf2MYwqzQh7mNBW6EZKxt7yKwS%2B0108GalXoD1n7ctjbtcyrbFAFKKLDgPNf%2BMlLBt8cwSSQ6J2xigI3P9T32L5YUg25kKr%2B4Dy%2FnwOKDntDszbGXQZdIBnTQ%3D%3D'

    r.status_code
    #[Out]# 200

Please look at the code for other available methods and their usage.
