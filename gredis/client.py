#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   15/04/15 17:16:34
#   Desc    :   Asynchronous
#
from __future__ import absolute_import, print_function, division, with_statement

from tornado import gen

from redis.client import StrictRedis, Redis
from redis.exceptions import ConnectionError, TimeoutError
from redis.connection import Connection, ConnectionPool

from gredis.connection import AsyncConnection


def _construct_connection_pool(pool):
    """ Construct a blocking socket connection pool based on asynchronous pool
    """
    _pool = ConnectionPool(Connection, pool.max_connections, **pool.connection_kwargs)

    return _pool


class AsyncStrictRedis(StrictRedis):

    def __init__(self, *args, **kwargs):
        StrictRedis.__init__(self, *args, **kwargs)
        self.connection_pool.connection_class = AsyncConnection

    # COMMAND EXECUTION AND PROTOCOL PARSING
    @gen.coroutine
    def execute_command(self, *args, **options):
        "Execute a command and return a parsed response"
        pool = self.connection_pool
        command_name = args[0]
        connection = pool.get_connection(command_name, **options)
        try:
            yield connection.send_command(*args)
            result = yield self.parse_response(connection, command_name, **options)
            raise gen.Return(result)
        except (ConnectionError, TimeoutError) as e:
            connection.disconnect()
            if not connection.retry_on_timeout and isinstance(e, TimeoutError):
                raise
            connection.send_command(*args)
            result = yield self.parse_response(connection, command_name, **options)
            raise  gen.Return(result)
        finally:
            pool.release(connection)

    @gen.coroutine
    def parse_response(self, connection, command_name, **options):
        response = yield connection.read_response()
        if command_name in self.response_callbacks:
            raise gen.Return(self.response_callbacks[command_name](response, **options))
        raise gen.Return(response)

    def pipeline(self, *args, **kwargs):
        obj = self.to_blocking_client()
        return obj.pipeline(*args, **kwargs)

    def to_blocking_client(self):
        """ Convert asynchronous client to blocking socket client
        """
        obj = StrictRedis()
        obj.connection_pool = _construct_connection_pool(self.connection_pool)
        return obj


class AsyncRedis(AsyncStrictRedis):
    def pubsub(self, **kwargs):
        obj = self.to_blocking_client()
        return obj.pubsub(**kwargs)

    def to_blocking_client(self):
        """ Convert asynchronous client to blocking socket client
        """
        obj = Redis()
        obj.connection_pool = _construct_connection_pool(self.connection_pool)
        return obj
