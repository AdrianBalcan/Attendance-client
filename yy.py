#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tornado.ioloop import IOLoop, PeriodicCallback
from tornado import gen
from tornado.websocket import websocket_connect
import json
import base64 
import uuid

hw = "sp:"+base64.b64encode(str(uuid.getnode()))+"0"

class Client(object):
    def __init__(self, url, timeout):
        self.url = url
        self.timeout = timeout
        self.ioloop = IOLoop.instance()
        self.ws = None
        self.connect()
	PeriodicCallback(self.keep_alive, 20000, io_loop=self.ioloop).start()
        self.ioloop.start()

    @gen.coroutine
    def connect(self):
        print "trying to connect"
        try:
            self.ws = yield websocket_connect(self.url)
        except Exception, e:
            print "connection error"
        else:
            print "connected"
            self.ws.write_message(json.dumps({
                "topic":hw,
                "event":"phx_join",
                "payload":"",
                "ref":""
            }))
            self.run()

    @gen.coroutine
    def run(self):
        while True:
            msg = yield self.ws.read_message()
            print(msg)
            if msg is None:
                print "connection closed"
                self.ws = None

    def keep_alive(self):
        if self.ws is None:
            self.connect()
        else:
            self.ws.write_message(json.dumps({
                "topic":hw,
                "event":"new_msg",
                "payload":"keep_alive",
                "ref":""
            }))

if __name__ == "__main__":
    host = "ws://localhost:4000/socket/websocket/"
    client = Client(host, 5)
