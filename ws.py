import hashlib
from pyfingerprint.pyfingerprint import PyFingerprint
#from inc.wsClient import wsClient 
#from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from tornado import websocket, web, ioloop
from threading import Thread
try:
    import thread
except ImportError:  # TODO use Threading instead of _thread in python3
    import _thread as thread
import threading
import json
import logging
import time
import re
import sys
import base64
import uuid
import websocket as websocketClient

#class EchoClient(WebSocketClient):
#    def opened(self):
#       print("aa")
#       for i in range(0, 200, 25):
#          self.send("*" * i)
#
#    def closed(self, code, reason):
#       print(("Closed down", code, reason))
#
#    def received_message(self, m):
#       print("=> %d %s" % (len(m), str(m)))
#
#print("aA")
#try:
#    ws = EchoClient('ws://localhost:4000/socket/websocket/', protocols=['http-only', 'chat'])
#    #ws = HelloSocket('ws://localhost:4000/socket/websocket/')
#    ws.connect()
#except KeyboardInterrupt:
#   ws.close()


class wClient(websocketClient.WebSocketApp):

  hw = "sp:0"
  host = "ws://localhost:4000/socket/websocket/"
  
  def on_open(ws):
      def run(*args):
          # send the message, then wait
          # so thread doesn't exit and socket
          # isn't closed
          ws.send(json.dumps({
              "topic":hw,
              "event":"phx_join",
              "payload":"",
              "ref":""
          }))
  
      thread.start_new_thread(run, ())
  
  def on_message(ws, message):
      message = json.loads(message) 
      print(message)
  
  def on_error(ws, error):
      print(error)
      time.sleep(10)
      wsClient()
  
  def on_close(ws, status):
      print("### closed ###")
      time.sleep(10)
      wsClient()
  
  def wsClient():
      try:
        logging.info("Begin")
        #websocket.enableTrace(True)
        ws = websocketClient.WebSocketApp(host)
        ws.on_open = on_open
        ws.on_message = on_message
        ws.on_error = on_error
        ws.run_forever(ping_interval=30, ping_timeout=10)
      except Exception as e:
        print('---Exception message: ' + str(e))
        wsClient()

