# T3 Trader Bot
# v1.0

'''NQBear and NQbull signals require 50 historical bars. 
Start script 40 minutes before open to include PM data.
No buy signals will then be possible for the first 10 minutes.'''

from datetime import datetime
import datetime
import time
import asyncio
import pandas as pd
import csv
from csv import writer
import os.path
from configparser import ConfigParser
from td.client import TdAmeritradeClient
from td.credentials import TdCredentials
from td.utils.enums import OptionType
from td.utils.enums import ContractType
from td.utils.option_chain import OptionChainQuery
from td.utils.enums import OrderStatus
from td.utils.enums import ChartServices
from td.utils.enums import ChartEquity
import talib as ta

weekdays = {1: "Monday",
            2: "Tuesday",
            3: "Wednesday",
            4: "Thursday",
            5: "Friday",
            6: "Saturday",
            7: "Sunday"}
            
day = datetime.date.today().isoweekday()

print("Today is", weekdays[day])

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
openorder = False

# check for existing trade log file
timestr = datetime.datetime.now().strftime("%Y_%m_%d")
if os.path.exists(timestr + "_trade_log.csv"):
    print('Trade log file already exists')
else:
    print('Creating new trade log file')
    headers = ['datetime', 'share_price', 'symbol', 'orderid', 'instruction',
               'desc', 'quantity', 'status', 'price', 'trade P/L', 'share P/L']
    with open(timestr + "_trade_log.csv", "w", newline='') as log:
        csv_output = csv.DictWriter(log, fieldnames=headers)
        csv_output.writeheader()

print('Loading signal functions')
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

print('Loading option order functions')
def build_0dte_order(option):
    # build the order
    today = datetime.date.today()

    # get 1 strike above and 1 below
    options_chain_service = td_client.options_chain()

    option_chain_query = OptionChainQuery(
        symbol='QQQ',
        contract_type=ContractType.All,
        from_date=today,
        to_date=today,
        strike_count='2',
        option_type=OptionType.StandardContracts
    )
    chain = options_chain_service.get_option_chain(option_chain_query=option_chain_query)
    status = chain['status']
    if status == 'FAILED':
        print('Failed. Chain does not exist.')
        return
    else:
        print('Retrieved current chain.')

    if option == 'long' :
        print('Building 0dte long order...')
        call_map = chain['callExpDateMap']
        last_prices = [i['last'] for d in call_map.values() for v in d.values() for i in v]
        call_map = [i['symbol'] for d in call_map.values() for v in d.values() for i in v]
        call = call_map[0]
        mark = last_prices[0]
        print('ITM Call:', call)
        print("Last price:", mark)
        return call, mark
    else :
        print('Building 0dte short order...')
        put_map = chain['putExpDateMap']
        put_map = chain['putExpDateMap']
        last_prices = [i["last"] for d in put_map.values() for v in d.values() for i in v]
        put_map = [i['symbol'] for d in put_map.values() for v in d.values() for i in v]
        put = put_map[-1]
        mark = last_prices[-1]
        print('ITM Put:', put)
        print("Last price:", mark)
        return put, mark

def build_1dte_order(option):
    today = datetime.date.today()
    tommorrow = today + datetime.timedelta(days=1)

    # get 1 strike above and 1 below, does not base on PM price
    options_chain_service = td_client.options_chain()

    option_chain_query = OptionChainQuery(
        symbol='QQQ',
        contract_type=ContractType.All,
        from_date=tommorrow,
        to_date=tommorrow,
        strike_count='2',
        option_type=OptionType.StandardContracts
    )
 
    chain = options_chain_service.get_option_chain(option_chain_query=option_chain_query)
    status = chain['status']
    if status == 'FAILED':
        print('Failed. Chain does not exist.')
        return
    else:
        print('Retrieved current chain.')

    if option == 'long' :
        print('Building 1dte long order...')
        call_map = chain['callExpDateMap']
        last_prices = [i['last'] for d in call_map.values() for v in d.values() for i in v]
        call_map = [i['symbol'] for d in call_map.values() for v in d.values() for i in v]
        call = call_map[0]
        mark = last_prices[0]
        print('ITM Call:', call)
        print("Last price:", mark)
        return call, mark
    else :
        print('Building 1dte short order...')
        put_map = chain['putExpDateMap']
        last_prices = [i["last"] for d in put_map.values() for v in d.values() for i in v]
        put_map = [i['symbol'] for d in put_map.values() for v in d.values() for i in v]
        put = put_map[-1]
        mark = last_prices[-1]
        print('ITM Put:', put)
        print("Last price:", mark)
        return put, mark
# real price
def place_option_order(contract, quantity):
    contract_symbol = contract[0]
    contract_price = contract[1]
    print ('Placing order for ' + contract_symbol + ' at ' + str(contract_price))

    single_option_order = {
        "session": "NORMAL",
        "duration": "GOOD_TILL_CANCEL",
        "orderStrategyType": "SINGLE",
        "orderType": "LIMIT",
        "price": contract_price,
        #"price": 0.10,
        "orderLegCollection": [
        {
            "instruction": "BUY_TO_OPEN",
            "quantity": quantity, 
            "instrument": {
            "assetType": "OPTION",
            "symbol": contract_symbol
            }
        }
        ]
    }

    orders_service = td_client.orders()

    response = orders_service.place_order(account_id=account_no, order_dict=single_option_order)
    print(response) # should be ID
    print('Successfully placed order for ' + contract_symbol + ' at ' + str(contract_price))

# replace market order not used
def replace_market_order(orderid, contract_symbol, quantity, bidprice):
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

def place_sell_order(contract_symbol, quantity):
    
    lastprice, bidprice = get_option_mark(contract_symbol)

    sell_order = {
        "orderType": "LIMIT",
        "session": "NORMAL",
        "duration": "GOOD_TILL_CANCEL",
        "orderStrategyType": "SINGLE",
        "price": lastprice,
        "orderLegCollection": [
            {
            "instrument": {
                "assetType": "OPTION",
                "symbol": contract_symbol
            },
            "instruction": "SELL_TO_CLOSE",
            "quantity": quantity
            }
        ]
    }
    orders_service = td_client.orders()
    print('Trying to place order for ', contract_symbol)
    response = orders_service.place_order(account_id=account_no, order_dict=sell_order)
    print(response) # should be ID
    print('Successfully placed sell order for ' + contract_symbol + ' at ' + str(lastprice))

    # get sell order id, check
    time.sleep(1) # give it a second to fill
    orderid, symbol = view_working_orders()
    global openorder

    while orderid is None:
        time.sleep(1)
        print('Checking for order id...')
        orderid, symbol = view_working_orders() # try again for working order id
        if orderid is not None:
            print('Order #' + str(orderid) + ' for ' + symbol + ' is still working...')
            break

        close_time, symbol2, orderid, instruction, desc, quantity, status, price = view_last_filled_orderid() # check if order was filled if it can't get working order

        if symbol2 == contract_symbol:
            print('Option order for ' + symbol2 + ' was successfully filled for ' + str(contract_symbol))
            openorder = False
            log_sell_order()
            return symbol2, price # order filled, exit monitoring loop

    if orderid is not None:
        # if sell order has not yet been filled, monitor, and set to bid after 5 seconds
    
        if symbol == contract_symbol: # check that it is the same order just placed

            ######## FIRST ORDER LOOP #########
            # this will run one addtional time after replace order loop is broken

            max_checks = 6
            i = 0
            while i < max_checks:
        
                order_status, symbol = get_order_status(orderid) # check order status
                
                if order_status == 'FILLED':
                    print('Option order for ' + symbol + ' was successfully filled for ' + str(contract_symbol))
                    openorder = False
                    log_sell_order()
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
                        lastprice, bidprice = get_option_mark(contract_symbol)
                        replace_sell_order(orderid, contract_symbol, bidprice)
                        
                        orderid, symbol = view_working_orders() # get last working order id, symbol

                        while orderid is None:
                            time.sleep(1)
                            print('Checking for order id...')
                            orderid, symbol = view_working_orders() # try again for working order id
                            if orderid is not None:
                                print('Order #' + str(orderid) + ' for ' + symbol + ' is still working...')
                                break

                            close_time, symbol2, orderid, instruction, desc, quantity, status, price = view_last_filled_orderid() # check if order was filled if it can't get working order

                            if symbol2 == contract_symbol:
                                print('Option order for ' + symbol2 + ' was successfully filled for ' + str(price))
                                openorder = False
                                log_sell_order()
                                return symbol2, price # order filled, exit monitoring loop

                        
                        if orderid is not None:
                        # if order has not yet been filled, monitor and set to bid again
                    
                            if symbol == contract_symbol: # check that it is the same order just placed
                                
                                ######## SECOND REPLACE ORDER LOOP #########

                                max_checks = 6
                                i = 0
                                while i < max_checks:
                            
                                    order_status, symbol = get_order_status(orderid) # check order status
                                    
                                    if order_status == 'FILLED':
                                        print('Option order for ' + symbol + ' was successfully filled for ' + str(contract_symbol))
                                        openorder = False
                                        log_sell_order()
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
            print('Last sell order was cancelled manually or queued order does not match')
            openorder = False
            log_sell_order()

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
            symbol2 = orders[1]['orderLegCollection'][0]['instrument']['symbol']
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
            symbol2 = orders[1]['orderLegCollection'][0]['instrument']['symbol']
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

def get_option_mark(contract):
  quote_service = td_client.quotes()

  quote = quote_service.get_quotes(instruments=[contract])

  lastprice = quote[contract]['lastPrice']
  bidprice = quote[contract]['bidPrice']
  
  print(contract + ' last: ' + str(lastprice) + ', bid: ' + str(bidprice))
  return lastprice, bidprice

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
# real price
def replace_order(orderid, contract_symbol, quantity, new_price):
    print ('Replacing order for #' + str(orderid) + ' at ' + str(new_price))

    replace_option_order = {
        "session": "NORMAL",
        "duration": "GOOD_TILL_CANCEL",
        "orderStrategyType": "SINGLE",
        "orderType": "LIMIT",
        "price": new_price,
        #"price": 0.15,
        "orderLegCollection": [
        {
            "instruction": "BUY_TO_OPEN",
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
    
    print('Successfully replaced buy order for ' + str(orderid) + ' at ' + str(new_price))

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

def log_buy_order():
    timestr = datetime.datetime.now().strftime("%Y_%m_%d")
    close_time, symbol2, orderid, instruction, desc, quantity, status, price = view_last_filled_orderid()
    print ('Logging buy order')
    output = pd.read_csv('QQQ_output.csv')
    last = output.iloc[-1]
    shareprice = last['close']
    
    trade = [close_time, shareprice, symbol2, orderid, instruction, desc, quantity, status, price]

    with open(timestr + "_trade_log.csv", "a", newline='') as log:
        csv_output = writer(log)
        csv_output.writerow(trade)

def log_sell_order():
    timestr = datetime.datetime.now().strftime("%Y_%m_%d")
    print ('Logging sell order')
    log = pd.read_csv(timestr + '_trade_log.csv')
    last = log.iloc[-1]
    sharebuyprice = last['share_price']
    buyprice = last['price']
    output = pd.read_csv('QQQ_output.csv')
    last = output.iloc[-1]
    shareprice = last['open']
    spnl = shareprice - sharebuyprice

    close_time, symbol2, orderid, instruction, desc, quantity, status, price = view_last_filled_orderid()

    pnl = price - buyprice
    pnl = round(pnl, 2)
    trade = [close_time, shareprice, symbol2, orderid, instruction, desc, quantity, status, price, pnl, spnl]

    with open(timestr + "_trade_log.csv", "a", newline='') as log:
        csv_output = writer(log)
        csv_output.writerow(trade)

# Option buy order scheme


def T3Buy(side, quantity):

    if day in [1,3,5]:
        contract = build_0dte_order(side)
        place_option_order(contract, quantity)

    else: 
        day in [2,4]
        contract = build_1dte_order(side)
        place_option_order(contract, quantity)
    
    time.sleep(2) # give it a couple of seconds to fill

    global openorder
    
    orderid, symbol = view_working_orders() # need the orderid to check status

    if orderid is None:
        time.sleep(1)
        close_time, symbol2, orderid, instruction, desc, quantity, status, price = view_last_filled_orderid() # check if order was filled if it can't get working order

        if symbol2 == contract[0]:
            print('Option order for ' + symbol2 + ' was successfully filled for ' + str(quantity) + ' contracts for ' + str(price))
            openorder = True
            log_buy_order()
            return symbol2, price # order filled, exit
        
        ### Should not reach this level, unless there is a problem/delay. 
        ### If order isn't found in working orders or filled orders then try one more time.
        else:
            time.sleep(1)
            print('Didnt find working order and no filled order yet. Checking again for order id...')
            # try again for working order id
            orderid, symbol = view_working_orders() 
            # if found
            if orderid is not None: 
                print('Order #' + str(orderid) + ' for ' + str(quantity) + ' contracts of ' + symbol + ' is still working...')
            # if not found check filled orders one more time
            else: 
                close_time, symbol2, orderid, instruction, desc, quantity, status, price = view_last_filled_orderid()
                if symbol2 == contract[0]:
                    print('Option order for ' + symbol2 + ' was successfully filled for ' + str(quantity) + ' contracts for ' + str(price))
                    openorder = True
                    log_buy_order()
                    return symbol2, price # order found filled, exit
                else:
                    print('Order was not filled and unable to find working order.')

    if orderid is not None:
        # order is working. Monitor, and raise bid after 5 seconds
    
        if symbol == contract[0]: # check that it is the same order just placed

            ######## FIRST ORDER LOOP #########
            # this will run one addtional time after replace order loop is broken

            max_checks = 6
            i = 0
            while i < max_checks:
        
                order_status, symbol = get_order_status(orderid) # check order status
                
                if order_status == 'FILLED':
                    print('Option order for ' + str(quantity) + ' contracts of ' + symbol + ' was successfully filled for ' + str(contract[1]))
                    log_buy_order()
                    openorder = True
                    break

                elif order_status == 'CANCELED': # check for cancellation
                    print('Order was cancelled or replaced')
                    openorder = False
                    break

                else:
                    print('Order #' + str(orderid) + ' for ' + str(quantity) + ' contracts of '  + symbol + ' is ' + order_status)
                    time.sleep(1) # wait 1 second to check again
                    i += 1

                    # increase bid after 5 seconds
                    if i == 5: 
                        print('Raising bid by 0.05')
                        new_price = contract[1] + 0.05
                        replace_order(orderid, contract[0], quantity, new_price)

                        orderid, symbol = view_working_orders() # get last working order id, symbol

                        while orderid is None:
                            time.sleep(1)
                            print('Checking for order id...')
                            orderid, symbol = view_working_orders() # try again for working order id
                            if orderid is not None:
                                print('Order #' + str(orderid) + ' for ' + symbol + ' is still working...')
                                break

                            close_time, symbol2, orderid, instruction, desc, quantity, status, price = view_last_filled_orderid() # check if order was filled if it can't get working order

                            if symbol2 == contract[0]:
                                print('Option order for ' + str(quantity) + ' contracts of ' + symbol2 + ' was successfully filled for '  + str(price))
                                log_buy_order()
                                openorder = True
                                return symbol2, price # order filled, exit monitoring loop

                        
                        if orderid is not None:
                        # if order has not yet been filled, monitor and cancel if it takes too long
                    
                            if symbol == contract[0]: # check that it is the same order just placed
                                
                                ######## SECOND REPLACE ORDER LOOP #########

                                max_checks = 6
                                i = 0
                                while i < max_checks:
                            
                                    order_status, symbol = get_order_status(orderid) # check order status
                                    
                                    if order_status == 'FILLED':
                                        print('Option order for ' + str(quantity) + ' contracts of ' + symbol + ' was successfully filled for ' + str(contract[1]))
                                        log_buy_order()
                                        openorder = True
                                        break

                                    elif order_status == 'CANCELED':
                                        print('Order was cancelled or replaced')
                                        break

                                    else:
                                        print('Order #' + str(orderid) + ' for '  + str(quantity) + ' contracts of ' + symbol + ' is ' + order_status)
                                        time.sleep(1) # wait 1 second to check again
                                        i += 1

                                    if i == 5:
                                        cancel_order(orderid)
                                        break
                            
                       
        else:
            print('Last buy order was cancelled manually or queued order does not match or unable to get working order id.')
            openorder = False


    return contract


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


print('Updating QQQ output file')
headers = ['datetime', 'open', 'high', 'low', 'close']
with open('QQQ_output.csv', 'w') as f_output:
    csv_output = csv.DictWriter(f_output, fieldnames=headers)
    csv_output.writeheader() 

# get historical 1-minute prices  
t = time.time()
t_ms = int(t * 1000)
t_ms = t_ms + 85000000 # use future date
price_history_service = td_client.price_history()
history = price_history_service.get_price_history('QQQ', end_date=t_ms, extended_hours_needed=True, period_type='day', period=1, frequency_type='minute', frequency=1)
history = history['candles']
history = pd.DataFrame(history)
history['datetime'] = pd.to_datetime(history['datetime'],unit='ms')
history = history[['datetime','open','high','low','close']]
# drop last two rows so they don't repeat when stream starts
history.drop(history.tail(2).index,
        inplace = True)

# initial signal calculation
signals = runT3(history)
signals.to_csv('QQQ_output.csv', index=False)

print('Loading QQQ data stream')

# Initialize the `StreamingApiClient` service.
streaming_api_service = td_client.streaming_api_client()

streaming_services = streaming_api_service.services()

# Stream equity bars
streaming_services.chart(
    service=ChartServices.ChartEquity,
    symbols=['QQQ'],
    fields=ChartEquity.All
)


async def data_pipeline():
  
    await streaming_api_service.build_pipeline()

    global openorder
    openorder = False

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

                with open("QQQ_output.csv", "a", newline='') as f_output:
                    csv_output = writer(f_output)
                    csv_output.writerow(row)
                
                print('Performing signal calculations')
                signals = pd.read_csv('QQQ_output.csv')
                signals = runT3(signals)
                signals.to_csv('QQQ_output.csv', index=False)

                t3_bull_signal = signals.iloc[-1]['T3 Bull Signal']
                t3_bear_signal = signals.iloc[-1]['T3 Bear Signal']

                long_sell_signal = signals.iloc[-1]['long_close']
                short_sell_signal = signals.iloc[-1]['short_close']

                print('T3 Bull:', t3_bull_signal)
                print('T3 Bear:', t3_bear_signal)
                print('Long close:', long_sell_signal)
                print('Short close:', short_sell_signal)
                print('Open order:', openorder)

                # Buy options on T3 signals
                # set number of contracts
                quantity = 1

                if t3_bear_signal:
                    # check there are no open orders already
                    if openorder == False:
                        buy_result = T3Buy('short', quantity)
                        print(buy_result)
                        openorder = True                       

                    else:
                        print('T3 Bear order was not placed because there is already an open order') 
                          
                    
                elif t3_bull_signal:
                    # check there are no open orders already
                    if openorder == False:
                        buy_result = T3Buy('long', quantity)
                        print(buy_result)
                        openorder = True

                    else:
                        print('T3 Bull order was not placed because there is already an open order')
              
                               
                # Sell opened options on sell signals
                elif openorder:
                    
                    if long_sell_signal:
                        
                        symbol = buy_result[0]
                        place_sell_order(symbol, quantity)
                        openorder = False

                    elif short_sell_signal:
                        
                        symbol = buy_result[0]
                        place_sell_order(symbol, quantity)
                        openorder = False

                    else:
                        print('An order is open, but no sell signals.')

                    
                
        elif data and 'notify' in data:
            print(data['notify'][0])
        
        else:
            print('No data...lost connection to stream.')

print('Starting QQQ data stream')
asyncio.run(data_pipeline())