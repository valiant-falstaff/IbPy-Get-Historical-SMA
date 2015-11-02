import time, threading
from ib.opt import Connection

class MyIb:
    def __init__(self, port=7496, clientId=100):
        self.reqId = 0
        self.conn = Connection.create(port=port, clientId=clientId)
    
    def connect_to_ib_servers(self):
        """Blocks until successfully connected to IB."""
        if hasattr(self.conn, 'isConnected'): #If conn has never connected to
            #TWS, it won't have the isConnected() method
            if self.conn.isConnected():
                return
        self.conn.connect()
        while self.conn.isConnected() == False:
            time.sleep(0.05)
    
    def generate_new_reqId(self):
        '''
        Every time you send information to IB's servers you need to attach a
        number that uniquely identifies the request. IB sends this number back
        with the requested information, allowing you to keep track of which
        information corresponds to which request.
        '''
        with threading.Lock():
            self.reqId+=1
            return self.reqId