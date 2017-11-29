#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""Inheritance from :class:`redis.connection.Connection` and make it
asynchronous.
"""
from __future__ import unicode_literals, print_function, division

import sys
import socket
import weakref

from select import select

from tornado import gen
from tornado.tcpclient import TCPClient
from tornado.iostream import StreamClosedError
from redis.connection import (
    Connection, ConnectionError, PythonParser, SocketBuffer,
    SERVER_CLOSED_CONNECTION_ERROR, TimeoutError, SYM_CRLF, DefaultParser)
from redis._compat import byte_to_chr, nativestr
from redis.exceptions import (
    InvalidResponse, RedisError, AuthenticationError,
    ResponseError)


class StreamBuffer(SocketBuffer):
    def __init__(self, stream, socket_read_size):
        super(StreamBuffer, self).__init__(None, socket_read_size)
        self._stream = stream

    @gen.coroutine
    def _read_from_stream(self, length=None):
        buf = self._buffer
        buf.seek(self.bytes_written)
        marker = 0

        try:
            while True:
                try:
                    data = yield self._stream.read_until_regex(b'\r\n')
                except StreamClosedError:
                    raise socket.error(SERVER_CLOSED_CONNECTION_ERROR)

                buf.write(data)

                data_length = len(data)
                self.bytes_written += data_length
                marker += data_length

                if length is not None and length > marker:
                    continue
                break
        except socket.timeout:
            raise TimeoutError("Timeout reading from stream")
        except socket.error:
            e = sys.exc_info()[1]
            raise ConnectionError(
                "Error while reading from stream: %s" % (e.args, ))

    @gen.coroutine
    def read(self, length):
        length = length + 2

        if length > self.length:
            yield self._read_from_stream(length - self.length)

        self._buffer.seek(self.bytes_read)
        data = self._buffer.read(length)
        self.bytes_read += len(data)

        if self.bytes_read == self.bytes_written:
            self.purge()

        raise gen.Return(data[:-2])

    @gen.coroutine
    def readline(self):
        buf = self._buffer
        buf.seek(self.bytes_read)
        data = buf.readline()

        while not data.endswith(SYM_CRLF):
            yield self._read_from_stream()
            buf.seek(self.bytes_read)
            data = buf.readline()

        self.bytes_read += len(data)

        if self.bytes_read == self.bytes_written:
            self.purge()

        raise gen.Return(data[:-2])


class AsyncParser(PythonParser):
    """ Parser class for connections using tornado asynchronous """

    def __init__(self, socket_read_size):
        self.socket_read_size = socket_read_size
        self.encoder = None
        self._stream = None
        self._buffer = None

    def __del__(self):
        try:
            self.on_disconnect()
        except Exception:
            pass

    def on_connect(self, connection):
        """ Called when stream connects """
        self._stream = weakref.proxy(connection._stream)
        self._buffer = StreamBuffer(self._stream, self.socket_read_size)
        self.encoder = connection.encoder

    def on_disconnect(self):
        if self._stream is not None:
            self._stream.close()
            self._stream = None

        if self._buffer is not None:
            self._buffer.close()
            self._buffer = None

        self.encoding = None

    def can_read(self):
        return self._buffer and bool(self._buffer.length)

    @gen.coroutine
    def read_response(self):
        response = yield self._buffer.readline()

        if not response:
            raise ConnectionError(SERVER_CLOSED_CONNECTION_ERROR)

        byte, response = byte_to_chr(response[0]), response[1:]

        if byte not in ('-', '+', ':', '$', '*'):
            raise InvalidResponse("Protocol Error: %s, %s" %
                                  (str(byte), str(response)))

        # server returned an error
        if byte == '-':
            response = nativestr(response)
            error = self.parse_error(response)
            # if the error is a ConnectionError, raise immediately so the user
            # is notified
            if isinstance(error, ConnectionError):
                raise error
            # otherwise, we're dealing with a ResponseError that might belong
            # inside a pipeline response. the connection's read_response()
            # and/or the pipeline's execute() will raise this error if
            # necessary, so just return the exception instance here.
            raise gen.Return(error)
        # single value
        elif byte == '+':
            pass
        # int value
        elif byte == ':':
            response = int(response)
        # bulk response
        elif byte == '$':
            length = int(response)
            if length == -1:
                raise gen.Return(None)
            response = yield self._buffer.read(length)
        # multi-bulk response
        elif byte == '*':
            length = int(response)
            if length == -1:
                raise gen.Return(None)
            response = []

            for i in range(length):
                res = yield self.read_response()
                response.append(res)

        if isinstance(response, bytes):
            response = self.encoder.decode(response)

        raise gen.Return(response)


class AsyncConnection(Connection, TCPClient):
    def __init__(self, *args, **kwargs):

        TCPClient.__init__(self, kwargs.pop("resolver", None),
                           kwargs.pop("io_loop", None))

        Connection.__init__(self, parser_class=AsyncParser, *args, **kwargs)

        self._stream = None

    @gen.coroutine
    def connect(self):

        if self._stream:
            return
        try:
            stream = yield self._connect()
        except socket.error:
            e = sys.exc_info()[1]
            raise ConnectionError(self._error_message(e))

        self._stream = stream

        try:
            yield self.on_connect()
        except RedisError:
            self.disconnect()
            raise

    @gen.coroutine
    def _connect(self):
        stream = yield TCPClient.connect(self, self.host, self.port)
        raise gen.Return(stream)

    @gen.coroutine
    def on_connect(self):
        self._parser.on_connect(self)

        if self.password:
            yield self.send_command('AUTH', self.password)

            response = yield self.read_response()
            if nativestr(response) != 'OK':
                raise AuthenticationError('Invalid Password')

        if self.db:
            yield self.send_command('SELECT', self.db)
            response = yield self.read_response()
            if nativestr(response) != 'OK':
                raise ConnectionError('Invalid Database')

    def disconnect(self):
        "Disconnects from the Redis server"
        self._parser.on_disconnect()
        if self._stream is None:
            return
        try:
            self._stream.close()
        except StreamClosedError:
            pass
        self._stream = None

    @gen.coroutine
    def send_packed_command(self, command):
        "Send an already packed command to the Redis server"
        if not self._sock:
            yield self.connect()
        try:
            if isinstance(command, str):
                command = [command]
            for item in command:
                yield self._stream.write(item)

        except StreamClosedError:
            self.disconnect()
            raise TimeoutError("Timeout writing to socket")
        except socket.error:
            e = sys.exc_info()[1]
            self.disconnect()
            if len(e.args) == 1:
                _errno, errmsg = 'UNKNOWN', e.args[0]
            else:
                _errno, errmsg = e.args
            raise ConnectionError("Error %s while writing to socket. %s." %
                                  (_errno, errmsg))
        except:
            self.disconnect()
            raise

    @gen.coroutine
    def send_command(self, *args):
        "Pack and send a command to the Redis server"
        yield self.send_packed_command(self.pack_command(*args))

    @gen.coroutine
    def can_read(self, timeout=0):
        "Poll the socket to see if there's data that can be read."
        sock = self._stream
        if not sock:
            yield self.connect()
            sock = self._stream.socket
        raise gen.Return(self._parser.can_read() or
                         bool(select([sock], [], [], timeout)[0]))

    @gen.coroutine
    def read_response(self):
        "Read the response from a previously sent command"
        try:
            response = yield self._parser.read_response()
        except:
            self.disconnect()
            raise

        if isinstance(response, ResponseError):
            raise response

        raise gen.Return(response)

    def to_blocking_connection(self, socket_read_size=65536):
        """ Convert asynchronous connection to blocking socket connection
        """
        conn = Connection(
            self.host, self.port, self.db, self.password, self.socket_timeout,
            self.socket_connect_timeout, self.socket_keepalive,
            self.socket_keepalive_options, self.retry_on_timeout,
            self.encoding, self.encoding_errors, self.decode_responses,
            DefaultParser, socket_read_size)

        conn._sock = self._stream.socket
        return conn
