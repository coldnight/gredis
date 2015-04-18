gredis
======
gRedis is a asynchronous client library of Redis written with `Tornado <https://github/tornadoweb/tornado>`_ coroutine.

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

Not Implementation
==================

* pubsub
* pipeline
