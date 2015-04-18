#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   15/04/18 13:21:25
#   Desc    :   A Chat Demo written with gredis
#
""" A chat demo based on list type of Redis, written with gredis """
from __future__ import absolute_import, print_function, division, with_statement

import uuid

from tornado import gen
from tornado import web
from tornado import ioloop
from gredis.client import AsyncRedis

client = AsyncRedis("192.168.1.50")


CHAT_PEER_KEY = "chat::peer"


class ChatHandler(web.RequestHandler):
    @gen.coroutine
    def get(self, chat_id=None):
        if not chat_id:
            chat_id = uuid.uuid1().get_hex()
            dist_id = uuid.uuid1().get_hex()
            yield client.hmset(CHAT_PEER_KEY, {chat_id: dist_id})
            yield client.hmset(CHAT_PEER_KEY, {dist_id: chat_id})
            self.redirect("/chat/{0}".format(chat_id))
        else:
            dist_id = yield client.hget(CHAT_PEER_KEY, chat_id)

        self.render("chat.html",
                    url="{0}://{1}/chat/{2}".format(self.request.protocol,
                                                    self.request.host, dist_id),
                    chat_id=chat_id)

    @gen.coroutine
    def post(self, chat_id):
        message = self.get_argument("message")
        recv_key = "chat::{0}::message".format(chat_id)
        yield client.rpush(recv_key, message)
        self.write("success")


class ChatMessageHandler(web.RequestHandler):
    @gen.coroutine
    def post(self):
        chat_id = self.get_argument("chat_id")
        dist_id = yield client.hget(CHAT_PEER_KEY, chat_id)

        send_key = "chat::{0}::message".format(dist_id)

        key, message = yield client.blpop(send_key)

        self.write(message)



if __name__ == "__main__":
    app = web.Application([
        (r'/chat/message', ChatMessageHandler),
        (r'/chat/?(.*)', ChatHandler),
    ], debug=True)

    app.listen(8888)
    ioloop.IOLoop.instance().start()
