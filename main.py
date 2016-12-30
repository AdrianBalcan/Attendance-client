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
from pysqlcipher import dbapi2 as sqlite
import datetime

f = None
wsconnected = 0 
hw = "sp:"+base64.b64encode(str(uuid.getnode()))+"0"
host = "ws://localhost:4000/socket/websocket/"
pragma = "0jFr90a"
enrollStatus = False

class Sql():
    conn = sqlite.connect('att', check_same_thread=False)
    c = conn.cursor()
    c.execute("PRAGMA key='"+pragma+"'")

    def create(self):
        try:
            Sql()
            Sql.c.execute("create table configs (id, fingerprints_limit int, devicegroup int, date text)")
            Sql.c.execute("create table attendances (employeeID int, date text);")
            Sql.c.execute("create table employees (employeeID int, date text);")
            Sql.c.execute("insert into configs values (1, 0, 0, '"+str(datetime.datetime.now())+"""')""")
            Sql.conn.commit()
        except Exception as e:
            print(str(e))

class DeviceGroup:
    def __init__(self):
        self.id = 0
        self.check()

    def callUpdate(self):
        if (wsconnected == 1):
            on_send(json.dumps({
                "topic":hw,
                "event":"new_msg",
                "payload":json.dumps({
                    "type": "devicegroup",
                    "hw": hw 
                }),
                "ref":""
            }))

    def update(self, id):
        print id
        Sql()
        Sql.c.execute("UPDATE configs SET devicegroup = %d WHERE id == 1" % id)
        Sql.conn.commit()
        self.check()

    def check(self):
        Sql()
        rows = Sql.c.execute("SELECT devicegroup FROM configs WHERE id == 1;")
        for row in rows:
          self.id = row[0]
        if(self.id == 0):
            print f
            if bool(f):
              f.__del__() 
            SocketHandler.send_to_all(json.dumps({
                'message': 'no-devicegroup',
                'hw': str(hw),
            }))

def on_open(ws):
    global wsconnected
    wsconnected = 1
    SocketHandler.send_to_all(json.dumps({
        'message': 'srv-conn',
    }))
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
        time.sleep(1)
        devicegroup.callUpdate()

    thread.start_new_thread(run, ())

def on_send(message):
    try:
      ws.send(message)
      print("sent: "+message)
    except Exception as e:
      print('---Exception message: ' + str(e))

def on_message(ws, message):
    print message
    message = json.loads(message) 
    if(bool(message["event"])):
      print("status exist: %s" % str(message["event"]))
      if(message["event"] == "phx_error"):
        ws.close() 
        time.sleep(10)
        wsClient() 

    if(bool(message["payload"])):

      if(bool(message["payload"]["response"]["type"])):
        if(message["payload"]["response"]["type"] == "enroll"):
            global enrollStatus
            enrollStatus = True
            global employeeName
            employeeName = message["payload"]["response"]["firstname"] + message["payload"]["response"]["lastname"]
        if(message["payload"]["response"]["type"] == "cancelEnroll"):
            global enrollStatus
            enrollStatus = False
        if(message["payload"]["response"]["type"] == "devicegroup"):
          if(message["payload"]["response"]["result"]):
            devicegroup.update(message["payload"]["response"]["result"][0])

def on_error(ws, error):
    global wsconnected
    wsconnected = 0
    SocketHandler.send_to_all(json.dumps({
        'message': 'no-srv-conn',
    }))
    try:
      print(error)
      time.sleep(10)
      wsClient()
    except Exception as e:
      print('---Exception message: ' + str(e))
      time.sleep(10)
      wsClient()

def on_close(ws, status):
    global wsconnected
    wsconnected = 0 
    SocketHandler.send_to_all(json.dumps({
        'message': 'no-srv-conn',
    }))
    try:
      print("### closed ###")
      time.sleep(10)
      wsClient()
    except Exception as e:
      print('---Exception message: ' + str(e))
      time.sleep(10)
      wsClient()

def wsClient():
    try:
      global ws
      ws = websocketClient.WebSocketApp(host)
      logging.info("Begin")
      ws.on_open = on_open
      ws.on_message = on_message
      ws.on_error = on_error
      ws.run_forever(ping_interval=10, ping_timeout=5)
    except Exception as e:
      print('---Exception message: ' + str(e))
      time.sleep(10)
      wsClient()

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
        if devicegroup.id == 0:
            SocketHandler.send_to_all(json.dumps({
                'message': 'no-devicegroup',
                'hw': str(hw),
            }))

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
    if (devicegroup.id > 0):
        try:
            global f
            f = PyFingerprint('/dev/cu.SLAB_USBtoUART', 57600, 0xFFFFFFFF, 0x00000000)
        
            if ( f.verifyPassword() == False ):
                raise ValueError('The given fingerprint sensor password is wrong!')
        
        except Exception as e:
            SocketHandler.send_to_all(json.dumps({
                'message': 'no-fingerprint',
            }))
            print('The fingerprint sensor could not be initialized!')
            print('Exception message: ' + str(e))
            time.sleep(20)
            sys.exc_clear()
            fingerprint()
    else:
        time.sleep(10)
        fingerprint()

    ## Gets some sensor information
    #f.clearDatabase()
    print f.getTemplateIndex(2)
    print('Currently used templates: ' + str(f.getTemplateCount()) +'/'+ str(f.getStorageCapacity()))
    print f.getSystemParameters()
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
            if(wsconnected == 1):
                on_send(json.dumps({
                    "topic":hw,
                    "event":"new_msg",
                    "payload":json.dumps({
                        "type": "identify-ok",
                        "id": int(positionNumber),
                    }),
                    "ref":""
                }))
            else:
              try:
                Sql()
                Sql.c.execute("insert into attendances values ("+ str(positionNumber) +",'"+ str(datetime.datetime.now())+"')")
                Sql.conn.commit()
              except Exception as e:
                print("insert: %s" % str(e))

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
    
        SocketHandler.send_to_all(json.dumps({
            'message': 'enroll',
            'enrollStep': 1,
            'enrollName': employeeName,
        }))
        ## Wait that finger is read
        while ( f.readImage()==False or enrollStatus==False ):
            if ( enrollStatus == True ):
                pass
            else:
                SocketHandler.send_to_all(json.dumps({
                    'message': 'clear',
                }))
                verify(f)
    
        ## Converts read image to characteristics and stores it in charbuffer 1
        f.convertImage(0x01)
    
        ## Checks if finger is already enrolled
        result = f.searchTemplate()
        positionNumber = result[0]
    
        if ( positionNumber >= 0 ):
            SocketHandler.send_to_all(json.dumps({
                'message': 'enroll-exist',
                'enrollStep': 1,
                'enrollName': employeeName,
            }))
            print('Template already exists at position #' + str(positionNumber))
            while ( f.readImage()==True ):
                pass
            time.sleep(2)
            enroll(f)
    
        SocketHandler.send_to_all(json.dumps({
            'message': 'enroll-ok',
            'enrollStep': 1,
            'enrollName': employeeName,
        }))
        print('Remove finger...')
        while ( f.readImage()==True ):
            pass
    
##############################
        print('Waiting for same finger again...')

        SocketHandler.send_to_all(json.dumps({
            'message': 'enroll',
            'enrollStep': 2,
            'enrollName': employeeName,
        }))
    
        ## Wait that finger is read again
        while ( f.readImage()==False or enrollStatus==False ):
            if ( enrollStatus == True ):
                pass
            else:
                SocketHandler.send_to_all(json.dumps({
                    'message': 'clear',
                }))
                verify(f)
    
        ## Converts read image to characteristics and stores it in charbuffer 2
        f.convertImage(0x02)

        ## Checks if finger is already enrolled
        result = f.searchTemplate(0x02)
        positionNumber = result[0]
    
        if ( positionNumber >= 0 ):
            SocketHandler.send_to_all(json.dumps({
                'message': 'enroll-exist',
                'enrollStep': 2,
                'enrollName': employeeName,
            }))
            print('Template already exists at position #' + str(positionNumber))
            while ( f.readImage()==True ):
                pass
            time.sleep(2)
            enroll(f)

        SocketHandler.send_to_all(json.dumps({
            'message': 'enroll-ok',
            'enrollStep': 2,
            'enrollName': employeeName,
        }))
        print('Remove finger...')
        while ( f.readImage()==True ):
            pass
        time.sleep(1)
        ## Compares the charbuffers and creates a template
        f.createTemplate()
        tst = f.downloadCharacteristics(0x01)   
        #print(tst)
        #f.uploadCharacteristics(0x01, tst) 
        ## Saves template at new position number
        positionNumber = f.storeTemplate()
        if(wsconnected == 1):
            on_send(json.dumps({
                "topic":hw,
                "event":"new_msg",
                "payload":json.dumps({
                    "type": "enroll-ok",
                    "id": int(positionNumber),
                    "template": tst,
                }),
                "ref":""
            }))
        SocketHandler.send_to_all(json.dumps({
            'message': 'enroll-successful',
            'enrollStep': 2,
            'enrollName': employeeName,
        }))
        print('Finger enrolled successfully!')
        print('New template position #' + str(positionNumber))
        time.sleep(1)
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

def devicegroupUpdate():
    time.sleep(60)
    devicegroup.callUpdate()
    devicegroupUpdate()

if __name__ == '__main__':
    sql = Sql()
    sql.create()
    devicegroup = DeviceGroup()
    Thread(target = wsClient).start()

    #init DeviceGroup class an check it which is included in __init__ method
    Thread(name='httpServer', target = httpServer).start()
    Thread(name='fingerprint', target = fingerprint).start()
    Thread(name='devicegroupUpdate', target = devicegroupUpdate).start()
