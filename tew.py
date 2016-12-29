class WsClient:
    def __init__(self):
        self.ws = websocketClient.WebSocketApp(host)
        try:
          ws.on_open = self.on_open
          self.ws.on_message = self.on_message
          self.ws.on_error = self.on_error
          self.ws.run_forever(ping_interval=30, ping_timeout=10)
        except Exception as e:
          print('start: ---Exception message: ' + str(e))
          time.sleep(10)

    def on_open(self):
        def run(*args):
            # send the message, then wait
            # so thread doesn't exit and socket
            # isn't closed
            self.ws.send(json.dumps({
                "topic":hw,
                "event":"phx_join",
                "payload":"",
                "ref":""
            }))
    
        thread.start_new_thread(run, ())
    
    def on_send(self, message):
        try:
          self.ws.send(message)
          print("sent: "+message)
        except Exception as e:
          print('on_send: ---Exception message: ' + str(e))
    
    def on_message(self, message):
        message = json.loads(message) 
        response = message["payload"]["response"]
        print response
        if(response["type"] == "devicegroup"):
          global devicegroup
          devicegroup = response["result"][0]
          print devicegroup
          conn = sqlite.connect('att')
          c = conn.cursor()
          c.execute("PRAGMA key='"+pragma+"'")
          c.execute("""update config set devicegroup = """+devicegroup) 
          conn.commit()
    
    def on_error(self, ws, error):
        try:
          print(error)
          time.sleep(10)
          self.start()
        except Exception as e:
          print('ws-on_error: ---Exception message: ' + str(e))
          time.sleep(10)
          self.start()
    
    def on_close(self, ws, status):
        try:
          print("### closed ###")
          time.sleep(10)
          self.start()
        except Exception as e:
          print('on_close: ---Exception message: ' + str(e))
          time.sleep(10)
          self.start()
    
    def start(self):
        print(type (self.ws))
        self.start()
