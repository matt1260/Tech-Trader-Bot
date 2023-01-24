# T3 Trader Bot
# v1.0

# TD Ameritrade Python module - https://github.com/areed1192/td-ameritrade-api

'''NQBear and NQbull signals require 50 historical bars. 
Start script 40 minutes before open to include PM data.
No buy signals will then be possible for the first 10 minutes.'''

from datetime import datetime
import datetime
import pytz
import time
import asyncio
import pandas as pd
import csv
from csv import writer
import os.path
from configparser import ConfigParser
from td.client import TdAmeritradeClient
from td.credentials import TdCredentials
from td.utils.enums import OrderStatus
from td.utils.enums import ChartServices
from td.utils.enums import ChartEquity
import talib as ta

set_timezone = pytz.timezone('America/New_York')

config = ConfigParser()
config.read('config/config.ini')
client_id = config.get('main', 'client_id')
redirect_uri = config.get('main', 'redirect_uri')
account_no = config.get('main', 'account_number')

print('Getting TD Ameritrade credentials')
td_credentials = TdCredentials(
    client_id=client_id,
    redirect_uri=redirect_uri,
    credential_file='config/td_credentials.json'
)

print('Creating new TD Ameritrade session')
td_client = TdAmeritradeClient(
    credentials=td_credentials
)

# global variables

# Ticker(s) to trade
symbol1 = 'QQQ'
assetType1 = 'INDEX'

#symbol2 = 'NVDA'
#assetType2 = 'INDEX'

#symbol3 = 'MRNA'
#assetType3 = 'INDEX'

# Share size to trade
quantity = 100

openorder = False


if symbol1:

    # check for existing trade log file and create new one if it doesn't
    timestr = datetime.datetime.now().strftime("%Y_%m_%d")

    if os.path.exists('logs/' + timestr + "_" + symbol1 + "_share_trade_log.csv"):
        print('Trade log file already exists')
    else:
        print('Creating new trade log file')
        headers = ['datetime', 'fill_price', 'symbol', 'orderid', 'instruction',
                'desc', 'quantity', 'status', 'share_pnl', 'cumulative_pnl']
        with open('logs/' + timestr + "_" + symbol1 + "_share_trade_log.csv", "w", newline='') as log:
            csv_output = csv.DictWriter(log, fieldnames=headers)
            csv_output.writeheader()

########## SIGNALS ##########
print('Loading signal calculations')
def SMA(price):
    sma5 = ta.SMA(price,5)
    sma10 = ta.SMA(price,10)
    sma20 = ta.SMA(price,20)
    
    crossdown = ((sma5 <= sma10) & (sma5.shift(1) >= sma10.shift(1)))
    crossup = ((sma5 >= sma10) & (sma5.shift(1) <= sma10.shift(1)))

    sellcrossup = ((sma5 >= sma20) & (sma5.shift(1) <= sma20.shift(1)))
    sellcrossdown = ((sma5 <= sma20) & (sma5.shift(1) >= sma20.shift(1)))

    return crossdown, crossup, sellcrossup, sellcrossdown

def NQ_scalp(open, close, high, low):

    ema = ta.EMA(close, 10)
    ema20 = ta.EMA(close, 20)
    ema50 = ta.EMA(close, 50)

    bull = ((close > open) & (low < low.shift(1)) & (high < high.shift(1)) & (close > ema) & (ema > ema20) & (ema20 > ema50))
    bear = ((close < open) & (low > low.shift(1)) & (high > high.shift(1)) & (close < ema) & (ema < ema20) & (ema20 < ema50))
    
    return bull, bear

def reversal_top(open, close, low):
    tr = ((close <= low) & (close >= (low - 0.02)) & (close < open.shift(1)) & (open.shift(3) < close) & (close < close.shift(2)))
    return tr

def reversal_top2(open, close, swinghigh):
    tr2 = (swinghigh.shift(1) | swinghigh.shift(2) | swinghigh.shift(3)) & ((open-close) > (abs(open.shift(1)-close.shift(1)) * 3))
    return tr2

def reversal_top3(open, close):
    tr3 = ((open - close) > (close.shift(1) - open.shift(1))) & ((close.shift(1) - open.shift(1)) > 0.30)
    return tr3

def reversal_top4(close, high, low, swinghigh):
    tr4 = (close < low.shift(4)) & (high < (high.shift(1) + 0.20)) & (swinghigh.shift(1) | swinghigh.shift(2) | swinghigh.shift(3))
    return tr4

def swingHighLow(high, low):

    swinglow = (low < low.shift(1)) & (low < low.shift(2)) & (low < low.shift(3)) & (low < low.shift(4)) & (low < low.shift(5)) & (low < low.shift(6)) & (low < low.shift(7)) & (low < low.shift(8)) & (low < low.shift(9))
    swinghigh = (high > high.shift(1)) & (high > high.shift(2)) & (high > high.shift(3)) & (high > high.shift(4)) & (high > high.shift(5)) & (high > high.shift(6)) & (high > high.shift(7)) & (high > high.shift(8)) & (high > high.shift(9))

    return swinglow, swinghigh

def swing10(swinglow, swinghigh):
    
    swinglow10 = swinglow.shift(1) | swinglow.shift(2) | swinglow.shift(3) | swinglow.shift(4) | swinglow.shift(5) | swinglow.shift(6) | swinglow.shift(7) | swinglow.shift(8) | swinglow.shift(9) | swinglow.shift(10)
    swinghigh10 = swinghigh.shift(1) | swinghigh.shift(2) | swinghigh.shift(3) | swinghigh.shift(4) | swinghigh.shift(5) | swinghigh.shift(6) | swinghigh.shift(7) | swinghigh.shift(8) | swinghigh.shift(9) | swinghigh.shift(10)

    return swinglow10, swinghigh10

def swing6(swinglow, swinghigh):
    
    swinglow6 = swinglow.shift(1) | swinglow.shift(2) | swinglow.shift(3) | swinglow.shift(4) | swinglow.shift(5) | swinglow.shift(6)
    swinghigh6 = swinghigh.shift(1) | swinghigh.shift(2) | swinghigh.shift(3) | swinghigh.shift(4) | swinghigh.shift(5) | swinghigh.shift(6)

    return swinglow6, swinghigh6

def bbcross(crossup, crossdown):
    
    bullcross = crossup | crossup.shift(1) | crossup.shift(2) | crossup.shift(3) | crossup.shift(4) | crossup.shift(5) | crossup.shift(6) | crossup.shift(7) | crossup.shift(8) | crossup.shift(9)
    bearcross = crossdown | crossdown.shift(1) |  crossdown.shift(2) | crossdown.shift(3) |  crossdown.shift(4) | crossdown.shift(5) | crossdown.shift(6) | crossdown.shift(7) | crossdown.shift(8) | crossdown.shift(9)
    return bullcross, bearcross

def drop(open, close):
    
    drop = ((open-close) >= .40) & (close < open) & (close.shift(1) < open.shift(1)) & (close.shift(2) < open.shift(2)) & ((open.shift(1)-close.shift(1)) < (open-close / 3)) & ((open-close) > (open.shift(1)-close.shift(1))*3)
    return drop

def pop(open, close, high):
    
    pop = ((close-open) >= .30) & (open > open.shift(1)) & ((close-open) > (close.shift(1)-open.shift(1))*3) & (open > close.shift(2)) & ((close-open) > (high-close))
    return pop


########## ORDER FUNCTIONS ##########
print('Loading share order functions...')

def place_long_order(symbol):
    print ('Placing order for ' + symbol + ' at ' + str(price))
    
    share_order = {
        "orderType": "MARKET",
        "session": "NORMAL",
        "duration": "DAY",
        "price": price,
        "orderStrategyType": "SINGLE",
        "orderLegCollection": [
        {
            "instruction": "BUY",
            "quantity": quantity,
            "instrument": {
            "symbol": symbol,
            "assetType": "INDEX"
            }
        }
        ]
    }
    
    orders_service = td_client.orders()

    response = orders_service.place_order(account_id=account_no, order_dict=share_order)
    print(response) # should be ID
    print('Successfully placed order for ' + symbol + ' at ' + str(price))

def place_short_order(price):
    print ('Placing short order for ' + symbol + ' at ' + str(price))
    
    share_order = {
        "orderType": "MARKET",
        "session": "NORMAL",
        "duration": "DAY",
        "price": price,
        "orderStrategyType": "SINGLE",
        "orderLegCollection": [
        {
            "instruction": "SELL",
            "quantity": quantity,
            "instrument": {
            "symbol": symbol,
            "assetType": assetType
            }
        }
        ]
    }
    
    orders_service = td_client.orders()

    response = orders_service.place_order(account_id=account_no, order_dict=share_order)
    print(response) # should be ID
    print('Successfully placed order for ' + symbol + ' at ' + str(price))

# replace order at market not used
def replace_market_order(orderid, symbol, bidprice):
    print ('Replacing sell order for #' + str(orderid) + ' at market')

    replace_option_order = {
        "session": "NORMAL",
        "duration": "DAY",
        "orderStrategyType": "SINGLE",
        "orderType": "MARKET",
        #"price": bidprice,
        #"price": 0.15,
        "orderLegCollection": [
        {
            "instruction": "SELL_TO_CLOSE",
            "quantity": quantity,
            "instrument": {
            "assetType": "OPTION",
            "symbol": contract_symbol
            }
        }
        ]
    }

    orders_service = td_client.orders()

    response = orders_service.replace_order(
            account_id=account_no,
            order_id=orderid,
            order_dict=replace_option_order)
    print(response) # should be ID
    
    print('Successfully replaced sell order for ' + str(orderid) + ' at market')

def place_close_short_order(symbol):
    
    lastprice, bidprice = get_mark(symbol)

    close_short_order = {
        "orderType": "LIMIT",
        "session": "NORMAL",
        "duration": "GOOD_TILL_CANCEL",
        "orderStrategyType": "SINGLE",
        "price": lastprice,
        "orderLegCollection": [
            {
            "instrument": {
                "assetType": "INDEX",
                "symbol": symbol
            },
            "instruction": "BUY_TO_CLOSE",
            "quantity": quantity
            }
        ]
    }
    orders_service = td_client.orders()
    print('Trying to place order for ', symbol)
    response = orders_service.place_order(account_id=account_no, order_dict=close_short_order)
    print(response) # should be ID
    print('Successfully placed sell order for ' + symbol + ' at ' + str(lastprice))

    # get sell order id, check
    time.sleep(1) # give it a second to fill
    orderid, order_symbol = view_working_orders()
    global openorder

    while orderid is None:
        time.sleep(1)
        print('Checking for order id...')
        orderid, order_symbol = view_working_orders() # try again for working order id
        if orderid is not None:
            print('Order #' + str(orderid) + ' for ' + symbol + ' is still working...')
            break

        close_time, order_symbol, orderid, instruction, desc, quantity, status, price = view_last_filled_orderid() # check if order was filled if it can't get working order

        if order_symbol == symbol:
            print('Option order for ' + order_symbol + ' was successfully filled for ' + str(symbol))
            openorder = False
            log_close_short_order()
            return order_symbol, price # order filled, exit monitoring loop

    if orderid is not None:
        # if sell order has not yet been filled, monitor, and set to bid after 5 seconds
    
        if order_symbol == symbol: # check that it is the same order just placed

            ######## FIRST ORDER LOOP #########
            # this will run one addtional time after replace order loop is broken

            max_checks = 6
            i = 0
            while i < max_checks:
        
                order_status, order_symbol = get_order_status(orderid) # check order status
                
                if order_status == 'FILLED':
                    print('Close short order for ' + order_symbol + ' was successfully filled.')
                    openorder = False
                    log_close_short_order()
                    break

                elif order_status == 'CANCELED': # check for cancellation
                    print('Order was cancelled or replaced')
                    
                    break

                else:
                    print('Order #' + str(orderid) + ' for ' + symbol + ' is ' + order_status)
                    time.sleep(1) # wait 1 second to check again
                    i += 1

                    # set to bid after 5 seconds
                    if i == 6: 
                        print('Setting sell price to bid')
                        lastprice = get_mark(symbol)
                        replace_sell_order(orderid, symbol, bidprice)
                        
                        orderid, symbol = view_working_orders() # get last working order id, symbol

                        while orderid is None:
                            time.sleep(1)
                            print('Checking for order id...')
                            orderid, symbol = view_working_orders() # try again for working order id
                            if orderid is not None:
                                print('Order #' + str(orderid) + ' for ' + symbol + ' is still working...')
                                break

                            close_time, order_symbol, orderid, instruction, desc, quantity, status, price = view_last_filled_orderid() # check if order was filled if it can't get working order

                            if order_symbol == symbol:
                                print('Option order for ' + order_symbol + ' was successfully filled for ' + str(price))
                                openorder = False
                                log_close_short_order()
                                return order_symbol, price # order filled, exit monitoring loop

                        
                        if orderid is not None:
                        # if order has not yet been filled, monitor and set to bid again
                    
                            if order_symbol == symbol: # check that it is the same order just placed
                                
                                ######## SECOND REPLACE ORDER LOOP #########

                                max_checks = 6
                                i = 0
                                while i < max_checks:
                            
                                    order_status, symbol = get_order_status(orderid) # check order status
                                    
                                    if order_status == 'FILLED':
                                        print('Close short order for ' + order_symbol + ' was successfully filled.')
                                        openorder = False
                                        log_close_short_order()
                                        break

                                    elif order_status == 'CANCELED':
                                        print('Order was cancelled or replaced')
                                        break

                                    else:
                                        print('Order #' + str(orderid) + ' for ' + symbol + ' is ' + order_status)
                                        time.sleep(1) # wait 1 second to check again
                                        i += 1
                                    
                                    if i == 6:
                                        print('Sell order was not filled')
                            
                       
        else:
            print('Last close short order was cancelled manually or queued order does not match')
            openorder = False
            log_close_short_order()

def view_working_orders():
        
    today = datetime.date.today()
    orders_service = td_client.orders()
    
    # get working orders
    orders = orders_service.get_orders_by_path(
        from_entered_time=today,
        account_id=account_no,
        order_status=OrderStatus.Working
    )

    if orders:
        if len(orders) > 2:
            print ('There are at least three working orders:')

            quantity = orders[0]['quantity']
            filledquantity = orders[0]['filledQuantity']
            remainingquantity = orders[0]['remainingQuantity']
            symbol1 = orders[0]['orderLegCollection'][0]['instrument']['symbol']
            description = orders[0]['orderLegCollection'][0]['instrument']['description']
            order_id = orders[0]['orderId']
            print('Working order: ' + str(order_id) + ', ' + description + ', Quantity: ' + str(quantity) + ', Filled: ' + str(filledquantity))
            
            quantity = orders[1]['quantity']
            filledquantity = orders[1]['filledQuantity']
            remainingquantity = orders[1]['remainingQuantity']
            order_symbol = orders[1]['orderLegCollection'][0]['instrument']['symbol']
            description = orders[1]['orderLegCollection'][0]['instrument']['description']
            order_id2 = orders[1]['orderId']
            print('Working order: ' + str(order_id2) + ', ' + description + ', Quantity: ' + str(quantity) + ', Filled: ' + str(filledquantity))

            quantity = orders[2]['quantity']
            filledquantity = orders[2]['filledQuantity']
            remainingquantity = orders[2]['remainingQuantity']
            symbol3 = orders[2]['orderLegCollection'][0]['instrument']['symbol']
            description = orders[2]['orderLegCollection'][0]['instrument']['description']
            order_id3 = orders[2]['orderId']
            print('Working order: ' + str(order_id3) + ', ' + description + ', Quantity: ' + str(quantity) + ', Filled: ' + str(filledquantity))
            return order_id, symbol1

        elif len(orders) > 1:
            print ('There are two working orders:')
            
            quantity = orders[0]['quantity']
            filledquantity = orders[0]['filledQuantity']
            remainingquantity = orders[0]['remainingQuantity']
            symbol1 = orders[0]['orderLegCollection'][0]['instrument']['symbol']
            description = orders[0]['orderLegCollection'][0]['instrument']['description']
            order_id = orders[0]['orderId']
            print('Working order: ' + str(order_id) + ', ' + description + ', Quantity: ' + str(quantity) + ', Filled: ' + str(filledquantity))

            quantity = orders[1]['quantity']
            filledquantity = orders[1]['filledQuantity']
            remainingquantity = orders[1]['remainingQuantity']
            order_symbol = orders[1]['orderLegCollection'][0]['instrument']['symbol']
            description = orders[1]['orderLegCollection'][0]['instrument']['description']
            order_id2 = orders[1]['orderId']
            print('Working order: ' + str(order_id2) + ', ' + description + ', Quantity: ' + str(quantity) + ', Filled: ' + str(filledquantity))
            return order_id, symbol1

        else:
            print('There is one working order:')
            quantity = orders[0]['quantity']
            filledquantity = orders[0]['filledQuantity']
            remainingquantity = orders[0]['remainingQuantity']
            symbol = orders[0]['orderLegCollection'][0]['instrument']['symbol']
            description = orders[0]['orderLegCollection'][0]['instrument']['description']
            order_id = orders[0]['orderId']
            print('Working order: ' + str(order_id) + ', ' + description + ', Quantity: ' + str(quantity) + ', Filled: ' + str(filledquantity))
            return order_id, symbol
    
    else: 
        print('No working orders.')
        return None, None

def view_last_filled_orderid() :
    today = datetime.date.today()

    orders_service = td_client.orders()

    # Query last filled order
    orders = orders_service.get_orders_by_path(
            from_entered_time=today,
            account_id=account_no,
            order_status=OrderStatus.Filled
        )
    if orders:
        orderlegcollection = orders[0]['orderLegCollection']
        #stopprice = orders[0]['stopPrice']
        orderid = orders[0]['orderId']
        close_time = orders[0]['closeTime']
        symbol = orders[0]['orderLegCollection'][0]['instrument']['symbol']
        price = orders[0]['orderActivityCollection'][0]['executionLegs'][0]['price']
        instruction = orderlegcollection[0]['instruction']
        instrument = orderlegcollection[0]['instrument']
        desc = instrument['description']
        status = orders[0]['status']
        quantity = orders[0]['filledQuantity']
        print ('Last Filled Order: #' + str(orderid) + ', ' + instruction + ' ' + desc + ', ' +  str(quantity) + ' ' + status + ' for ' + str(price)) 
        return close_time, symbol, orderid, instruction, desc, quantity, status, price
        
    else:
        print('No filled orders today')
        return None, None, None, None, None, None, None, None

def get_mark(symbol):
    quote_service = td_client.quotes()
  
    quote = quote_service.get_quotes(instruments=[symbol])

    bid_price = quote[symbol]['bidPrice']
    ask_price = quote[symbol]['askPrice']
    last_price = quote[symbol]['lastPrice']

    print(symbol + ' last: ' + str(last_price) + ', bid: ' + str(bid_price) + ', ask: ' + str(ask_price))

    return last_price

def cancel_order(orderid):

    # Cancel order
    order_status = ''
    while order_status != 'CANCELED':
        
        orders_service = td_client.orders()
        orders_service.cancel_order(
                account_id=account_no,
                order_id=orderid
            )
        order_status, symbol = get_order_status(orderid)
        if order_status == 'CANCELED':
            print('Order was canceled')
            break

def get_order_status(orderid):
    orders_service = td_client.orders()

    # Query order
    order = orders_service.get_order(
            account_id=account_no,
            order_id=orderid
        )
    order_status = order['status']
    symbol = order['orderLegCollection'][0]['instrument']['symbol']
    
    return order_status, symbol

def replace_long_order(orderid, symbol, quantity, new_price):
    print ('Replacing long order for #' + str(orderid) + ' at ' + str(new_price))

    replace_order = {
        "session": "NORMAL",
        "duration": "GOOD_TILL_CANCEL",
        "orderStrategyType": "SINGLE",
        "orderType": "LIMIT",
        "price": new_price,
        "orderLegCollection": [
        {
            "instruction": "BUY_TO_OPEN",
            "quantity": quantity,
            "instrument": {
            "assetType": "INDEX",
            "symbol": symbol
            }
        }
        ]
    }

    orders_service = td_client.orders()

    response = orders_service.replace_order(
            account_id=account_no,
            order_id=orderid,
            order_dict=replace_order)
    print(response) # should be ID
    
    print('Successfully replaced long order for ' + str(orderid) + ' at ' + str(new_price))

def replace_short_order(orderid, symbol, quantity, new_price):
    print ('Replacing short order for #' + str(orderid) + ' at ' + str(new_price))

    replace_order = {
        "session": "NORMAL",
        "duration": "GOOD_TILL_CANCEL",
        "orderStrategyType": "SINGLE",
        "orderType": "LIMIT",
        "price": new_price,
        "orderLegCollection": [
        {
            "instruction": "SELL_TO_OPEN",
            "quantity": quantity,
            "instrument": {
            "assetType": "INDEX",
            "symbol": symbol
            }
        }
        ]
    }

    orders_service = td_client.orders()

    response = orders_service.replace_order(
            account_id=account_no,
            order_id=orderid,
            order_dict=replace_order)
    print(response) # should be ID
    
    print('Successfully replaced short order for ' + str(orderid) + ' at ' + str(new_price))

def replace_sell_order(orderid, contract_symbol, new_price):
    print ('Replacing sell order for #' + str(orderid) + ', changing price to: ' + str(new_price))

    # market orders must have DAY duration, GOOD_TIL_CANCEL duration is for LIMIT orders
    replace_sell_order = {
        "orderType": "MARKET",
        "session": "NORMAL",
        "duration": "DAY",
        "orderStrategyType": "SINGLE",
        "price": new_price,
        "orderLegCollection": [
            {
            "instrument": {
                "assetType": "OPTION",
                "symbol": contract_symbol
            },
            "instruction": "SELL_TO_CLOSE",
            "quantity": 1
            }
        ]
    }

    orders_service = td_client.orders()

    response = orders_service.replace_order(
            account_id=account_no,
            order_id=orderid,
            order_dict=replace_sell_order)
    print(response) # should be ID
    
    print('Successfully replaced buy order for ' + str(orderid) + ' at ' + str(new_price))


########## ORDER LOG ##########

def log_long_order(symbol):
    timestr = datetime.datetime.now().strftime("%Y_%m_%d")
    #close_time, order_symbol, orderid, instruction, desc, quantity, status, fill_price = view_last_filled_orderid()

    close_time = datetime.datetime.now(set_timezone).time()
    orderid = ""
    instruction = "BUY_TO_OPEN"
    desc = "simulated paper trade"
    quantity = 100
    status = "FILLED"
    fill_price = get_mark(symbol)

    print ('Logging buy order')

    trade = [close_time, fill_price, symbol, orderid, instruction, desc, quantity, status]

    with open(timestr + "_" + symbol + "_share_trade_log.csv", "a", newline='') as log:
        csv_output = writer(log)
        csv_output.writerow(trade)

def log_short_order(symbol):
    timestr = datetime.datetime.now().strftime("%Y_%m_%d")
    #close_time, order_symbol, orderid, instruction, desc, quantity, status, fill_price = view_last_filled_orderid()

    close_time = datetime.datetime.now(set_timezone).time()
    orderid = ""
    desc = "simulated paper trade"
    fill_price = get_mark(symbol)
    instruction = "SELL_TO_OPEN"
    quantity = 100
    status = "FILLED"

    print ('Logging short order')

    trade = [close_time, fill_price, symbol, orderid, instruction, desc, quantity, status]

    with open(timestr + "_" + symbol + "_share_trade_log.csv", "a", newline='') as log:
        csv_output = writer(log)
        csv_output.writerow(trade)

def log_sell_long_order(symbol):
    timestr = datetime.datetime.now().strftime("%Y_%m_%d")
    print ('Logging sell long order')
    log = pd.read_csv(timestr + "_" + symbol + "_share_trade_log.csv")
    last = log.iloc[-1]
    long_price = last['fill_price']
    last_cumulative = last['cumulative_pnl']

    #close_time, order_symbol, orderid, instruction, desc, quantity, status, fill_price = view_last_filled_orderid()

    close_time = datetime.datetime.now(set_timezone).time()
    orderid = ""
    desc = "simulated paper trade"
    fill_price = get_mark(symbol)
    instruction = "SELL_TO_CLOSE"
    quantity = 100
    status = "FILLED"

    pnl = fill_price - long_price
    pnl = round(pnl, 2)
    cumulative = last_cumulative + pnl

    trade = [close_time, fill_price, symbol, orderid, instruction, desc, quantity, status, pnl, cumulative]

    with open(timestr + "_" + symbol + "_share_trade_log.csv", "a", newline='') as log:
        csv_output = writer(log)
        csv_output.writerow(trade)

def log_close_short_order(symbol):
    timestr = datetime.datetime.now().strftime("%Y_%m_%d")
    print ('Logging short close order')
    log = pd.read_csv(timestr + "_" + symbol + "_share_trade_log.csv")
    last = log.iloc[-1]
    short_price = last['fill_price']
    last_cumulative = last['cumulative_pnl']

    #close_time, order_symbol, orderid, instruction, desc, quantity, status, sell_price = view_last_filled_orderid()

    close_time = datetime.datetime.now(set_timezone).time()
    orderid = ""
    desc = "simulated paper trade"
    fill_price = get_mark(symbol)
    instruction = "BUY_TO_CLOSE"
    quantity = 100
    status = "FILLED"

    pnl = short_price - fill_price
    pnl = round(pnl, 2)
    cumulative = last_cumulative + pnl

    trade = [close_time, fill_price, symbol, orderid, instruction, desc, quantity, status, pnl, cumulative]

    with open(timestr + "_" + symbol + "_share_trade_log.csv", "a", newline='') as log:
        csv_output = writer(log)
        csv_output.writerow(trade)


########## ORDER BOT ##########

def T3Long():

    place_long_order()
    
    time.sleep(2) # give it a couple of seconds to fill

    global openorder
    
    orderid, symbol = view_working_orders() # need the orderid to check status

    if orderid is None:
        time.sleep(1)
        close_time, order_symbol, orderid, instruction, desc, quantity, status, price = view_last_filled_orderid() # check if order was filled if it can't get working order

        if status == "FILLED":
            print('Share order for ' + order_symbol + ' was successfully filled for ' + str(quantity))
            openorder = True
            log_long_order()
            return order_symbol, price # order filled, exit
        
        ### Should not reach this level, unless there is a problem/delay. 
        ### If order isn't found in working orders or filled orders then try one more time.
        else:
            time.sleep(1)
            print('Didnt find working order and no filled order yet. Checking again for order id...')
            # try again for working order id
            orderid, symbol = view_working_orders() 
            # if found
            if orderid is not None: 
                print('Order #' + str(orderid) + ' for ' + str(quantity) + ' shares of ' + symbol + ' is still working...')
            # if not found check filled orders one more time
            else: 
                close_time, order_symbol, orderid, instruction, desc, quantity, status, price = view_last_filled_orderid()
                if status == "FILLED":
                    print('Order for ' + order_symbol + ' was successfully filled for ' + str(quantity) + ' shares at ' + str(price))
                    openorder = True
                    log_long_order()
                    return order_symbol, price # order found filled, exit
                else:
                    print('Order was not filled and unable to find working order.')

    if orderid is not None:
        # order is working. Monitor, and raise bid after 5 seconds

        ######## FIRST ORDER LOOP #########
        # this will run one addtional time after replace order loop is broken

        max_checks = 6
        i = 0
        while i < max_checks:
    
            order_status, symbol = get_order_status(orderid) # check order status
            
            if order_status == 'FILLED':
                print('Order for ' + str(quantity) + ' shares of ' + symbol + ' was successfully filled for ' + str(price))
                log_long_order()
                openorder = True
                break

            elif order_status == 'CANCELED': # check for cancellation
                print('Order was cancelled or replaced')
                openorder = False
                break

            else:
                print('Order #' + str(orderid) + ' for ' + str(quantity) + ' shares of '  + symbol + ' is ' + order_status)
                time.sleep(1) # wait 1 second to check again
                i += 1

                # increase bid after 5 seconds
                if i == 5: 
                    print('Raising bid by 0.05')
                    new_price = price + 0.05
                    replace_long_order(orderid, quantity, new_price)

                    orderid, symbol = view_working_orders() # get last working order id, symbol

                    while orderid is None:
                        time.sleep(1)
                        print('Checking for order id...')
                        orderid, symbol = view_working_orders() # try again for working order id
                        if orderid is not None:
                            print('Order #' + str(orderid) + ' for ' + symbol + ' is still working...')
                            break

                        close_time, order_symbol, orderid, instruction, desc, quantity, status, price = view_last_filled_orderid() # check if order was filled if it can't get working order

                        if order_symbol == symbol:
                            print('Order for ' + str(quantity) + ' shares of ' + order_symbol + ' was successfully filled for '  + str(price))
                            log_long_order()
                            openorder = True
                            return order_symbol, price # order filled, exit monitoring loop

                    
                    if orderid is not None:
                    # if order has not yet been filled, monitor and cancel if it takes too long
                      
                        ######## SECOND REPLACE ORDER LOOP #########

                        max_checks = 6
                        i = 0
                        while i < max_checks:
                    
                            order_status, symbol = get_order_status(orderid) # check order status
                            
                            if order_status == 'FILLED':
                                print('Share order for ' + str(quantity) + ' contracts of ' + symbol + ' was successfully filled for ' + str(contract[1]))
                                log_long_order()
                                openorder = True
                                break

                            elif order_status == 'CANCELED':
                                print('Order was cancelled or replaced')
                                break

                            else:
                                print('Order #' + str(orderid) + ' for '  + str(quantity) + ' shares of ' + symbol + ' is ' + order_status)
                                time.sleep(1) # wait 1 second to check again
                                i += 1

                            if i == 5:
                                cancel_order(orderid)
                                break
                        
                       
        else:
            print('Last buy order was cancelled manually or queued order does not match or unable to get working order id.')
            openorder = False


    return price

def T3Short():

    place_short_order()
    
    time.sleep(2) # give it a couple of seconds to fill

    global openorder
    
    orderid, symbol = view_working_orders() # need the orderid to check status

    if orderid is None:
        time.sleep(1)
        close_time, order_symbol, orderid, instruction, desc, quantity, status, price = view_last_filled_orderid() # check if order was filled if it can't get working order

        if status == "FILLED":
            print('Short order for ' + order_symbol + ' was successfully filled for ' + str(quantity))
            openorder = True
            log_short_order()
            return order_symbol, price # order filled, exit
        
        ### Should not reach this level, unless there is a problem/delay. 
        ### If order isn't found in working orders or filled orders then try one more time.
        else:
            time.sleep(1)
            print('Didnt find working order and no filled order yet. Checking again for order id...')
            # try again for working order id
            orderid, symbol = view_working_orders() 
            # if found
            if orderid is not None: 
                print('Order #' + str(orderid) + ' for ' + str(quantity) + ' shares of ' + symbol + ' is still working...')
            # if not found check filled orders one more time
            else: 
                close_time, order_symbol, orderid, instruction, desc, quantity, status, price = view_last_filled_orderid()
                if status == "FILLED":
                    print('Order for ' + order_symbol + ' was successfully filled for ' + str(quantity) + ' shares at ' + str(price))
                    openorder = True
                    log_short_order()
                    return order_symbol, price # order found filled, exit
                else:
                    print('Short order was not filled and unable to find working order.')

    if orderid is not None:
        # order is working. Monitor, and raise bid after 5 seconds

        ######## FIRST ORDER LOOP #########
        # this will run one addtional time after replace order loop is broken

        max_checks = 6
        i = 0
        while i < max_checks:
    
            order_status, symbol = get_order_status(orderid) # check order status
            
            if order_status == 'FILLED':
                print('Short order for ' + str(quantity) + ' shares of ' + symbol + ' was successfully filled for ' + str(price))
                log_short_order()
                openorder = True
                break

            elif order_status == 'CANCELED': # check for cancellation
                print('Short order was cancelled or replaced')
                openorder = False
                break

            else:
                print('Short order #' + str(orderid) + ' for ' + str(quantity) + ' shares of '  + symbol + ' is ' + order_status)
                time.sleep(1) # wait 1 second to check again
                i += 1

                # increase bid after 5 seconds
                if i == 5: 
                    print('Raising bid by 0.05')
                    new_price = price + 0.05
                    replace_short_order(orderid, quantity, new_price)

                    orderid, symbol = view_working_orders() # get last working order id, symbol

                    while orderid is None:
                        time.sleep(1)
                        print('Checking for order id...')
                        orderid, symbol = view_working_orders() # try again for working order id
                        if orderid is not None:
                            print('Order #' + str(orderid) + ' for ' + symbol + ' is still working...')
                            break

                        close_time, order_symbol, orderid, instruction, desc, quantity, status, price = view_last_filled_orderid() # check if order was filled if it can't get working order

                        if order_symbol == symbol:
                            print('Short order for ' + str(quantity) + ' shares of ' + order_symbol + ' was successfully filled for '  + str(price))
                            log_short_order()
                            openorder = True
                            return order_symbol, price # order filled, exit monitoring loop

                    
                    if orderid is not None:
                    # if order has not yet been filled, monitor and cancel if it takes too long
                      
                        ######## SECOND REPLACE ORDER LOOP #########

                        max_checks = 6
                        i = 0
                        while i < max_checks:
                    
                            order_status, symbol = get_order_status(orderid) # check order status
                            
                            if order_status == 'FILLED':
                                print('Option order for ' + str(quantity) + ' contracts of ' + symbol + ' was successfully filled for ' + str(contract[1]))
                                log_short_order()
                                openorder = True
                                break

                            elif order_status == 'CANCELED':
                                print('Order was cancelled or replaced')
                                break

                            else:
                                print('Order #' + str(orderid) + ' for '  + str(quantity) + ' shares of ' + symbol + ' is ' + order_status)
                                time.sleep(1) # wait 1 second to check again
                                i += 1

                            if i == 5:
                                cancel_order(orderid)
                                break
                        
                       
        else:
            print('Last short order was cancelled manually or queued order does not match or unable to get working order id.')
            openorder = False


    return price


########## STOCK DATA PROCESSING ##########

def runT3(data):
    
    open = data['open'] #series
    close = data['close'] #series
    high = data['high'] #series
    low = data['low'] #series

    # check for EOD
    t = data.iloc[-1]
    t = str(t['datetime'])
    t = t[-8:]
    if t == '19:59:00':
        endofday = True
        print('End of day:', endofday)
    else:
        endofday = False
        print('End of day:', endofday)

        
    # Simple Moving Average calcs
    crossdown, crossup, sellcrossup, sellcrossdown = SMA(close)
    data['crossdown'] = crossdown
    data['crossup'] = crossup
    data['sellcrossup'] = sellcrossup
    data['sellcrossdown'] = sellcrossdown

    # SwingHigh, SwingLow bars
    swinglow, swinghigh = swingHighLow(high, low)
    data['swinglow'] = swinglow
    data['swinghigh'] = swinghigh

    # SwingHigh, SwingLow bar within last 10 bars
    swinglow10, swinghigh10 = swing10(swinglow, swinghigh)
    data['swinglow10'] = swinglow10
    data['swinghigh10'] = swinghigh10

    # Swings in last 6 bars
    swinglow6, swinghigh6 = swing6(swinglow, swinghigh)
    data['swinghigh6'] = swinghigh6
    data['swinglow6'] = swinglow6
    
    # NQ 1m bull or bear
    NQbull, NQbear = NQ_scalp(open, close, high, low)
    data['NQbull'] = NQbull
    data['NQbear'] = NQbear

    # Top reversal candles
    topreverse = reversal_top(open, close, low)
    topreverse2 = reversal_top2(open, close, swinghigh)
    topreverse3 = reversal_top3(open, close)
    topreverse4 = reversal_top4(close, high, low, swinghigh)
    data['reversal_top'] = topreverse
    data['reversal_top2'] = topreverse2 # for bear trends
    data['reversal_top3'] = topreverse3
    data['reversal_top4'] = topreverse4 # for bear trends

    # Bullcross/Bearcross
    bullcross, bearcross = bbcross(crossup, crossdown)
    data['bullcross'] = bullcross
    data['bearcross'] = bearcross

    # Pop/Drop
    p = pop(open, close, high)
    d = drop(open, close)
    data['pop'] = p
    data['drop'] = d

    # Sell signals
    long_close = p | sellcrossdown | topreverse | topreverse3 | endofday
    data['long_close'] = long_close
    short_close = p | d | sellcrossup | endofday
    data['short_close'] = short_close

    # T3 signal
    T3bull = swinglow10 & NQbull & bullcross
    T3bear = swinghigh10 & NQbear & bearcross
    data['T3 Bull Signal'] = T3bull
    data['T3 Bear Signal'] = T3bear

    return data

symbol = symbol1 # temporary, set conditions for which symbols to create outputs for here 

print('Updating ' + symbol + ' output file')
headers = ['datetime', 'open', 'high', 'low', 'close']
with open(symbol + '_output.csv', 'w') as f_output:
    csv_output = csv.DictWriter(f_output, fieldnames=headers)
    csv_output.writeheader() 

# get historical 1-minute prices  
t = time.time()
t_ms = int(t * 1000)
t_ms = t_ms + 85000000 # use future date
price_history_service = td_client.price_history()
history = price_history_service.get_price_history(symbol, end_date=t_ms, extended_hours_needed=True, period_type='day', period=1, frequency_type='minute', frequency=1)
history = history['candles']
history = pd.DataFrame(history)
history['datetime'] = pd.to_datetime(history['datetime'],unit='ms')
history = history[['datetime','open','high','low','close']]
# drop last two rows so they don't repeat when stream starts
history.drop(history.tail(2).index,
        inplace = True)

# initial signal calculation
signals = runT3(history)
signals.to_csv(symbol + '_output.csv', index=False)

print('Loading ' + symbol + ' data stream')

# Initialize the `StreamingApiClient` service.
streaming_api_service = td_client.streaming_api_client()

streaming_services = streaming_api_service.services()

# Stream equity bars
streaming_services.chart(
    service=ChartServices.ChartEquity,
    symbols=[symbol],
    fields=ChartEquity.All
)

async def data_pipeline():
  
    await streaming_api_service.build_pipeline()

    global openorder
    openorder = False

    symbol = symbol1

    while True:
        print("Running pipline loop")
        # Start the Pipeline.
        data = await streaming_api_service.start_pipeline()
        
        # Grab the Data, if there was any. Not every message will have `data.`
        if data and 'data' in data:

            print('-='*40)

            data_content = data['data'][0]['content']
            print("Data content:", data_content)

            if 'key' in data_content[0]:
                print('Data for symbol: {}'.format(data_content[0]['key']))

                # 1-open 2-high 3-low 4-close, 5-volume, 7-epoch time
                t = pd.to_datetime(data_content[0]['7'], unit='ms')
                open_price = data_content[0]['1']
                high = data_content[0]['2']
                low = data_content[0]['3']
                close = data_content[0]['4']
                row = [t, open_price, high, low, close]

                print('Time:', t)
                print('Open:', open_price)
                print('High:', high)
                print('Low:', low)
                print('Close:', close)

                print('-='*40)

                with open(symbol + "_output.csv", "a", newline='') as f_output:
                    csv_output = writer(f_output)
                    csv_output.writerow(row)
                
                print('Performing signal calculations')
                signals = pd.read_csv(symbol + '_output.csv')
                signals = runT3(signals)
                signals.to_csv(symbol + '_output.csv', index=False)

                t3_bull_signal = signals.iloc[-1]['T3 Bull Signal']
                t3_bear_signal = signals.iloc[-1]['T3 Bear Signal']

                long_sell_signal = signals.iloc[-1]['long_close']
                short_close_signal = signals.iloc[-1]['short_close']

                print('T3 Bull:', t3_bull_signal)
                print('T3 Bear:', t3_bear_signal)
                print('Long close:', long_sell_signal)
                print('Short close:', short_close_signal)
                print('Open order:', openorder)

                # Place orders on T3 signals

                if t3_bear_signal:
                    # check there are no open orders already
                    if openorder == False:
                        #buy_result = T3Short()
                        order_result = log_short_order()
                        print(order_result)
                        openorder = True                       

                    else:
                        print('T3 Bear order was not placed because there is already an open order') 
                          
                    
                elif t3_bull_signal:
                    # check there are no open orders already
                    if openorder == False:
                        #buy_result = T3Long()
                        order_result = log_long_order()
                        print(order_result)
                        openorder = True

                    else:
                        print('T3 Bull order was not placed because there is already an open order')
              
                               
                # Close opened positions on sell signals
                elif openorder:
                    
                    if long_sell_signal:
                        
                        #symbol = order_result[0]
                        #place_close_short_order(symbol)
                        log_sell_long_order(symbol)
                        openorder = False

                    elif short_close_signal:
                        
                        #symbol = order_result[0]
                        #place_close_long_order(symbol)
                        log_close_short_order(symbol)
                        openorder = False

                    else:
                        print('An order is open, but no sell signals.')

                    
                
        elif data and 'notify' in data:
            print(data['notify'][0])
        
        else:
            print('No data...lost connection to stream.')

print('Starting ' + symbol + ' data stream')
asyncio.run(data_pipeline())