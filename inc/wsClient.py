#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tornado.ioloop import IOLoop, PeriodicCallback
from tornado import gen
from tornado.websocket import websocket_connect
import json
import base64 
import uuid
try:
    import thread
except ImportError:  # TODO use Threading instead of _thread in python3
    import _thread as thread


hw = "sp:"+base64.b64encode(str(uuid.getnode()))+"0"

#class wsClient():
hw = "sp:"+base64.b64encode(str(uuid.getnode()))+"0"

ws.url = "ws://localhost:4000/socket/websocket/"
ws.timeout = 5
ws.ioloop = IOLoop.instance()
self.ws = None
self.connect()
PeriodicCallback(self.keep_alive, 20000, io_loop=self.ioloop).start()
thread.start_new_thread(self.ioloop.start, ())

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
        #thread.start_new_thread(self.run(), ())

def send(self, msg):
    self.connect()
    print(self.ws)
    self.ws.write_message(msg)

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
