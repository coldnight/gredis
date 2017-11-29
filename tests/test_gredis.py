#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   15/04/15 17:10:57
#   Desc    :
#
from __future__ import absolute_import, print_function, division, with_statement

import os
from tornado.testing import gen_test, AsyncTestCase

from gredis.client import AsyncRedis


class GRedisTest(AsyncTestCase):
    def setUp(self):
        super(GRedisTest, self).setUp()
        self.client = AsyncRedis(
            "192.168.1.50", 6379, encoding="utf8",
            decode_responses=True,
        )

    @gen_test
    def test_get_set(self):
        key = "g_test_key"
        yield self.client.set(key, "w")
        # print("set")
        future = self.client.get(key)
        response = yield future
        self.assertEqual(response, "w")

    @gen_test
    def test_list(self):
        key = "g_test_list_key"
        self.client.delete(key)
        yield self.client.lpush(key, "w")
        key, response = yield self.client.blpop(key)
        print(response)
        self.assertEqual(response, "w")
        lst = ['a', 'b', 'c']
        for i in lst:
            yield self.client.rpush(key, i)
        _lst = yield self.client.lrange(key, 0, -1)
        self.assertListEqual(lst, _lst)

    @gen_test
    def test_to_blocking_client(self):
        key = "g_test_1_key"

        yield self.client.set(key, "gredis")
        client = self.client.to_blocking_client()
        result = client.get(key)
        self.assertEqual(result, "gredis")
        asyc_result = yield self.client.get(key)
        self.assertEqual(asyc_result, "gredis")

    @gen_test
    def test_blocking_pipeline(self):
        key = "g_pipeline_test"
        key1 = "g_pipeline_test1"
        pipeline = self.client.pipeline()

        pipeline.set(key, "gredis")
        pipeline.set(key1, "gredis1")
        pipeline.execute()

        ret = yield self.client.get(key)
        self.assertEqual(ret, "gredis")
        ret1 = yield self.client.get(key1)
        self.assertEqual(ret1, "gredis1")

    @gen_test
    def test_async_pubsub(self):
        pubsub = self.client.pubsub()
        channel = "test"
        yield pubsub.subscribe(channel)
        response = yield pubsub.get_message(True)
        self.assertEqual(response["type"], "subscribe")
        yield self.client.publish(channel, "test")
        response = yield pubsub.get_message(True)
        self.assertEqual(response["type"], "message")
        self.assertEqual(response["data"], "test")
