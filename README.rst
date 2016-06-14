pycsob
======

Python client for ČSOB payment gateway

Latest CircleCI build:

    .. image:: https://circleci.com/gh/whit/pycsob.svg?style=svg
       :target: https://circleci.com/gh/whit/pycsob

Install:
--------

.. code-block:: bash

    pip install pycsob

Run tests:
----------

.. code-block:: bash

    python setup.py test

Usage:
------

.. code-block:: python

    from pycsob.client import CsobClient, CsobClientError
    from pycsob import conf

    c = CsobClient('MERCHANT_ID', 'https://iapi.iplatebnibrana.csob.cz/api/v1.6/',
                   '/path/to/your/private.key',
                   '/path/to/mips_iplatebnibrana.csob.cz.pub')

    # init payment
    # note: total_amount = 20000.00
    r = c.payment_init(1, 2000000, 'https://return.url/', 'Some note', customer_id='a@a.aa')

    assert r['resultCode'] == conf.RETURN_CODE_OK
    c.payment_status(r['payId'])
    c.payment_close(r['payId'])
    # ...

    # init payment and also create template for one-click payment
    r = c.payment_init(2, 2000000, 'https://return.url/', 'Some note', customer_id='a@a.aa',
                       return_method='POST', pay_operation='oneclickPayment')

    # init one-click payment
    r = c.oneclick_init(r['payId'], 123, 10000)

    # start (process) one-click payment
    r = c.oneclick_start(r['payId'])

