import re
from operator import itemgetter
from datetime import datetime, timedelta, date as dtdate
import dateutil.relativedelta as relativedelta
import tzlocal

def format_endDateTime(endDateTime, trading_exchange_timezone):
    """
    The date string passed into the endDateTime arg of reqHistoricalData() should represent the connecting
    computer's local time and should have no timezone information in it; adding a timezone to the passed-in
    string, while allowed by IB, presents complications because IB's servers throw an error if you pass in
    a Daylight Savings Time timezone. For example, passing in the date string '20150812 15:30:00 EDT' will
    return the IB error: 
    <error id=1, errorCode=321, errorMsg=Error validating request:-'vd' : cause - Historical data query end date/time string [20150812 15:30:00 EDT] is invalid.  Format is 'YYYYMMDD{SPACE}hh:mm:ss[{SPACE}TMZ]'.>
    In order to avoid the error, you must pass in 'EST' instead of 'EDT', even though EDT is correct for
    the month of August. To avoid such complications altogether, this application includes no tmz info in 
    the endDateTime arg, which causes IB to automatically identify the connecting computer's timezone and
    it to the datetime. This function creates and returns such a string. It also returns a datetime object
    of the same time with the trading_exchange_timezone (for use in this package's calculate_durationStr()
    function).
    Args:
        endDateTime (datetime.datetime or str): the string 'now' or a datetime object, which can be either
            naive or timezone-aware and can have any timezone information.
        trading_exchange_timezone (pytz.tzinfo): self-explanatory
    Returns:
        2-tuple:
        1) datetime obj of the passed-in endDateTime with tzinfo set to trading_exchange_timezone
        2) local-time-formatted date string for the endDateTime arg in reqHistoricalData(), e.g.
            '20150812 13:30:00'
    """
    local_timezone = tzlocal.get_localzone()
    if endDateTime == 'now':
        end = datetime.now(tz=local_timezone)
        end_exchange = end.astimezone(trading_exchange_timezone)
        end_str_for_reqHistoricalData = datetime.strftime(end, '%Y%m%d %H:%M:%S')
    else:
        if not isinstance(endDateTime, datetime):
            raise TypeError("endDateTime - {} - must be either the string 'now' or a datetime object".format(endDateTime))
        if endDateTime.tzinfo == None: #assume local time
            if endDateTime > datetime.now(): raise Exception("endDateTime is in the future")
            end_exchange = trading_exchange_timezone.localize(endDateTime)
            end_local = end_exchange.astimezone(local_timezone)
            end_str_for_reqHistoricalData = datetime.strftime(end_local, '%Y%m%d %H:%M:%S')
        elif endDateTime.tzinfo == local_timezone:
            if endDateTime > datetime.now(): raise Exception("endDateTime is in the future")
            end_exchange = endDateTime.astimezone(trading_exchange_timezone)
            end_str_for_reqHistoricalData = datetime.strftime(endDateTime, '%Y%m%d %H:%M:%S')
            
        elif endDateTime.tzinfo == trading_exchange_timezone:
            end_exchange = endDateTime
            end_local = end_exchange.astimezone(local_timezone)
            if end_local > datetime.now(): raise Exception("endDateTime is in the future")
            end_str_for_reqHistoricalData = datetime.strftime(end_local, '%Y%m%d %H:%M:%S')
    return (end_exchange, end_str_for_reqHistoricalData)
        
def calculate_durationStr(length, barSizeSetting, endDateTime, trading_holidays, trading_exchange_timezone, exchange_opening_time, exchange_normal_close_time, exchange_early_close_time):
    """
    Returns the start datetime of the historical info span and the durationStr string to be passed
    into a reqHistoricalData() function. This function handles two complications:
    1) If you want to request historical data for the past 150 days, in 1 day chunks, you can't
    request '150 days', you must request 'x months', because requesting that many days will cause
    IB to return the error
    'errorCode=162: Historical Market Data Service error message:Time length exceed max'.
    2) If you want 150 trading days of data, you need to request ~200 calendar days worth of data to
    account for weekends and holidays, therefore the durationStr should not be '5 M' but rather '7 M'.
    Args:
        length (int): The number of bars in the historical calculation, e.g. A 150-day SMA would pass
        in 150; a 30x 5-min SMA would pass in 30.
        barSizeSetting_value (int): the value of bar sizes to be returned by IB. A 150 hour SMA
            would pass in 1 (you want 1hr chunks); a 30x 5-min SMA would pass in 5 (5 min chunks).
        endDateTime (datetime): a timezone-aware datetime object set to trading_exchange_timezone
        barSizeSetting (str): '1 hour' for 150hr SMA, '5 mins' for 30x 5-min SMA, etc.
        trading_holidays (list): a list of 2-tuples, e.g. (datetime.date, 'full day'/'early close')
        trading_exchange_timezone (pytz.tzfile): A pytz timezone object
        exchange_opening_time (datetime.time): self-explanatory
        exchange_normal_close_time (datetime.time): self-explanatory
        exchange_early_close_time (datetime.time): self-explanatory
    Returns:
        2-tuple:
            1) datetime.datetime of the start of the historical info timespan, 
            2) the durationStr to pass into reqHistoricalData(), e.g. '30 S' or '7 M' or '5 Y';
        
    """
    info_span_start_dt = _calculate_start_datetime_of_historical_request(length, barSizeSetting, endDateTime, trading_holidays, trading_exchange_timezone, exchange_opening_time, exchange_normal_close_time, exchange_early_close_time)
    #set the start time back 1 second to account for the microseconds that will get cutoff
    #from the end time in the ensuing relativedelta calculation; set it back 1 more second
    #because IB will often not send the very most recent second of data in a historical
    #request with a barSizeSetting of '1 sec'
    info_span_start_dt-=timedelta(seconds=2)
    
    #Get time span, #e.g. relativedelta(years=1, months=5, days=30, hours=12)
    rd_obj = relativedelta.relativedelta(info_span_start_dt, endDateTime) 
    rd_yrs = abs(rd_obj.years)
    rd_mo = abs(rd_obj.months)
    rd_days = abs(rd_obj.days)
    rd_hrs = abs(rd_obj.hours)
    rd_mins = abs(rd_obj.minutes)
    rd_secs = abs(rd_obj.seconds)
    
    if rd_yrs > 0:
        durationStr = '{} Y'.format(rd_yrs+1)
    elif rd_mo == 11:
        durationStr = '1 Y'
    elif rd_mo > 0:
        durationStr = '{} M'.format(rd_mo+1)
    elif rd_days == 27:
        durationStr = '1 M'
    elif rd_days >= 6:
        durationStr = '{} W'.format((rd_days//7)+1)
    elif rd_days > 0:
        durationStr = '{} D'.format(rd_days+1)
    elif rd_hrs == 23:
        durationStr = '1 D'
    else:
        num_secs_to_request = rd_hrs*3600 + rd_mins*60 + rd_secs
        durationStr = '{} S'.format(num_secs_to_request)
    return (info_span_start_dt, durationStr)

def fix_barSizeSetting_cruft(barSizeSetting):
    """
    Contrary to IB's online documentation, as of Aug 2015 the string '1 sec' does
    not work; it throws this error:
        <error id=1, errorCode=321, errorMsg=Error validating request:-'vd' : cause -
        Historical data bar size setting is invalid. Legal ones are: 1 secs, 5 secs,
        10 secs, 15 secs, 30 secs, 1 min, 2 mins, 3 mins, 5 mins, 10 mins, 15 mins,
        20 mins, 30 mins, 1 hour, 2 hours, 3 hours, 4 hours, 8 hours, 1 day, 1W, 1M>
    This function changes '1 sec' to '1 secs'
    """
    if barSizeSetting == '1 sec':
        return '1 secs'
    else:
        return barSizeSetting

def calculate_historical_sma(length, historical_values, startDateTime, endDateTime):
    """
    Args:
        length (int): e.g. the 30 in '30-day SMA'
        historical_values (list): list of tuples: 1 historical value per subtuple.
            item 1: datetime.datetime (or datetime.date if durationStr is days);
            item 2: historical data (float)
    """
    #sort list of tuples by datetime (1st item), newest first
    historical_values.sort(key=itemgetter(0), reverse=True)
    #filter out historical values before the startDateTime
    historical_values = historical_values[:length]

    if len(historical_values) < length:
        list_of_values_for_error_msg = ''
        for (date, value) in historical_values:
            list_of_values_for_error_msg+='date={}, value={}\n'.format(date, value)
        error_message = 'There should be {} historical values that lie between {} and {} but IB only returned {} values. Values returned by IB:\n{}'.format(length, startDateTime, endDateTime, len(historical_values), list_of_values_for_error_msg)
        raise IndexError(error_message)
    
    #print historical values
    for historical_value in historical_values:
        print("historicalData date={} value={}".format(historical_value[0], historical_value[1]))
    
    return sum([t[1] for t in historical_values])/len(historical_values) #SMA



def _calculate_start_datetime_of_historical_request(length, barSizeSetting, endDateTime, trading_holidays, trading_exchange_timezone, exchange_opening_time, exchange_normal_close_time, exchange_early_close_time):
    """
    If you want a 50 day SMA, you need to request ~75 calendar days worth of data to account for weekends
    and holidays; if you want a 50 hour SMA, that's about 8 trading days, so you need to request 10-12
    real days accounting for weekends and holidays. This function figures out the oldest date and time
    that the historical data sent from IB needs to include.
    Args:
        see calling function docstring.
    Returns:
        datetime.datetime object representing the start time of the historical request
    """
    barSizeSetting_value, barSizeSetting_type = _parse_barSizeSetting(barSizeSetting) #(150, 'days')
    if barSizeSetting_type == 'day':
        return _x_trading_days_ago_starts_on_this_date(length, endDateTime, trading_holidays, trading_exchange_timezone)
    else:
        return _x_trading_secs_mins_or_hrs_ago_starts_at_this_time(length, barSizeSetting_value, barSizeSetting_type, endDateTime, trading_holidays, trading_exchange_timezone, exchange_opening_time, exchange_normal_close_time, exchange_early_close_time)
    
    
    
def _parse_barSizeSetting(barSizeSetting):
    """
    Args:
        barSizeSetting (str): '1 sec' or '5 secs' or '1 day', etc.
    Returns:
        2-tuple: (1, 'sec')
    """
    barSizeSetting = barSizeSetting.strip() #strip leading and trailing whitespace
    match = re.fullmatch('(\d{1,2}) (sec|secs|min|mins|hour|day)', barSizeSetting)
    if not match: raise Exception("Invalid barSizeSetting: {}".format(barSizeSetting))
    barSizeSetting_value, barSizeSetting_type = match.group(1, 2)
    barSizeSetting_value = int(barSizeSetting_value)
    
    #add or remove ending s if necessary
    if barSizeSetting_value == 1 and barSizeSetting_type[-1] == 's':
        barSizeSetting_type = barSizeSetting_type[:-1]
    if barSizeSetting_value > 1 and barSizeSetting_type[-1] != 's':
        barSizeSetting_type = barSizeSetting_type+'s'
    
    return (barSizeSetting_value, barSizeSetting_type)

def _x_trading_days_ago_starts_on_this_date(number_of_trading_days, endDateTime, trading_holidays, trading_exchange_timezone):
    """
    Iterates back from today, checking each day to see if it's a trading day.
    Once we've gotten to x trading days, return that date.
    Args:
        number_of_trading_days (int): e.g. 1 represents yesterday
        trading_holidays (list): a list of 2-tuples, e.g. (datetime.date, 'full day')
        endDateTime (datetime.datetime): see calling function
    Returns:
        datetime.datetime object, set to midnight
    """
    running_count_of_trading_days_encountered = 0
    running_day = endDateTime.date()
    while running_count_of_trading_days_encountered < number_of_trading_days:
        running_day -= timedelta(days=1)
        if _is_date_a_trading_day(running_day, trading_holidays):
            running_count_of_trading_days_encountered+=1
    dt_to_return = datetime.combine(running_day, datetime.min.time()) #convert date to datetime at midnight
    return trading_exchange_timezone.localize(dt_to_return)

def _x_trading_secs_mins_or_hrs_ago_starts_at_this_time(length, barSizeSetting_value, barSizeSetting_type, endDateTime, trading_holidays, trading_exchange_timezone, exchange_opening_time, exchange_normal_close_time, exchange_early_close_time):
    """
    Returns the datetime x secs, mins or hrs ago, counting
    only time that falls during trading hours.
    Args:
        see calling function
    Returns:
        datetime.datetime object
    """
    if barSizeSetting_type in ('sec', 'secs'):
        seconds_coefficient = 1
    elif barSizeSetting_type in ('min', 'mins'):
        seconds_coefficient = 60
    elif barSizeSetting_type == 'hour':
        seconds_coefficient = 3600
    
    total_trading_secs = length*barSizeSetting_value*seconds_coefficient
    return _subtract_x_trading_secs_from_datetime(endDateTime, total_trading_secs, trading_holidays, exchange_opening_time, exchange_normal_close_time, exchange_early_close_time)
    
def _subtract_x_trading_secs_from_datetime(d, x_trading_secs, trading_holidays, exchange_opening_time, exchange_normal_close_time, exchange_early_close_time):
    """
    Pass in a datetime and this function returns a datetime prior to it with x
    trading seconds subtracted from it. Seconds that do not fall in trading hours
    do not count, ie if the datetime passed in falls during after-hours, the
    function immediately jumps to the end of the previous trading day.
    Args:
        d (datetime.datetime): a timezone-aware datetime object set to the
            exchange timezone
        x_trading_secs (int): the number of seconds to subtract
        others: see calling function docstring
    Returns:
        datetime.datetime object
    """
    if not _does_datetime_fall_during_trading_hours(d, trading_holidays, exchange_opening_time, exchange_normal_close_time, exchange_early_close_time):
        endtime_within_trading_hrs = _calculate_most_recent_trading_day_endtime(d, trading_holidays, exchange_opening_time, exchange_normal_close_time, exchange_early_close_time)
    else:
        endtime_within_trading_hrs = d
    
    trading_day_start_dt = datetime.combine(endtime_within_trading_hrs.date(), exchange_opening_time) #now naive
    trading_day_start_dt = d.tzinfo.localize(trading_day_start_dt) #make timezone-aware again
    total_secs_from_trading_day_start_time_until_endtime = (endtime_within_trading_hrs-trading_day_start_dt).total_seconds()
    if x_trading_secs > total_secs_from_trading_day_start_time_until_endtime: #x_trading_secs spans multiple trading days
        running_count_of_daily_seconds = total_secs_from_trading_day_start_time_until_endtime
        previous_trading_day = _get_previous_trading_day(endtime_within_trading_hrs, trading_holidays)
        while True:
            if _is_date_a_trading_holiday(previous_trading_day, trading_holidays, return_true_for_one_holiday_type_only='early close'):
                close_time = exchange_early_close_time
            else:
                close_time = exchange_normal_close_time
            opening_bell_dt = datetime.combine(previous_trading_day, exchange_opening_time)
            closing_bell_dt = datetime.combine(previous_trading_day, close_time)
            total_sec_in_trading_day = (closing_bell_dt-opening_bell_dt).total_seconds()
            if running_count_of_daily_seconds+total_sec_in_trading_day < x_trading_secs:
                running_count_of_daily_seconds+=total_sec_in_trading_day
                previous_trading_day = _get_previous_trading_day(previous_trading_day, trading_holidays)
                continue
            else:
                num_secs_to_attribute_to_final_day = x_trading_secs - running_count_of_daily_seconds
                dt_to_return = closing_bell_dt-timedelta(seconds=num_secs_to_attribute_to_final_day)
                return d.tzinfo.localize(dt_to_return) #add exchgange timezone info to d_to_return
            
    else: #if x_trading_secs doesn't span >1 trading day
        return endtime_within_trading_hrs-timedelta(seconds=x_trading_secs)

def _is_date_a_trading_day(mydate, trading_holidays):
    """
    Args:
        mydate (datetime.datetime or datetime.date): date to check
        trading_holidays (list): a list of 2-tuples, e.g. (datetime.date, 'full day')
    Returns:
        True or False (bool)
    """
    myweekday = mydate.weekday() #Monday = 0, Tues = 1 ... Sun = 6
    if myweekday == 5 or myweekday == 6: #If the date passed in is a Sat or Sun
        return False
    else:
        if isinstance(mydate, datetime): #convert datetime to date
            mydate = mydate.date()
        for holiday in trading_holidays:
            if mydate == holiday[0]: #if the date passed in is a trading holiday
                if holiday[1] == 'full day':
                    return False
                else:
                    return True
        else: return True

def _is_date_a_trading_holiday(mydate, trading_holidays, return_true_for_one_holiday_type_only=False):
    """
    Returns True if datetime/date object passed in is a trading holiday, False if not.
    Args:
        mydate (datetime.datetime or datetime.date): the date to check
        trading_holidays (tuple): a tuple/list of 2-tuples: (datetime.date, 'full day')
        return_true_for_one_holiday_type_only (str): 'full day', 'early close', or False
    Returns:
        True or False (bool)
    """
    if isinstance(mydate, datetime): #convert datetime to date
        mydate = mydate.date()
    for holiday in trading_holidays:
        if mydate == holiday[0]:
            if return_true_for_one_holiday_type_only == False:
                return True
            else:
                if holiday[1] == return_true_for_one_holiday_type_only:
                    return True
                else:
                    return False
    else: return False

def _does_datetime_fall_during_trading_hours(d, trading_holidays, exchange_opening_time, exchange_normal_close_time, exchange_early_close_time):
    """
    Args:
        d (datetime.datetime): a timezone-aware datetime object set to the exchange timezone
        others: see calling function docstring
    Returns:
        True or False (bool)
    """
    if not _is_date_a_trading_day(d, trading_holidays):
        return False
    if _is_date_a_trading_holiday(d, trading_holidays, return_true_for_one_holiday_type_only='early close'):
        return exchange_opening_time <= d.time() <= exchange_early_close_time
    else:
        return exchange_opening_time <= d.time() <= exchange_normal_close_time

def _calculate_most_recent_trading_day_endtime(d, trading_holidays, exchange_opening_time, exchange_normal_close_time, exchange_early_close_time):
    """
    Pass in a datetime and this function fetches the closing datetime of the previous trading day.
    If the datetime falls on a trading day and is also later than the exchange close time,
    returns the exchange close time of the same trading day.
    Args:
        d (datetime.datetime): a timezone-aware datetime object set to the exchange timezone
        others: see calling function docstring
    Returns:
        a datetime.datetime object representing the trading day closing time of the most
            recent previous trading day
    """
    if _is_date_a_trading_day(d, trading_holidays):
        if not _does_datetime_fall_during_trading_hours(d, trading_holidays, exchange_opening_time, exchange_normal_close_time, exchange_early_close_time):
            if _is_date_a_trading_holiday(d, trading_holidays, return_true_for_one_holiday_type_only='early close'):
                close_time = exchange_early_close_time
            else:
                close_time = exchange_normal_close_time
            if d.time() > close_time:
                d_to_return = datetime.combine(d.date(), close_time)
                return d.tzinfo.localize(d_to_return) #add exchgange timezone to d_to_return
    
    previous_trading_day = _get_previous_trading_day(d, trading_holidays)
    if _is_date_a_trading_holiday(previous_trading_day, trading_holidays, return_true_for_one_holiday_type_only='early close'):
        d_to_return = datetime.combine(previous_trading_day, exchange_early_close_time)
    else:
        d_to_return = datetime.combine(previous_trading_day, exchange_normal_close_time)
    return d.tzinfo.localize(d_to_return) #add exchgange timezone to d_to_return

def _get_previous_trading_day(d, trading_holidays):
    """
    Pass in a datetime object and this function returns the date of the previous trading day
    Args:
        d (datetime.datetime or datetime.date): any datetime.datetime/date object
        trading_holidays (list): a list of 2-tuples, e.g. (datetime.date, 'full day')
    Returns:
        datetime.date object of previous trading day
    """
    while True:
        d-=timedelta(days=1)
        if _is_date_a_trading_day(d, trading_holidays):
            if isinstance(d, datetime): #if datetime.datetime obj
                return d.date() #convert to datetime.date obj
            else: #if already a datetime.date obj
                return d