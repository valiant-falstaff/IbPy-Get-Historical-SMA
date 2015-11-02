#!/usr/bin/python3
from datetime import datetime

import exchange_info
from myib import MyIb
from security import Security

def error_handler(msg):
    """Callback to 'Error' message."""
    #faux error messages; they mean we've successfully connected to IB's servers
    if msg.errorCode in (2104, 2106, 2108):
        pass
    else: #An actual error
        raise Exception("We've received an error message from IB:\n{}".format(
            msg))

def main():
    #setup
    my_ib = MyIb()
    Security.set_trading_exchange_information(
        exchange_info.trading_exchange_timezone, 
        exchange_info.exchange_opening_time, 
        exchange_info.exchange_normal_close_time, 
        exchange_info.exchange_early_close_time, exchange_info.trading_holidays)
    
    #create security object
    my_security = Security(my_ib, symbol='GOOG', secType='STK',
        exchange='SMART')
    
    #Register callbacks
    my_ib.conn.register(error_handler, 'Error')
    my_ib.conn.register(my_security.save_historical_data, 'HistoricalData')
    
    my_ib.connect_to_ib_servers()
    
    #get SMA
    sma = my_security.get_historical_sma(length=150, barSizeSetting='1 day',
        ohlc='CLOSE', whatToShow='MIDPOINT', endDateTime='now')
    print("My SMA: {}".format(sma))
    
    print(sma)

    my_ib.conn.disconnect()

if __name__ == "__main__": main()