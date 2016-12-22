import logging
import json
import websocket
import time
import base64
import uuid
import sqlite3 as lite
import sys
from threading import Thread
from main import SocketHandler

try:
    import thread
except ImportError:  # TODO use Threading instead of _thread in python3
    import _thread as thread

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
    #thread(target = run).start()

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

hw = 'sp:'+base64.b64encode(str(uuid.getnode()))+'0'
host = "ws://localhost:4000/socket/websocket/"
ws = websocket.WebSocketApp(host)
ws.on_open = on_open
ws.on_message = on_message
ws.on_error = on_error

def wsClient():
    logging.info("Begin")
    # websocket.enableTrace(True)
    ws.run_forever(ping_interval=30, ping_timeout=10)
