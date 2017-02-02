#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" This code """
from threading import Thread
try:
    import thread
except ImportError:
    import _thread as thread
import sys
import os
import pytz
import json
import logging
from logging.handlers import RotatingFileHandler
import time
import uuid
import datetime
import websocket as websocketClient
from pysqlcipher import dbapi2 as sqlite
from tornado import websocket, web, ioloop
from pyfingerprint.pyfingerprint import PyFingerprint

logfile_path = 'attendance-client.log'
if 'debug' in sys.argv:
    handler = logging.StreamHandler()
else:
    handler = RotatingFileHandler(logfile_path, maxBytes=10485760, 
            backupCount=300, encoding='utf-8')
formatter = logging.Formatter("[%(asctime)s] [%(name)s] \
[%(funcName)s():%(lineno)s] \
[PID:%(process)d TID:%(threadName)s;%(thread)d] \
[%(levelname)s]:%(message)s", "%d/%m/%Y %H:%M:%S")
handler.setLevel(logging.DEBUG)
handler.setFormatter(formatter)
logging.root.addHandler(handler)
logging.root.setLevel(logging.DEBUG)

f = None
Verify = True
wsconnected = 0
hw = str(uuid.getnode())
host = "ws://"+os.environ["ATTD_HOST"]+":"+os.environ["ATTD_PORT"]+"/socket/websocket/"
pragma = "0jFr90a"
enrollStatus = False

class Dbm():
    def __init__(self):
        self.conn = sqlite.connect('att', check_same_thread=False)
        self.conn.execute("PRAGMA key='"+pragma+"'")
        self.conn.commit()
        self.cur = self.conn.cursor()

    def queryOne(self, arg):
        self.cur.execute(arg)
        return self.cur.fetchone()

    def query(self, arg):
        self.cur.execute(arg)
        self.conn.commit()
        return self.cur

    def __del__(self):
        self.conn.close()

def createDB():
    try:
        dbm = Dbm()
        dbm.query("create table configs(id, fingerprints_limit int, devicegroup int, date text)")
        dbm.query("create table attendances(employeeID int, date text);")
        dbm.query("create table employees(employeeID int PRIMARY KEY, firstname text, lastname text, status int, smart_update_time text);")
        dbm.query("create table fingerprints(f_id int PRIMARY KEY, employeeID int, template text);")
        dbm.query("insert into configs values(1, 0, 0, '"+str(datetime.datetime.now(pytz.timezone('Europe/Bucharest')))+"""')""")
    except Exception as e:
        logging.exception("createDB: " + str(e))

def alterDB():
    try:
        dbm = Dbm()
        #dbm.query("ALTER TABLE employees ADD COLUMN smart_update_time text")
    except Exception as e:
        logging.exception("alterDb: " + str(e))

def employeeStatus(id, status, timestamp):
    try:
        print timestamp
        if isinstance(status, int):
            s = status
        elif "IN" in status:
            s = 1
        elif "OUT" in status:
            s = 0
        dbm = Dbm()
        if timestamp is "now":
            dbm.query("UPDATE employees SET status = "+str(s)+", smart_update_time = strftime('%s','now') where employeeID = "+str(id))
        else:
            timestamp = time.mktime(datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f+02:00").timetuple())
            dbm.query("UPDATE employees SET status = "+str(s)+", smart_update_time = "+str(timestamp)+" where employeeID = "+str(id))
    except Exception as e:
        logging.exception("employeeStatus" + str(e))

class DeviceGroup:
    def __init__(self):
        self.id = 0
        self.check()

    def callUpdate(self):
        if wsconnected == 1:
            on_send(json.dumps({
                "topic": "sp:"+hw,
                "event":"new_msg",
                "payload":json.dumps({
                    "type": "devicegroup",
                    "hw": hw 
                }),
                "ref":""
            }))

    def setSecurity(setSecurityID):
        if f is not None:
            stopVerify()
            f.setSystemParameter(5, setSecurityID)
            startVerify()

    def update(self, id):
        dbm = Dbm()
        dbm.query("UPDATE configs SET devicegroup = %d WHERE id == 1" % id)
        self.check()

    def check(self):
        dbm = Dbm()
        rows = dbm.query("SELECT devicegroup FROM configs WHERE id == 1;")
       # sql = Sql()
       # rows = sql.c.execute("SELECT devicegroup FROM configs WHERE id == 1;")
        for row in rows:
          self.id = row[0]
        if(self.id == 0):
            if bool(f):
                stopVerify() 
            SocketHandler.send_to_all(json.dumps({
                'message': 'no-devicegroup',
                'hw': str(hw),
            }))
        else:
            SocketHandler.send_to_all(json.dumps({
                'message': 'devicegroup',
                'devicegroup': self.id,
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
        on_send(json.dumps({
            "topic": "sp:"+hw,
            "event":"phx_join",
            "payload":"",
            "ref":""
        }))
        devicegroup.callUpdate()

    thread.start_new_thread(run,())

def on_send(message):
    try:
      ws.send(message)
      logging.debug("sent: "+message)
    except Exception as e:
      logging.exception('on_send: ' + str(e))
      wsClient() 

def on_message(ws, message):
    logging.debug("on_message: " + message)
    try:
        message = json.loads(message) 
        if "event" in message: 
          if(message["event"] == "phx_error"):
            ws.close() 
            time.sleep(10)
            wsClient() 

        if "payload" in message:
          if "response" in message["payload"]:
            if "type" in message["payload"]["response"]:
              if(message["payload"]["response"]["type"] == "deleteFingerprint"):
                  deleteFingerprint(message["payload"]["response"]["id"])
              if(message["payload"]["response"]["type"] == "employeesSync"):
                  Thread(name='employeesSync', target = employeesSync, args=[message["payload"]["response"]["result"]]).start()
              if(message["payload"]["response"]["type"] == "statusSync"):
                  Thread(name='statusSync', target = statusSync, args=[message["payload"]["response"]["result"]]).start()
              if(message["payload"]["response"]["type"] == "synchronize"):
                  synchronize()
              if(message["payload"]["response"]["type"] == "enrollSync"):
                  Thread(name='enrollSync', target = enrollSync, args=[message["payload"]["response"]]).start()
              if(message["payload"]["response"]["type"] == "enroll"):
                  global enrollStatus
                  enrollStatus = True
                  global employeeFirstname
                  employeeFirstname = message["payload"]["response"]["firstname"]
                  global employeeLastname
                  employeeLastname = message["payload"]["response"]["lastname"]
                  global employeeName
                  employeeName = employeeFirstname + " " + employeeLastname
                  global employeeID
                  employeeID = message["payload"]["response"]["employeeID"]
              if(message["payload"]["response"]["type"] == "cancelEnrollment"):
                  global enrollStatus
                  enrollStatus = False
                  SocketHandler.send_to_all(json.dumps({
                      'message': 'clear',
                  }))
              if(message["payload"]["response"]["type"] == "devicegroup-create"):
                if(message["payload"]["response"]["result"]):
                  devicegroup.update(int(message["payload"]["response"]["result"]))
                  devicegroup.check()
              if(message["payload"]["response"]["type"] == "devicegroup"):
                if(message["payload"]["response"]["result"]):
                  devicegroup.update(message["payload"]["response"]["result"][0])
                  devicegroup.check()
              if(message["payload"]["response"]["type"] == "identify-ok"):
                  employeeStatus(message["payload"]["response"]["employeeID"], message["payload"]["response"]["result"], message["payload"]["response"]["timestamp"])
              if(message["payload"]["response"]["type"] == "employees-status"):
                if(message["payload"]["response"]["result"]):
                  devicegroup.update(message["payload"]["response"]["result"][0])
    except Exception as e:
        logging.exception("on_message: "+str(e))

def on_error(ws, error):
    global wsconnected
    wsconnected = 0
    SocketHandler.send_to_all(json.dumps({
        'message': 'no-srv-conn',
    }))
    try:
      time.sleep(10)
      wsClient()
    except Exception as e:
      logging.exception('on_error: ' + str(e))
      time.sleep(10)
      wsClient()

def on_close(ws, status):
    global wsconnected
    wsconnected = 0 
    SocketHandler.send_to_all(json.dumps({
        'message': 'no-srv-conn',
    }))
    try:
      time.sleep(10)
      wsClient()
    except Exception as e:
      logging.exception('on_close: ' + str(e))
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
      logging.exception('wsClient: ' + str(e))
      time.sleep(10)
      wsClient()

cl = []

class IndexHandler(web.RequestHandler):
    def get(self):
        self.render("index.html")

class EnrollHandler(web.RequestHandler):
    def get(self):
        self.write("<html><body><h1>hi!</h1></body></html>")
        synchronize()
        #pass

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
        else:
            SocketHandler.send_to_all(json.dumps({
                'message': 'devicegroup',
                'devicegroup': devicegroup.id,
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
    (r'/ws', SocketHandler),
    (r'/api', ApiHandler),
    (r'/js/(.*)', web.StaticFileHandler, {'path': 'public/js/'}),
    (r'/css/(.*)', web.StaticFileHandler, {'path': 'public/css/'}),
])

def httpServer():
    app.listen(8888)
    ioloop.IOLoop.instance().start()

def fingerprint():
    ## Search for a finger
    ##
    ## Tries to initialize the sensor
    #dbm = Dbm()
    #deviceGroupID = dbm.queryOne("SELECT devicegroup FROM configs WHERE id == 1")
    logging.info(devicegroup.id)
    if(devicegroup.id > 0):
        try:
            global f
            f = PyFingerprint(os.environ["ATTD_COM_PORT"], 115200, 0xFFFFFFFF, 0x00000000)
        
            if(f.verifyPassword() == False):
                raise ValueError('The given fingerprint sensor password is wrong!')
        
        except Exception as e:
            if(devicegroup.id > 0):
                SocketHandler.send_to_all(json.dumps({
                    'message': 'no-fingerprint',
                }))
                logging.warning('The fingerprint sensor could not be initialized!')
                logging.warning('fingerprint: ' + str(e))
            time.sleep(20)
            sys.exc_clear()
            fingerprint()
    else:
        time.sleep(10)
        fingerprint()

    ## Gets some sensor information
    #f.clearDatabase()
    try:
        #synchronize()
        callEmployeesSync()
    except Exception as e:
        logging.exception("fingerprint callEmployeesSync")
    finally: 
        pass
        #f.setSystemParameter(5, 1))
        #f.getTemplateIndex())
        #logging.info('Currently used templates: ' + str(f.getTemplateCount()) +'/'+ str(f.getStorageCapacity()))
        #logging.info(f.getSystemParameters())
        #verify(f)

def changeSecurity(value):
    stopVerify()
    time.sleep(1)
    startVerify()

def deleteFingerprint(ID):
    stopVerify()
    try:
        dbm = Dbm()
        dbm.query("DELETE FROM fingerprints where f_id == %s" % ID)
        f.deleteTemplate(ID)
    except Exception as e:
        logging.exception("Opss!" + str(e))
        pass
    startVerify()
     
def callEmployeesSync():
    if wsconnected == 1:
        on_send(json.dumps({
            "topic": "sp:"+hw,
            "event":"new_msg",
            "payload":json.dumps({
                "type": "employeesSync",
                "devicegroup": int(devicegroup.id),
                "hw": hw 
            }),
            "ref":""
        }))

def callStatusSync():
    if wsconnected == 1:
        on_send(json.dumps({
            "topic": "sp:"+hw,
            "event":"new_msg",
            "payload":json.dumps({
                "type": "statusSync",
                "devicegroup": int(devicegroup.id),
                "hw": hw 
            }),
            "ref":""
        }))

def enrollSync(employee):
    try:
        dbm = Dbm()
        dbm.query("INSERT OR REPLACE into employees VALUES ("+str(employee["employeeID"])+", '"+str(employee["firstname"])+"', '"+str(employee["lastname"])+"', 0, '')")
        dbm.query("INSERT OR REPLACE into fingerprints VALUES ("+str(employee["f_id"])+", "+str(employee["employeeID"])+", '"+str(employee["template"])+"')")
        stopVerify()
        f.uploadCharacteristics(0x01, map(int, employee["template"].split(',')))
        f.storeTemplate(employee["f_id"], 0x01)
        callStatusSync()
        startVerify()
    except Exception as e:
        logging.exception("enrollSync: "+str(e))
    
def employeesSync(data):
    try:
        SocketHandler.send_to_all(json.dumps({
            'message': 'synchronize',
        }))
        stopVerify()
        dbm = Dbm()
        dbm.query("DELETE FROM employees")
        dbm.query("DELETE FROM fingerprints")
        f.clearDatabase()
        for employee in data:
            logging.info(employee["employeeID"])
            dbm.query("INSERT OR REPLACE into employees VALUES ("+str(employee["employeeID"])+", '"+str(employee["firstname"])+"', '"+str(employee["lastname"])+"', 0, '')")
            dbm.query("INSERT into fingerprints VALUES ("+str(employee["f_id"])+", "+str(employee["employeeID"])+", '"+str(employee["template"])+"')")
            f.uploadCharacteristics(0x01, map(int, employee["template"].split(',')))
            f.storeTemplate(employee["f_id"], 0x01)
   # time.sleep(1)
   # dbm = Dbm()
   # rows = dbm.query("SELECT * FROM fingerprints;")
   # try:
   #     for row in rows:
   #         logging.debug(row[0])
   #         f.uploadCharacteristics(0x01, map(int, row[2].split(',')))
   #         f.storeTemplate(row[0], 0x01)
   #         time.sleep(.1)
    except Exception as e:
        logging.exception("employeesSync - uploadCh :"+str(e))
    finally:
        SocketHandler.send_to_all(json.dumps({
            'message': 'clear',
        }))
        startVerify()
        callStatusSync()
        logging.info('Currently used templates: ' + str(f.getTemplateCount()) +'/'+ str(f.getStorageCapacity()))
        logging.info(f.getSystemParameters())
        Thread(name='fingerprint', target = verify, args=[f]).start()

def statusSync(data):
    for status in data:
        if status["employeeID"] is not None:
            s = 0
            if status["status"] is not None and "IN" in status["status"]:
                s = 1
            try:
                inserted_at = time.mktime(datetime.datetime.strptime(status["inserted_at"], "%Y-%m-%dT%H:%M:%S.%f").timetuple()) 
                dbm = Dbm()
                dbm.query("UPDATE employees SET status = "+str(s)+", smart_update_time = '"+str(inserted_at)+"' where employeeID = "+str(status["employeeID"]))
            except Exception as e:
                logging.exception("statusSync: "+str(e))

def synchronize():
    stopVerify()
    SocketHandler.send_to_all(json.dumps({
        'message': 'synchronize',
    }))
    devicegroup.callUpdate()
    time.sleep(1)
    callEmployeesSync()
    time.sleep(2)
    f.clearDatabase()
    dbm = Dbm()
    rows = dbm.query("SELECT * FROM fingerprints;")
    try:
        for row in rows:
            logging.debug(row[0])
            f.uploadCharacteristics(0x01, map(int, row[2].split(',')))
            f.storeTemplate(row[0], 0x01)
            time.sleep(.1)
    finally:
        startVerify()

def stopVerify():
    while(enrollStatus==True):
        time.sleep(.1)
    global Verify
    Verify = False
    time.sleep(1)

def startVerify():
    global Verify
    time.sleep(1)
    Verify = True
    time.sleep(1)
    SocketHandler.send_to_all(json.dumps({
        'message': 'clear',
    }))
    #verify(f)

def verify(f):
    ## Tries to search the finger and calculate hash

    try:
        global Verify
        global enrollStatus
        logging.info('Waiting for finger...%s' % enrollStatus)
        SocketHandler.send_to_all(json.dumps({
            'message': 'clear',
        }))

        ## Wait that finger is read
        while(f.readImage()==False or enrollStatus==True or Verify == False):
            while(Verify == False):
                time.sleep(.1)
            if(enrollStatus == True):
                enroll(f)
    
        ## Converts read image to characteristics and stores it in charbuffer 1
        f.convertImage(0x01)
    
        ## Searchs template
        result = f.searchTemplate()
    
        positionNumber = result[0]
        accuracyScore = result[1]
        print str(f.downloadCharacteristics(0x01))

    
        if(positionNumber == -1):
            logging.info("No match found!")
            SocketHandler.send_to_all(json.dumps({
                'message': 'identify-err',
            }))
        else:
            dbm = Dbm()
            row = dbm.queryOne("SELECT firstname, lastname, status, \
                (strftime('%s', 'now') - smart_update_time) \
                as smart_update_time, employees.employeeID \
                FROM employees JOIN fingerprints \
                ON employees.employeeID = fingerprints.employeeID \
                WHERE fingerprints.f_id == "+ str(positionNumber) +";")

            if row[3] is not None and row[3] < 600:
                logging.debug("Blocked by smartUpdate")
                SocketHandler.send_to_all(json.dumps({
                    'message': 'smartUpdate',
                    'name': row[0] +" "+ row[1],
                    'status': row[2],
                }))
            else:
               # dbm = Dbm()
               # dbm.query("UPDATE employees SET smart_update_time = strftime('%s','now') where employeeID = "+str(row[4]))
                if row[2] == 1:
                    status = 0
                elif row[2] == 0:
                    status = 1

                employeeStatus(row[4], status, "now")
                if(wsconnected == 1):
                    SocketHandler.send_to_all(json.dumps({
                        'message': 'identify-ok',
                        'name': row[0] +" "+ row[1],
                        'status': row[2],
                    }))
                    on_send(json.dumps({
                        "topic": "sp:"+hw,
                        "event": "new_msg",
                        "payload": json.dumps({
                            "type": "identify-ok",
                            "f_id": int(positionNumber),
                            "employeeID": row[4],
                            "devicegroup_id": int(devicegroup.id),
                            "device_hw": hw,
                            "timestamp": str(datetime.datetime.now(pytz.timezone('Europe/Bucharest')))
                        }),
                        "ref":""
                    }))
                else:
                    SocketHandler.send_to_all(json.dumps({
                        'message': 'identify-ok',
                        'name': row[0] +" "+ row[1],
                        'status': 2,
                    }))
                    try:
                        dbm = Dbm()
                        dbm.query("INSERT into attendances values("+
                            str(positionNumber) +",'"+
                            str(datetime.datetime.now(pytz.timezone('Europe/Bucharest')))+"')")
                    except Exception as e:
                        logging.exception("insert: %s" % str(e))

            logging.info("Found template at position #" + str(positionNumber))
            logging.info("The accuracy score is: " + str(accuracyScore))
 
        while(f.readImage()==True or Verify == False):
            while(Verify == False):
                time.sleep(.1)
            pass
        
        verify(f)
    
    except Exception as e:
        if(devicegroup.id > 0):
            SocketHandler.send_to_all(json.dumps({
                'message': "no-fingerprint",
            }))
        logging.warning("Operation failed!")
        logging.exception("Exception message: " + str(e))
        sys.exc_clear()
        fingerprint()

def enroll(f):
    global enrollStatus
    ## Tries to enroll new finger
    try:
        logging.info("Enrollment: Waiting for finger...")
    
        SocketHandler.send_to_all(json.dumps({
            'message': 'enroll',
            'enrollStep': 1,
            'enrollName': employeeName,
        }))
        ## Wait that finger is read
        while( f.readImage()==False or enrollStatus==False):
            if( enrollStatus == True):
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
    
        if( positionNumber >= 0):
            SocketHandler.send_to_all(json.dumps({
                'message': 'enroll-exist',
                'enrollStep': 1,
                'enrollName': employeeName,
            }))
            logging.info("Template already exists at position #" + str(positionNumber))
            while(f.readImage()==True):
                pass
            time.sleep(2)
            enroll(f)
    
        SocketHandler.send_to_all(json.dumps({
            'message': 'enroll-ok',
            'enrollStep': 1,
            'enrollName': employeeName,
        }))
        logging.info("Remove finger...")
        while(f.readImage()==True):
            pass
        time.sleep(1)
    
##############################
        logging.info("Waiting for same finger again...")

        SocketHandler.send_to_all(json.dumps({
            'message': 'enroll',
            'enrollStep': 2,
            'enrollName': employeeName,
        }))
    
        ## Wait that finger is read again
        while(f.readImage()==False or enrollStatus==False):
            if(enrollStatus == True):
                pass
            else:
                SocketHandler.send_to_all(json.dumps({
                    'message': 'clear',
                }))
                verify(f)
    
        ## Converts read image to characteristics and stores it in charbuffer 2
        f.convertImage(0x02)
        if(f.compareCharacteristics() == 0):
            SocketHandler.send_to_all(json.dumps({
                'message': 'enroll-no-match',
                'enrollStep': 2,
                'enrollName': employeeName,
            }))
            logging.debug("Fingerprints no match!")
            while(f.readImage()==True):
                pass
            time.sleep(2)
            enroll(f)


        ## Checks if finger is already enrolled
        result = f.searchTemplate(0x02)
        positionNumber = result[0]
    
        if(positionNumber >= 0):
            SocketHandler.send_to_all(json.dumps({
                'message': 'enroll-exist',
                'enrollStep': 2,
                'enrollName': employeeName,
            }))
            logging.debug("Template already exists at position #" + str(positionNumber))
            while(f.readImage()==True):
                pass
            time.sleep(2)
            enroll(f)

        SocketHandler.send_to_all(json.dumps({
            'message': 'enroll-ok',
            'enrollStep': 2,
            'enrollName': employeeName,
        }))
        logging.debug("Remove finger...")
        while(f.readImage()==True):
            pass
        #time.sleep()
        ## Compares the charbuffers and creates a template
        f.createTemplate()
        template = str(f.downloadCharacteristics(0x01))[1:-1]
        ## Saves template at new position number
        positionNumber = f.storeTemplate()
        if(wsconnected == 1):
          try:
            on_send(json.dumps({
                "topic": "sp:"+hw,
                "event":"new_msg",
                "payload":json.dumps({
                    "type": "enroll-ok",
                    "f_id": int(positionNumber),
                    "employeeID": employeeID,
                    "template": template,
                    "devicegroup": devicegroup.id,
                    "firstname": employeeFirstname,
                    "lastname": employeeLastname,
                    "hw": hw,
                }),
                "ref":""
            }))
          except Exception as e:
            f.deleteTemplate(positionNumber)
            SocketHandler.send_to_all(json.dumps({
                'message': 'enroll-fail',
                'enrollStep': 2,
                'enrollName': employeeName,
            }))
            time.sleep(2)
            enrollStatus = False
            while(f.readImage()==False):
              verify(f) 

          try:
            dbm = Dbm()
            #TODO: fix status value
            dbm.query("insert or replace into employees values("+ str(employeeID) +",'" + str(employeeFirstname) +"','"+ str(employeeLastname)+"', 0, strftime('%s','now'))")
            dbm.query("insert or replace into fingerprints values("+ str(positionNumber) +", "+ str(employeeID) +", '"+str(template)+"')")
          except Exception as e:
            logging.exception("insert: %s" % str(e))

          SocketHandler.send_to_all(json.dumps({
              'message': 'enroll-successful',
              'enrollStep': 2,
              'enrollName': employeeName,
          }))

          logging.info("Finger enrolled successfully!")
          logging.info("New template position #" + str(positionNumber))
          enrollStatus = False
          while(f.readImage()==False):
            verify(f)
        else:
          f.deleteTemplate(positionNumber)
          SocketHandler.send_to_all(json.dumps({
              'message': 'enroll-fail',
              'enrollStep': 2,
              'enrollName': employeeName,
          }))
          time.sleep(2)
          enrollStatus = False
          while(f.readImage()==False):
            verify(f) 
    
    except Exception as e:
        if(devicegroup.id > 0):
            SocketHandler.send_to_all(json.dumps({
                'message': 'no-fingerprint',
            }))
        logging.warning("Operation failed!")
        logging.exception("Exception message: " + str(e))
        fingerprint()

def devicegroupUpdate():
    devicegroup.callUpdate()
    time.sleep(100)
    devicegroupUpdate()

if __name__ == '__main__':
    createDB()
    alterDB()
    devicegroup = DeviceGroup()
    Thread(name='wsClient', target = wsClient).start()

    #init DeviceGroup class an check it which is included in __init__ method
    Thread(name='httpServer', target = httpServer).start()
    time.sleep(4)
    Thread(name='fingerprint', target = fingerprint).start()
    #Thread(name='devicegroupUpdate', target = devicegroupUpdate).start()
