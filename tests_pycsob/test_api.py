# coding: utf-8
import os
import json
from unittest import TestCase
from urllib3_mock import Responses

from pycsob import conf, utils
from pycsob.client import CsobClient

KEY_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'fixtures', 'test.key'))

responses = Responses(package='requests.packages.urllib3')


class CsobClientTests(TestCase):

    def setUp(self):
        self.c = CsobClient(merchant_id='MERCHANT',
                            base_url='https://gw.cz',
                            private_key_file=KEY_PATH,
                            csob_pub_key_file=KEY_PATH)

    @responses.activate
    def test_echo_post(self):
        resp_payload = utils.mk_payload(KEY_PATH, pairs=(
            ('dttm', utils.dttm()),
            ('resultCode', conf.RETURN_CODE_OK),
            ('resultMessage', 'OK'),
        ))
        responses.add(responses.POST, '/echo/', body=json.dumps(resp_payload),
                      status=200, content_type='application/json')
        out = self.c.echo()
        assert out['dttm'] == resp_payload['dttm']
        assert out['resultCode'] == conf.RETURN_CODE_OK

    @responses.activate
    def test_echo_get(self):
        payload = utils.mk_payload(KEY_PATH, pairs=(
            ('merchantId', self.c.merchant_id),
            ('dttm', utils.dttm()),
        ))
        resp_payload = utils.mk_payload(KEY_PATH, pairs=(
            ('dttm', utils.dttm()),
            ('resultCode', conf.RETURN_CODE_OK),
            ('resultMessage', 'OK'),
        ))
        url = utils.mk_url('/', 'echo/', payload)
        responses.add(responses.GET, url, body=json.dumps(resp_payload),
                      status=200, content_type='application/json')
        out = self.c.echo(method='GET')
        assert out['dttm'] == resp_payload['dttm']
        assert out['resultCode'] == conf.RETURN_CODE_OK

    def test_sign_message(self):
        msg = 'Příliš žluťoučký kůň úpěl ďábelské ódy.'
        payload = utils.mk_payload(KEY_PATH, pairs=(
            ('merchantId', self.c.merchant_id),
            ('dttm', utils.dttm()),
            ('description', msg)
        ))
        assert payload['description'] == msg
        signature = payload['signature']
        del payload['signature']
        assert utils.verify(payload, signature, KEY_PATH)
