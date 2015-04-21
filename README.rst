gredis
======
gRedis is an asynchronous client library of Redis written with `Tornado <https://github.com/tornadoweb/tornado>`_ coroutine.

gRedis is standing on the shoulders of giants:

* `redis-py <https://github.com/andymccurdy/redis-py>`_
* `Tornado <https://github.com/tornadoweb/tornado>`_

Installation
============

.. code-block:: shell

    pip install gredis

OR

.. code-block:: shell

    easy_install gredis


OR 
    
.. code-block:: shell

    git clone https://github.com/coldnight/gredis
    cd gredis
    python setup.py install

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
            redis = client.to_blocking_client()
            ret2 = redis.incr("key")
            self.write(str(ret + ret2))

Pub/Sub
-------
.. code-block:: python

    from tornado import gen
    from tornado import web
    from gredis.client import AsyncRedis

    client = AsyncRedis("ip.or.host", 6379)

    class PubSubHandler(web.RequestHandler):

        @gen.coroutine
        def get(self):
            pubsub = client.pubsub()
            channel = "test"
            yield pubsub.subscribe(channel)
            response = yield pubsub.get_message(True)
            assert response["type"] == "subscribe"
            response = yield pubsub.get_message(True)
            assert response["type"] == "message"
            self.write(response['data'])

        @gen.coroutine
        def post(self):
            yield client.publish(channel, "test")


Not Implementation
==================

* pipeline
