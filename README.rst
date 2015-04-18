gredis
======
gRedis is a asynchronous client library of Redis written with `Tornado <https://github/tornadoweb/tornado>`_ coroutine.

Usage
=====

.. code-block:: python

    from tornado import gen
    from tornado import web
    from gredis.client import AsyncRedis

    client = AsyncRedis("ip.or.host", 6379)

    class DemoHandler(web.RequestHandler):

        @gen.coroutine
        def get(self):
            ret = yield client.incr("key")
            redis = client.to_socket_client()
            ret2 = redis.incr(key)
            self.write(ret + ret2)

Not Implementation
==================

* pubsub
* pipeline
