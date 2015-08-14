import time, re
from datetime import datetime, timedelta
import dateutil.relativedelta as relativedelta
import tzlocal

from ib.ext.Contract import Contract

from . import helper_functions

class Security:
    """
    An object of this class represents any ticker symbol: SPY, IBM, MSFT, etc. Due to this broadness,
    'Security' is a bit of a misnomer: this can be any financial measurable, such as an index like
    the VIX, which technically isn't a security. But 'Security' is a much more associative term than
    something as vague as 'Measurable'.
    """
    
    @classmethod
    def set_trading_exchange_information(cls, trading_exchange_timezone, exchange_opening_time, exchange_normal_close_time, exchange_early_close_time, trading_holidays):
        cls.trading_exchange_timezone = trading_exchange_timezone
        cls.exchange_opening_time = exchange_opening_time
        cls.exchange_normal_close_time = exchange_normal_close_time
        cls.exchange_early_close_time = exchange_early_close_time
        cls.trading_holidays = trading_holidays
    
    def __init__(self, my_ib, symbol, secType, exchange, primaryExch=None, currency='USD'):
        """
        Args:
            my_ib (MyIb): a MyIb object defined in this Python package
            symbol (str): ticker symbol: 'GOOG', 'IBM', 'SPY', 'VIX', etc.
            secType (str): security type: 'STK', 'FUT', 'IND', etc.
            exchange (str): 'NASDAQ', 'CBOE', etc. Set to 'SMART' to use IB's SmartRouting ('SMART' is invalid
                for some securities, e.g. 'VIX' requires 'CBOE').
            primaryExch (str): Resolves ambiguity when exchange is 'SMART' and the security is traded on more
                than one exchange. For instance, Apple is traded on both the NASDAQ and in Europe, so if the
                exchange attribute is SMART, IB doesn't know which exchange to trade it on. The ambiguity is
                resolved by setting primaryExch to e.g. 'NASDAQ' or 'LON'.
            currency (str): 'USD', 'EUR', etc.
        """
        self.my_ib = my_ib
        self.symbol = symbol
        self.secType = secType
        self.exchange = exchange
        self.primaryExch = primaryExch
        self.currency = currency
        self.contract = self._create_security_contract()
    
    def _create_security_contract(self):
        """To pass into IB messages"""
        contract = Contract()
        contract.m_symbol = self.symbol
        contract.m_secType = self.secType
        contract.m_exchange = self.exchange
        if self.primaryExch != None: #don't set m_primaryExch at all if None
            contract.m_primaryExch = self.primaryExch
        contract.m_currency = self.currency
        return contract

    def get_historical_sma(self, length, barSizeSetting, ohlc, whatToShow, endDateTime='now'):
        """
        Returns a historical SMA value. This has limits; for instance, you cannot reach back more than
        1-5 years into the past (depending on account type). This is not the only limitation: see
        https://www.interactivebrokers.com/en/software/api/apiguide/tables/historical_data_limitations.htm
        for full details.
        Args:
            length (int): The 30 in '30-day SMA', 50 in '50 5-min SMA', etc.
            endDateTime (datetime.datetime or str): If you want a 10hr SMA ending on 7/15/2015 11:30am
                (i.e. one that spans from 7/14/2015 10:00am to 7/15/2015 11:30am), pass in a
                datetime.datetime object set to that time. Otherwise, pass in 'now' for an end
                time of now. The datetime can be naive or timezone-aware; if naive, the time will be
                assumed to represent the time of the trading exchange.
            ohlc (str): 'OPEN', 'HIGH', 'LOW', 'CLOSE', or 'AVG' - 'AVG' takes the high/low average;
            others: see interactivebrokers.com/en/software/api/apiguide/java/reqhistoricaldata.htm
        Returns:
            The historical SMA value (float)
        """
        #set attrs used by self.save_historical_data()
        self.ohlc = ohlc
        if 'day' in barSizeSetting:
            self.historicalReq_date_str_fmt = '%Y%m%d'
        else: #otherwise bars are < 1 day
            self.historicalReq_date_str_fmt = '%Y%m%d  %H:%M:%S' #2 spaces between day and hour
        
        self.have_we_received_all_historical_data_from_ib = False
        self.historical_data = []
        
        reqId = self.my_ib.generate_new_reqId()
        eDT_for_calculate_durationStr, eDT_for_reqHistoricalData = helper_functions.format_endDateTime(endDateTime, self.trading_exchange_timezone)
        startDateTime, durationStr = helper_functions.calculate_durationStr(length, barSizeSetting, eDT_for_calculate_durationStr, self.trading_holidays, self.trading_exchange_timezone, self.exchange_opening_time, self.exchange_normal_close_time, self.exchange_early_close_time)
        barSizeSetting = helper_functions.fix_barSizeSetting_cruft(barSizeSetting)
        
        self.my_ib.conn.reqHistoricalData(reqId, self.contract, endDateTime=eDT_for_reqHistoricalData, durationStr=durationStr, barSizeSetting=barSizeSetting, whatToShow=whatToShow, useRTH=1, formatDate=1)
        while not self.have_we_received_all_historical_data_from_ib:
            time.sleep(0.1)

        return helper_functions.calculate_historical_sma(length, self.historical_data, startDateTime, eDT_for_calculate_durationStr)
    
    def save_historical_data(self, msg):
        """Callback to reqHistoricalData()"""
        try:
            self._save_historicalData_price(msg)
        except ValueError as e: #will happen on final historicalData msg
            if 'finished' in msg.date:
                self.have_we_received_all_historical_data_from_ib = True
            else: raise e
    
    def _save_historicalData_price(self, msg):
        msg_dt = datetime.strptime(msg.date, self.historicalReq_date_str_fmt).date() #convert date string to date obj
        ohlc = self.ohlc.lower()
        if ohlc == 'open':
            target_value = msg.open
        elif ohlc == 'high':
            target_value = msg.high
        elif ohlc == 'low':
            target_value = msg.low  
        elif ohlc == 'close':
            target_value = msg.close
        elif ohlc == 'avg':
            target_value = (msg.high+msg.low)/2  
        self.historical_data.append((msg_dt, target_value))