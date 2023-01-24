# Options Quickdraw
# v1.1


import asyncio
import csv
import datetime
import os.path
import time

from configparser import ConfigParser
from csv import writer
from datetime import datetime
import datetime
import pandas as pd


from td.client import TdAmeritradeClient
from td.credentials import TdCredentials
from td.utils.enums import (ChartEquity, ChartServices, ContractType,
                            OptionType, OrderStatus)
from td.utils.option_chain import OptionChainQuery

import aiotkinter
import tkinter as tk
from tkinter import *
from tkinter import messagebox
#from tkinter import ttk
from tkinter.ttk import *

open_position = False

weekdays = {1: "Monday",
            2: "Tuesday",
            3: "Wednesday",
            4: "Thursday",
            5: "Friday",
            6: "Saturday",
            7: "Sunday"}

day = datetime.date.today().isoweekday()

optiondate = weekdays[day]

print("Today is", weekdays[day])

config = ConfigParser()
config.read('config/config.ini')
client_id = config.get('main', 'client_id')
redirect_uri = config.get('main', 'redirect_uri')
account_no = config.get('main', 'account_number')

symb = 'QQQ'

# check for existing trade log
timestr = datetime.datetime.now().strftime("%Y_%m_%d")

if os.path.exists('logs/' + timestr + "_3dte_quickdraw_log.csv"):
    print('Trade log file already exists')
else:
    print('Creating new quickdraw log file')
    headers = ['datetime', 'share_price', 'symbol', 'orderid', 'instruction',
               'desc', 'quantity', 'status', 'price', 'trade P/L', 'share P/L']
    with open('logs/' + timestr + "_quickdraw_log.csv", "w", newline='') as log:
        csv_output = csv.DictWriter(log, fieldnames=headers)
        csv_output.writeheader()

print('Loading option order functions')

# builds only for indexes with daily options, not equities
def build_3dte_order(option, status):
    # build the order
    day = datetime.date.today().isoweekday()
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)



    if optiondate == weekdays[day]:
        dte = today
    else:
        if optiondate == "Monday":
            if weekdays[day] == "Tuesday":
                dte = today + datetime.timedelta(days=6)
            if weekdays[day] == "Wednesday":
                dte = today + datetime.timedelta(days=5)
            if weekdays[day] == "Thursday":
                dte = today + datetime.timedelta(days=4)
            if weekdays[day] == "Friday":
                dte = today + datetime.timedelta(days=3)
        if optiondate == "Tuesday":
            if weekdays[day] == "Monday":
                dte = today + datetime.timedelta(days=1)
            if weekdays[day] == "Wednesday":
                dte = today + datetime.timedelta(days=6)
            if weekdays[day] == "Thursday":
                dte = today + datetime.timedelta(days=5)
            if weekdays[day] == "Friday":
                dte = today + datetime.timedelta(days=4)
        if optiondate == "Wednesday":
            if weekdays[day] == "Monday":
                dte = today + datetime.timedelta(days=2)
            if weekdays[day] == "Tuesday":
                dte = today + datetime.timedelta(days=1)
            if weekdays[day] == "Thursday":
                dte = today + datetime.timedelta(days=6)
            if weekdays[day] == "Friday":
                dte = today + datetime.timedelta(days=5)
        if optiondate == "Thursday":
            if weekdays[day] == "Monday":
                dte = today + datetime.timedelta(days=3)
            if weekdays[day] == "Tuesday":
                dte = today + datetime.timedelta(days=2)
            if weekdays[day] == "Wednesday":
                dte = today + datetime.timedelta(days=1)
            if weekdays[day] == "Friday":
                dte = today + datetime.timedelta(days=6)
        if optiondate == "Friday":
            if weekdays[day] == "Monday":
                dte = today + datetime.timedelta(days=4)
            if weekdays[day] == "Tuesday":
                dte = today + datetime.timedelta(days=3)
            if weekdays[day] == "Wednesday":
                dte = today + datetime.timedelta(days=2)
            if weekdays[day] == "Thursday":
                dte = today + datetime.timedelta(days=1)


    # get 1 strike above and 1 below
    options_chain_service = td_client.options_chain()

    option_chain_query = OptionChainQuery(
        symbol=symb,
        contract_type=ContractType.All,
        from_date=dte,
        to_date=dte,
        strike_count='2',
        option_type=OptionType.StandardContracts
    )
    print('Retrieving chain for ' + symb)
    chain = options_chain_service.get_option_chain(
        option_chain_query=option_chain_query)
    chain_status = chain['status']
    if chain_status == 'FAILED':
        print('Failed. Chain does not exist.')
        status.config(text = 'Chain does not exist for Monday. Trying Friday.')
        
        print('Retrieving tomorrows chain for ' + symb)
        option_chain_query = OptionChainQuery(
            symbol=symb,
            contract_type=ContractType.All,
            from_date=tomorrow,
            to_date=tomorrow,
            strike_count='2',
            option_type=OptionType.StandardContracts
        )
        chain = options_chain_service.get_option_chain(
        option_chain_query=option_chain_query)
        chain_status = chain['status']
        if chain_status == 'FAILED':
            print('Failed. Chain does not exist for Friday either.')
            return
    else:
        print('Retrieved current chain.')

    if option == 'long':
        print('Building 3dte long order...')
        call_map = chain['callExpDateMap']
        last_prices = [i['last'] for d in call_map.values()
                       for v in d.values() for i in v]
        call_map = [i['symbol'] for d in call_map.values()
                    for v in d.values() for i in v]
        call = call_map[0]
        mark = last_prices[0]
        print('ITM Call:', call)
        print("Last price:", mark)
        return call, mark
    else:
        print('Building 3dte short order...')
        put_map = chain['putExpDateMap']
        put_map = chain['putExpDateMap']
        last_prices = [i["last"] for d in put_map.values()
                       for v in d.values() for i in v]
        put_map = [i['symbol'] for d in put_map.values()
                   for v in d.values() for i in v]
        put = put_map[-1]
        mark = last_prices[-1]
        print('ITM Put:', put)
        print("Last price:", mark)
        return put, mark


def place_option_order(contract, quantity, status):
    contract_symbol = contract[0]

    lastprice, bidprice, askprice = get_option_mark(contract_symbol)

    contract_price = askprice

    print('Placing order for ' + contract_symbol + ' at ' + str(contract_price))

    single_option_order = {
        "session": "NORMAL",
        "duration": "GOOD_TILL_CANCEL",
        "orderStrategyType": "SINGLE",
        "orderType": "LIMIT",
        "price": contract_price,
        # "price": 0.10,
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

    response = orders_service.place_order(
        account_id=account_no, order_dict=single_option_order)
    print(response)  # should be ID
    print('Successfully placed order for ' +
          contract_symbol + ' at ' + str(contract_price))

    log_quickdraw_buy_order()

def place_sell_order(contract_symbol, quantity, status):

    lastprice, bidprice, askprice = get_option_mark(contract_symbol)
    global open_position

    sell_order = {
        "orderType": "LIMIT",
        "session": "NORMAL",
        "duration": "GOOD_TILL_CANCEL",
        "orderStrategyType": "SINGLE",
        "price": bidprice,
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
    response = orders_service.place_order(
        account_id=account_no, order_dict=sell_order)
    print(response)  # should be ID
    print('Successfully placed sell order for ' +
          contract_symbol + ' at ' + str(lastprice))
    open_position = False
    log_quickdraw_sell_order()
    status.config(text = 'Closed ' + str(quantity) + ' options >> ' + contract_symbol)


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
            print('There are at least three working orders:')

            quantity = orders[0]['quantity']
            filledquantity = orders[0]['filledQuantity']
            remainingquantity = orders[0]['remainingQuantity']
            symbol1 = orders[0]['orderLegCollection'][0]['instrument']['symbol']
            description = orders[0]['orderLegCollection'][0]['instrument']['description']
            order_id = orders[0]['orderId']
            print('Working order: ' + str(order_id) + ', ' + description +
                  ', Quantity: ' + str(quantity) + ', Filled: ' + str(filledquantity))

            quantity = orders[1]['quantity']
            filledquantity = orders[1]['filledQuantity']
            remainingquantity = orders[1]['remainingQuantity']
            symbol2 = orders[1]['orderLegCollection'][0]['instrument']['symbol']
            description = orders[1]['orderLegCollection'][0]['instrument']['description']
            order_id2 = orders[1]['orderId']
            print('Working order: ' + str(order_id2) + ', ' + description +
                  ', Quantity: ' + str(quantity) + ', Filled: ' + str(filledquantity))

            quantity = orders[2]['quantity']
            filledquantity = orders[2]['filledQuantity']
            remainingquantity = orders[2]['remainingQuantity']
            symbol3 = orders[2]['orderLegCollection'][0]['instrument']['symbol']
            description = orders[2]['orderLegCollection'][0]['instrument']['description']
            order_id3 = orders[2]['orderId']
            print('Working order: ' + str(order_id3) + ', ' + description +
                  ', Quantity: ' + str(quantity) + ', Filled: ' + str(filledquantity))
            return order_id, symbol1

        elif len(orders) > 1:
            print('There are two working orders:')

            quantity = orders[0]['quantity']
            filledquantity = orders[0]['filledQuantity']
            remainingquantity = orders[0]['remainingQuantity']
            symbol1 = orders[0]['orderLegCollection'][0]['instrument']['symbol']
            description = orders[0]['orderLegCollection'][0]['instrument']['description']
            order_id = orders[0]['orderId']
            print('Working order: ' + str(order_id) + ', ' + description +
                  ', Quantity: ' + str(quantity) + ', Filled: ' + str(filledquantity))

            quantity = orders[1]['quantity']
            filledquantity = orders[1]['filledQuantity']
            remainingquantity = orders[1]['remainingQuantity']
            symbol2 = orders[1]['orderLegCollection'][0]['instrument']['symbol']
            description = orders[1]['orderLegCollection'][0]['instrument']['description']
            order_id2 = orders[1]['orderId']
            print('Working order: ' + str(order_id2) + ', ' + description +
                  ', Quantity: ' + str(quantity) + ', Filled: ' + str(filledquantity))
            return order_id, symbol1

        else:
            print('There is one working order:')
            quantity = orders[0]['quantity']
            filledquantity = orders[0]['filledQuantity']
            remainingquantity = orders[0]['remainingQuantity']
            symbol = orders[0]['orderLegCollection'][0]['instrument']['symbol']
            description = orders[0]['orderLegCollection'][0]['instrument']['description']
            order_id = orders[0]['orderId']
            print('Working order: ' + str(order_id) + ', ' + description +
                  ', Quantity: ' + str(quantity) + ', Filled: ' + str(filledquantity))
            return order_id, symbol

    else:
        print('No working orders.')
        return None, None


def view_last_filled_orderid():
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
        print('Last Filled Order: #' + str(orderid) + ', ' + instruction + ' ' +
              desc + ', ' + str(quantity) + ' ' + status + ' for ' + str(price))
        return close_time, symbol, orderid, instruction, desc, quantity, status, price

    else:
        print('No filled orders today')
        return None, None, None, None, None, None, None, None


def get_option_mark(contract):
    quote_service = td_client.quotes()

    quote = quote_service.get_quotes(instruments=[contract])

    lastprice = quote[contract]['lastPrice']
    bidprice = quote[contract]['bidPrice']
    askprice = quote[contract]['askPrice']

    print("Option quote >> " + contract + ' last: ' + str(lastprice) + ', bid: ' + str(bidprice) + 'ask: ' + str(askprice))
    return lastprice, bidprice, askprice

def cancel_quickdraw_order(status, button):
    button.config(state="disabled")
    # Cancel order
    orderid, symbol = view_working_orders()
    order_status = ''
    print("Canceling order id: ", str(orderid))
    while order_status != 'CANCELED':

        orders_service = td_client.orders()
        orders_service.cancel_order(
            account_id=account_no,
            order_id=orderid
        )
        
        order_status, symbol = get_order_status(orderid)
        
        if order_status == 'CANCELED':
            print('Quickdraw order was canceled')
            status.config(text = 'Last Quickdraw order was canceled ')
            button.config(state="normal")
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
    print('Replacing order for #' + str(orderid) + ' at ' + str(new_price))

    replace_option_order = {
        "session": "NORMAL",
        "duration": "GOOD_TILL_CANCEL",
        "orderStrategyType": "SINGLE",
        "orderType": "LIMIT",
        "price": new_price,
        # "price": 0.15,
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
    print(response)  # should be ID

    print('Successfully replaced buy order for ' +
          str(orderid) + ' at ' + str(new_price))


def replace_sell_order(orderid, contract_symbol, new_price):
    print('Replacing sell order for #' + str(orderid) +
          ', changing price to: ' + str(new_price))

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
    print(response)  # should be ID

    print('Successfully replaced buy order for ' +
          str(orderid) + ' at ' + str(new_price))


def log_quickdraw_buy_order():
    timestr = datetime.datetime.now().strftime("%Y_%m_%d")
    close_time, symbol2, orderid, instruction, desc, quantity, status, price = view_last_filled_orderid()
    print('Logging buy order')
    quote_service = td_client.quotes()
    quote = quote_service.get_quote(instrument=symb)
    shareprice = quote[symb]['lastPrice']

    trade = [close_time, shareprice, symbol2, orderid,
             instruction, desc, quantity, status, price]

    with open('logs/' + timestr + "_3dte_quickdraw_log.csv", "a", newline='') as log:
        csv_output = writer(log)
        csv_output.writerow(trade)


def log_quickdraw_sell_order():
    timestr = datetime.datetime.now().strftime("%Y_%m_%d")
    print('Logging sell order')
    log = pd.read_csv(timestr + '_3dte_quickdraw_log.csv')
    last = log.iloc[-1]
    sharebuyprice = last['share_price']
    buyprice = last['price']

    quote_service = td_client.quotes()
    quote = quote_service.get_quote(instrument=symb)
    shareprice = quote[symb]['lastPrice']

    spnl = shareprice - sharebuyprice

    close_time, symbol2, orderid, instruction, desc, quantity, status, price = view_last_filled_orderid()

    pnl = price - buyprice
    pnl = round(pnl, 2)
    trade = [close_time, shareprice, symbol2, orderid,
             instruction, desc, quantity, status, price, pnl, spnl]

    with open('logs/' + timestr + "_3dte_quickdraw_log.csv", "a", newline='') as log:
        csv_output = writer(log)
        csv_output.writerow(trade)

# Buy order scheme

def QuickdrawBuy(side, quantity, status):

    contract = build_3dte_order(side, status)
    place_option_order(contract, quantity, status)
    global open_position

    open_position = True
    if side == "long":
        status.config(text = 'In ' + str(quantity) + ' calls >> ' + contract[0])
    if side == "short":
        status.config(text = 'In ' + str(quantity) + ' puts >> ' + contract[0])


        
    return contract


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



def buy_call(num, status, button):
    button.config(state="disabled")

    global buy_order
    global num_contracts
    global order_side
    order_side = "long"
    num_contracts = num
    buy_order = QuickdrawBuy('long', num, status)
    
    button.config(state="normal")

def buy_put(num, status, button):
    button.config(state="disabled")

    global buy_order
    global num_contracts
    global order_side
    order_side = "short"
    num_contracts = num
    buy_order = QuickdrawBuy('short', num, status)

    button.config(state="normal")

def sell_option(num, status, button):
    button.config(state="disabled")

    if open_position == True:
        symbol = buy_order[0]
        place_sell_order(symbol, num, status)
    elif open_position == False:
        status.config(text = 'No open positions to sell')
    else:
        status.config(text = 'open position variable is none')

    button.config(state="normal")
  
def flip(status, button):
    global order_side
    global num_contracts
    global buy_order
    root.button_flip.config(state="disabled")
    if open_position == True:

        symbol = buy_order[0]
        place_sell_order(symbol, num_contracts, status)
        if order_side == "long":
            buy_order = QuickdrawBuy("short", num_contracts, status)
            order_side = "short"
        elif order_side == "short":
            buy_order = QuickdrawBuy("long", num_contracts, status)
            order_side = "long"
        else:
            print("Error in order_side variable: It is neither long or short")
    elif open_position == False:
        status.config(text = 'No open positions to flip')
    else:
        status.config(text = 'open position variable is none')
     
    root.button_flip.config(state="normal")

def closeall(status, button):
    button.config(state="disabled")

    if open_position == True:

        symbol = buy_order[0]
        place_sell_order(symbol, num_contracts, status)
        status.config(text = 'All options closed')
    elif open_position == False:
        status.config(text = 'No open options to close')

    button.config(state="normal")

def tasks_done(task):
    messagebox.showinfo(message='Stream closed.')
    
def ticker_submit(tickerlabel):
    global symb
    symb = ticker_var.get()
    tickerlabel2.config(text = symb)

if __name__ == '__main__':
    asyncio.set_event_loop_policy(aiotkinter.TkinterEventLoopPolicy())
    loop = asyncio.get_event_loop()

    background="#00aaee"
    opacity=0.9

    root = tk.Tk()
    root.geometry("630x370")
    root.title('Options Trader')
    root.resizable(1, 1)



    root.configure(background=background)
    root.overrideredirect(True)
    root.overrideredirect(False)
    root.wm_attributes("-alpha", opacity)
    root.wm_attributes("-topmost", "true")

    root.columnconfigure(0, weight=1)
    root.columnconfigure(1, weight=2)
    root.columnconfigure(2, weight=2)

    tickerlabel = tk.Label(root, text='Active Ticker:', bg=background, fg="black", font=("calibre", 14))
    tickerlabel.grid(column=0, row=0, sticky=tk.W, padx=10, pady=10)
    tickerlabel2 = tk.Label(root, text='QQQ', bg=background, fg="black", font=("calibre", 14))
    tickerlabel2.grid(column=0, row=0, sticky=tk.E, padx=10, pady=10)

    ticker_var = tk.StringVar()
    ticker_entry = tk.Entry(root, width=5, textvariable = ticker_var, font=('calibre',14,'normal'))
    ticker_entry.grid(column=1, row=0, sticky=tk.W, padx=10, pady=10)

    sub_btn=tk.Button(root, text = 'Change', command=lambda : ticker_submit(tickerlabel2))
    sub_btn.grid(column=1, row=0, sticky=tk.E, padx=10, pady=10)

    status = tk.Label(root, text='status', bg="gray", fg="black", font=("calibre", 14))
    status.grid(column=0, row=1, columnspan=2, sticky=tk.W+tk.E, padx=15, pady=15)

    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday"
    ]
    dayclicked = StringVar()
    dayclicked.set(weekdays[day])
    def selectday(daylabel2):
        daylabel2.config( text = dayclicked.get() )
        global optiondate
        optiondate = dayclicked.get()

    daylabel = tk.Label(root, text='Strike Day:', bg=background, fg="black", font=("calibre", 14))
    daylabel.grid(column=4, row=0, sticky=tk.W, padx=5, pady=5)
    daylabel2 = tk.Label(root, text=weekdays[day], bg=background, fg="black", font=("calibre", 14))
    daylabel2.grid(column=4, row=1, sticky=tk.W+tk.N, padx=5, pady=5)

    drop = OptionMenu(root, dayclicked, *days)
    drop.grid(column=4, row=2, sticky=tk.W, padx=5, pady=5)
    root.daybutton = Button(root, text = "Select DTE", command=lambda : selectday(daylabel2))
    root.daybutton.grid(column=4, row=3, sticky=tk.E, padx=5, pady=5)

    # pricelabel = tk.Label(root, text='Last Price:', bg=background, fg="black", font=("Arial", 14))
    # pricelabel.grid(column=2, row=0, sticky=tk.W, padx=5, pady=5)
    # pricelabel2 = tk.Label(root, text='$$$$', bg=background, fg="black", font=("Arial", 14))
    # pricelabel2.grid(column=2, row=1, sticky=tk.W+tk.N, padx=5, pady=5)

    root.button_buycall = Button(root, text='Buy 1 CALL', command=lambda : buy_call(1, status, root.button_buycall))
    root.button_buycall.grid(column=0, row=2, padx=5, pady=5)
    root.button_sellcall = Button(root, text='Close 1 CALL', command=lambda : sell_option(1, status, root.button_sellcall))
    root.button_sellcall.grid(column=0, row=3, padx=5, pady=5)

    root.button_buycall = Button(root, text='Buy 2 CALLS', command=lambda : buy_call(2, status, root.button_buycall))
    root.button_buycall.grid(column=1, row=2, padx=5, pady=5)
    root.button_sellcall = Button(root, text='Close 2 CALLS', command=lambda : sell_option(2, status, root.button_sellcall))
    root.button_sellcall.grid(column=1, row=3, padx=5, pady=5)

    root.button_buycall = Button(root, text='Buy 5 CALLS', command=lambda : buy_call(5, status, root.button_buycall))
    root.button_buycall.grid(column=2, row=2, padx=5, pady=5)
    root.button_sellcall = Button(root, text='Close 5 CALLS', command=lambda : sell_option(5, status, root.button_sellcall))
    root.button_sellcall.grid(column=2, row=3, padx=5, pady=5)

    root.button_cancel = Button(root, text='Cancel Order', command=lambda : cancel_quickdraw_order(status, root.button_cancel))
    root.button_cancel.grid(column=0, row=4, padx=15, pady=15)

    root.button_flip = Button(root, text='Flip', command=lambda : flip(status, root.button_flip))
    root.button_flip.grid(column=1, row=4, padx=15, pady=15)

    root.button_buyput = Button(root, text='Buy 1 PUT', command=lambda : buy_put(1, status, root.button_buyput))
    root.button_buyput.grid(column=0, row=5, padx=5, pady=5)
    root.button_sellput = Button(root, text='Sell 1 PUT', command=lambda : sell_option(1, status, root.button_sellput))
    root.button_sellput.grid(column=0, row=6, padx=5, pady=5)

    root.button_buyput = Button(root, text='Buy 2 PUTS', command=lambda : buy_put(2, status, root.button_buyput))
    root.button_buyput.grid(column=1, row=5, padx=5, pady=5)
    root.button_sellput = Button(root, text='Sell 2 PUTS',  command=lambda : sell_option(2, status, root.button_sellput))
    root.button_sellput.grid(column=1, row=6, padx=5, pady=5)

    root.button_buyput = Button(root, text='Buy 5 PUTS',command=lambda : buy_put(5, status, root.button_buyput))
    root.button_buyput.grid(column=2, row=5, padx=5, pady=5)
    root.button_sellput = Button(root, text='Sell 5 PUTS', command=lambda : sell_option(5, status, root.button_sellput))
    root.button_sellput.grid(column=2, row=6, padx=5, pady=5)

    root.button_closeall = Button(root, text='Close All', command=lambda : closeall(status, root.button_closeall))
    root.button_closeall.grid(column=0, row=7, padx=15, pady=15)


    loop.run_forever()

