#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

hw = "sp:"+base64.b64encode(str(uuid.getnode()))+"0"

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

def wsClient():
    logging.info("Begin")
    # websocket.enableTrace(True)
    ws.run_forever(ping_interval=30, ping_timeout=10)

hw = 'sp:'+base64.b64encode(str(uuid.getnode()))+'0'
host = "ws://localhost:4000/socket/websocket/"
ws = websocketClient.WebSocketApp(host)
ws.on_open = on_open
ws.on_message = on_message
ws.on_error = on_error
#thread.wsClient()

enrollStatus=True

cl = []

class IndexHandler(web.RequestHandler):
    def get(self):
        self.render("index.html")

class EnrollHandler(web.RequestHandler):
    def get(self):
        global enrollStatus
        enrollStatus=True
        self.wfile.write("<html><body><h1>hi!</h1></body></html>")

class DeleteHandler(web.RequestHandler):
    def get(self):
        id = self.path.split("/")[2]
        delete(f, id)
        self.wfile.write("<html><body><h1>hi!</h1></body></html>")

#class GetTemplateIndexHandler(web.RequestHandler):

#class HelloSocket(wsClient.WebSocket):
#
#    def on_open(self):
#        self.write('hello, world')
#
#    def on_message(self, data):
#        print data
#
#    def on_ping(self):
#        print 'I was pinged'
#
#    def on_pong(self):
#        print 'I was ponged'
#
#    def on_close(self):
#        print 'Socket closed.'
#
#
#ws = HelloSocket('ws://localhost:4000/socket/websocket/')
#ws.connect()

class SocketHandler(websocket.WebSocketHandler):
   
    @staticmethod
    def send_to_all(message):
        for c in cl:
            c.write_message(message)

    def check_origin(self, origin):
        return True

    def open(self):
        if self not in cl:
            cl.append(self)

    def on_close(self):
        if self in cl:
            cl.remove(self)

class ApiHandler(web.RequestHandler):

    @web.asynchronous
    def get(self, *args):
        self.finish()
        id = self.get_argument("id")
        value = self.get_argument("value")
        data = {"id": id, "value" : value}
        data = json.dumps(data)
        for c in cl:
            c.write_message(data)

    @web.asynchronous
    def post(self):
        pass

app = web.Application([
    (r'/', IndexHandler),
    (r'/enroll', EnrollHandler),
    (r'/delete/(.*)', DeleteHandler),
    (r'/ws', SocketHandler),
    (r'/api', ApiHandler),
    (r'/js/(.*)', web.StaticFileHandler, {'path': './public/js/'}),
    (r'/css/(.*)', web.StaticFileHandler, {'path': './public/css/'}),
])

#class S(BaseHTTPRequestHandler):
#    def _set_headers(self):
#        self.send_response(200)
#        self.send_header('Content-type', 'text/html')
#        self.end_headers()
#
#    def do_GET(self):
#        self._set_headers()
#        if self.path=="/enroll":
#            global enrollStatus
#            enrollStatus=True
#            self.wfile.write("<html><body><h1>hi!</h1></body></html>")
#        if re.match('^/delete/\d*$', self.path):
#            id = self.path.split("/")[2]
#            delete(f, id)
#            self.wfile.write("<html><body><h1>hi!</h1></body></html>")
#
#    def do_HEAD(self):
#        self._set_headers()
#        
#    def do_POST(self):
#        self._set_headers()
#        if self.path=="/enroll":
#            self.wfile.write("<html><body><h1>hi!</h1></body></html>")
#
#
#def httpServer(server_class=HTTPServer, handler_class=S, port=8000):
#    try:
#        server_address = ('', port)
#        httpd = server_class(server_address, handler_class)
#        print 'Starting httpd...'
#        httpd.serve_forever()
#    except KeyboardInterrupt:
#        print '^C received, shutting down the web server'
#        server.socket.close()
def httpServer():
    app.listen(8888)
    ioloop.IOLoop.instance().start()

def fingerprint():
    ## Search for a finger
    ##
    ## Tries to initialize the sensor
    try:
        f = PyFingerprint('/dev/cu.SLAB_USBtoUART', 115200, 0xFFFFFFFF, 0x00000000)
    
        if ( f.verifyPassword() == False ):
            raise ValueError('The given fingerprint sensor password is wrong!')
    
    except Exception as e:
        SocketHandler.send_to_all(json.dumps({
            'message': 'no-fingerprint',
        }))
        print('The fingerprint sensor could not be initialized!')
        print('Exception message: ' + str(e))
        time.sleep(10)
        sys.exc_clear()
        fingerprint()

    
    ## Gets some sensor information
    #f.clearDatabase()
    print('Currently used templates: ' + str(f.getTemplateCount()) +'/'+ str(f.getStorageCapacity()))
    #f.getSystemParameters()
    #f.loadTemplate(1,1) 
    #wee = f.downloadCharacteristics(1) 
    #print(wee)
    verify(f)

def verify(f):
    ## Tries to search the finger and calculate hash

    try:
        global enrollStatus

        print('Waiting for finger...%s' % enrollStatus)
        SocketHandler.send_to_all(json.dumps({
            'message': 'clear',
        }))

        ## Wait that finger is read
        while ( f.readImage()==False or enrollStatus==True ):
            if ( enrollStatus == False ):
                pass
            else:
                enroll(f)
    
        ## Converts read image to characteristics and stores it in charbuffer 1
        f.convertImage(0x01)
    
        ## Searchs template
        result = f.searchTemplate()
    
        positionNumber = result[0]
        accuracyScore = result[1]
    
        if ( positionNumber == -1 ):
            print('No match found!')
            SocketHandler.send_to_all(json.dumps({
                'message': 'identify-err',
            }))
        else:
            SocketHandler.send_to_all(json.dumps({
                'message': 'identify-ok',
                'name': str(positionNumber),
            }))
           # ws.send(json.dumps({
           #     "topic":hw,
           #     "event":"new_msg",
           #     "payload":json.dumps({
           #         "type": "identify-ok",
           #         "id": str(positionNumber),
           #     }),
           #     "ref":""
           # }))

            print('Found template at position #' + str(positionNumber))
            print('The accuracy score is: ' + str(accuracyScore))
    
        ## OPTIONAL stuff
        ##
    
        ## Loads the found template to charbuffer 1
        # f.loadTemplate(positionNumber, 0x01)
    
        ## Downloads the characteristics of template loaded in charbuffer 1
        #characterics = str(f.downloadCharacteristics(0x01))
    
        ## Hashes characteristics of template
        #print('SHA-2 hash of template: ' + hashlib.sha256(characterics).hexdigest())

        while ( f.readImage()==True ):
            pass
        
        verify(f)
    
    except Exception as e:
        SocketHandler.send_to_all(json.dumps({
            'message': 'no-fingerprint',
        }))
        print('Operation failed!')
        print('Exception message: ' + str(e))
        sys.exc_clear()
        fingerprint()

def enroll(f):
    global enrollStatus
    ## Tries to enroll new finger
    try:
        print('Enrollment: Waiting for finger...')
    
        ## Wait that finger is read
        while ( f.readImage()==False or enrollStatus==False ):
            if ( enrollStatus == True ):
                pass
            else:
                verify(f)
    
        ## Converts read image to characteristics and stores it in charbuffer 1
        f.convertImage(0x01)
    
        ## Checks if finger is already enrolled
        result = f.searchTemplate()
        positionNumber = result[0]
    
        if ( positionNumber >= 0 ):
            print('Template already exists at position #' + str(positionNumber))
            while ( f.readImage()==True ):
                pass
            enroll(f)
    
        print('Remove finger...')
        while ( f.readImage()==True ):
            pass
    
        print('Waiting for same finger again...')
    
        ## Wait that finger is read again
        while ( f.readImage()==False or enrollStatus==False ):
            if ( enrollStatus == True ):
                pass
            else:
                verify(f)
    
        ## Converts read image to characteristics and stores it in charbuffer 2
        f.convertImage(0x02)
    
        ## Compares the charbuffers and creates a template
        f.createTemplate()
        tst = f.downloadCharacteristics(0x01)   
        print(tst)
        f.uploadCharacteristics(0x01, tst) 
        ## Saves template at new position number
        positionNumber = f.storeTemplate()
        print('Finger enrolled successfully!')
        print('New template position #' + str(positionNumber))
        enrollStatus = False
        while ( f.readImage()==False ):
            verify(f) 
    
    except Exception as e:
        SocketHandler.send_to_all(json.dumps({
            'message': 'no-fingerprint',
        }))
        print('Operation failed!')
        print('Exception message: ' + str(e))
        fingerprint()

def delete(f, id):
    try:
        positionNumber = int(id)
        if ( f.deleteTemplate(positionNumber) == True ):
            print('Template deleted! %d' % positionNumber)
    except Exception as e:
        print('Template delete error.Exception message: ' + str(e))

def getTemplateIndex(f):
    try:
        data = f.getTemplateIndex('1')
        print('Template deleted! %s' % data)
    except Exception as e:
        print('Exception message: ' + str(e))


#def startWsClient():
#    wsClient().connect()

if __name__ == '__main__':
    Thread(name='httpServer', target = httpServer).start()
    Thread(name='fingerprint', target = fingerprint).start()
    Thread(target = wsClient).start()
