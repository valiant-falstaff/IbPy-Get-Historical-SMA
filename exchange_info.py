import pytz, re
from datetime import datetime, time as dttime

trading_exchange_timezone = pytz.timezone('US/Eastern')
exchange_opening_time = dttime(hour=9, minute = 30)
exchange_normal_close_time = dttime(hour=16)
exchange_early_close_time = dttime(hour=13)
trading_holidays = ( #US Exchanges
    #We record back to 2010 because we can request up to 5yrs of historical data
    ('1/1/2010', 'full day'), 
    ('1/18/2010', 'full day'), 
    ('2/15/2010', 'full day'), 
    ('4/4/2010', 'full day'), 
    ('5/31/2010', 'full day'), 
    ('7/5/2010', 'full day'), 
    ('9/6/2010', 'full day'), 
    ('11/25/2010', 'full day'), 
    ('11/26/2010', 'early close'), 
    ('12/24/2010', 'full day'),  
    
    ('1/17/2011', 'full day'), 
    ('2/21/2011', 'full day'), 
    ('4/22/2011', 'full day'), 
    ('5/30/2011', 'full day'), 
    ('7/4/2011', 'full day'), 
    ('9/5/2011', 'full day'), 
    ('11/24/2011', 'full day'), 
    ('11/25/2011', 'early close'), 
    ('12/26/2011','full day'), 
    
    ('1/2/2012', 'full day'), 
    ('1/16/2012', 'full day'), 
    ('2/20/2012', 'full day'), 
    ('4/6/2012', 'full day'), 
    ('5/28/2012', 'full day'), 
    ('7/3/2012', 'early close'), 
    ('7/4/2012', 'full day'), 
    ('9/3/2012', 'full day'), 
    ('11/22/2012', 'full day'), 
    ('11/23/2012', 'early close'), 
    ('12/24/2012', 'early close'), 
    ('12/25/2012','full day'), 
    
    ('1/1/2013', 'full day'), 
    ('1/21/2013', 'full day'), 
    ('2/18/2013', 'full day'), 
    ('3/29/2013', 'full day'), 
    ('5/27/2013', 'full day'), 
    ('7/3/2013', 'early close'), 
    ('7/4/2013', 'full day'), 
    ('9/2/2013', 'full day'), 
    ('11/28/2013', 'full day'), 
    ('11/29/2013', 'early close'), 
    ('12/24/2013', 'early close'), 
    ('12/25/2013','full day'), 
    
    ('1/1/2014', 'full day'), 
    ('1/20/2014', 'full day'), 
    ('2/17/2014', 'full day'), 
    ('4/18/2014', 'full day'), 
    ('5/26/2014', 'full day'), 
    ('7/3/2014', 'early close'), 
    ('7/4/2014', 'full day'), 
    ('9/1/2014', 'full day'), 
    ('11/27/2014', 'full day'), 
    ('11/28/2014', 'early close'), 
    ('12/24/2014', 'early close'), 
    ('12/25/2014','full day'), 
    
    ('1/1/2015', 'full day'), 
    ('1/19/2015', 'full day'), 
    ('2/16/2015', 'full day'), 
    ('4/3/2015', 'full day'), 
    ('5/25/2015', 'full day'), 
    ('7/3/2015', 'full day'), 
    ('9/7/2015', 'full day'), 
    ('11/26/2015', 'full day'), 
    ('11/27/2015', 'early close'), 
    ('12/24/2015', 'early close'), 
    ('12/25/2015', 'full day'), 
    
    ('1/1/2016', 'full day'), 
    ('1/18/2016', 'full day'), 
    ('2/15/2016', 'full day'), 
    ('3/25/2016', 'full day'), 
    ('5/30/2016', 'full day'), 
    ('7/3/2016', 'early close'), 
    ('7/4/2016', 'full day'), 
    ('9/5/2016', 'full day'), 
    ('11/25/2016', 'early close'), 
    ('12/26/2016', 'full day'), 
)

def convert_trading_holiday_datestrings_into_date_objects(trading_holidays):
    """
    Args:
        trading_holidays (list/tuple): a list of 2-tuples; 1st item of each
            tuple: a datestring formatted as mm/dd/YYYY or m/d/YYYY
            (zero-padding not necessary); 2nd item: 'full day' or 'early close'
    Returns:
        list of 2-tuples with first item in each tuple converted to a
        datetime.date obj
    """
    converted_trading_holidays = []
    for holiday in trading_holidays:
        #syntax check
        date = holiday[0].strip() #strip leading and trailing whitespace
        match = re.fullmatch('(\d{1,2})/(\d{1,2})/(\d{4})', date)
        if not match:
            raise Exception("Syntax of date {} in the trading holidays list "
                "is invalid".format(date))
        
        #zero-pad month and day if necessary
        month, day, year = match.group(1, 2, 3)
        if len(month) == 1:
            month = "0{}".format(month)
        if len(day) == 1:
            day = "0{}".format(day)
        
        converted_date = datetime.strptime('{}/{}/{}'.format(month, day, year),
            '%m/%d/%Y').date()
        converted_trading_holidays.append( (converted_date, holiday[1]) )
    
    return converted_trading_holidays

trading_holidays = convert_trading_holiday_datestrings_into_date_objects(
    trading_holidays)