# Options Trader
# v1.2
# Kivy Version

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.core.window import Window
from kivy.clock import Clock


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



# should be reomved (not used)
from tkinter import messagebox


open_position = False

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


def tasks_done(task):
    messagebox.showinfo(message='Stream closed.')


class MainBox(BoxLayout):

    def __init__(self, **kwargs):
        super(MainBox, self).__init__(**kwargs)


    # check ticker if more than 4 characters and capital letters
    def check_ticker(self):
        ticker = self.ids.ticker_input.text
        if len(ticker) > 4:
            self.ids.ticker_input.text = ticker[:4]
        else:
            self.ids.ticker_input.text = ticker.upper()


    # builds only for indexes with daily options, not equities
    def build_3dte_order(self, option):

        # assign ticker to symb variable
        symb = self.ids.ticker_box.text
    
        # build the order
        day = datetime.date.today().isoweekday()
        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(days=1)
        
        # wednesday
        if day == 3:
            three_days = today + datetime.timedelta(days=2)
        
        # thursday
        if day == 4:
            three_days = today + datetime.timedelta(days=4)
        
        # friday
        elif day == 5:
            three_days = today + datetime.timedelta(days=3)
        
        # monday, tuesday
        else:
            three_days = today + datetime.timedelta(days=2)

        # get 1 strike above and 1 below
        options_chain_service = td_client.options_chain()

        option_chain_query = OptionChainQuery(
            symbol=symb,
            contract_type=ContractType.All,
            from_date=three_days,
            to_date=three_days,
            strike_count='2',
            option_type=OptionType.StandardContracts
        )
        print('Retrieving chain for ' + symb)
        chain = options_chain_service.get_option_chain(
            option_chain_query=option_chain_query)
        chain_status = chain['status']
        if chain_status == 'FAILED':
            print('Failed. Chain does not exist.')
            self.ids.status_box.text = 'Chain does not exist for Monday. Trying Friday.'
            
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


    def place_option_order(self, contract, quantity):
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



    def place_sell_order(self, contract_symbol, quantity):

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
        self.ids.status_box.text = 'Closed ' + str(quantity) + ' options >> ' + contract_symbol



    def log_quickdraw_buy_order(self):
        # assign ticker to symb variable
        symb = self.ids.ticker_box.text
        
        timestr = datetime.datetime.now().strftime("%Y_%m_%d")
        close_time, symbol2, orderid, instruction, desc, quantity, status, price = view_last_filled_orderid()
        print('Logging buy order')
        quote_service = td_client.quotes()
        quote = quote_service.get_quote(instrument=symb)
        shareprice = quote[symb]['lastPrice']

        trade = [close_time, shareprice, symbol2, orderid,
                 instruction, desc, quantity, status, price]

        with open(timestr + "_3dte_quickdraw_log.csv", "a", newline='') as log:
            csv_output = writer(log)
            csv_output.writerow(trade)


    def log_quickdraw_sell_order():
        # assign ticker to symb variable
        symb = self.ids.ticker_box.text

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

        with open(timestr + "_3dte_quickdraw_log.csv", "a", newline='') as log:
            csv_output = writer(log)
            csv_output.writerow(trade)




    # Buy order scheme

    def QuickdrawBuy(self, side, quantity):

        contract = self.build_3dte_order(side)
        self.place_option_order(contract, quantity)
        global open_position

        open_position = True
        if side == "long":
            self.ids.status_box.text = 'In ' + str(quantity) + ' calls >> ' + contract[0]
        if side == "short":
            self.ids.status_box.text = 'In ' + str(quantity) + ' puts >> ' + contract[0]

        self.log_quickdraw_buy_order()

            
        return contract


    def buy_call(self, num, button):
        button.disabled = True

        global buy_order
        global num_contracts
        global order_side
        order_side = "long"
        num_contracts = num
        buy_order = self.QuickdrawBuy('long', num)

        button.disabled = False


    def buy_put(self, num, button):
        button.disabled = True

        global buy_order
        global num_contracts
        global order_side
        order_side = "short"
        num_contracts = num
        buy_order = self.QuickdrawBuy('short', num)

        button.disabled = False


    def sell_option(self, num, button):
        button.disabled = True

        if open_position == True:
            symbol = buy_order[0]
            self.place_sell_order(symbol, num)
        elif open_position == False:
            self.ids.status_box.text = 'No open positions to sell'
        else:
            self.ids.status_box.text = 'open position variable is none'

        button.disabled = False


    def cancel_quickdraw_order(self):

        # Cancel order
        orderid, symbol = view_working_orders()
        order_status = ''
        while order_status != 'CANCELED':

            orders_service = td_client.orders()
            orders_service.cancel_order(
                account_id=account_no,
                order_id=orderid
            )
            order_status, symbol = get_order_status(orderid)
            if order_status == 'CANCELED':
                print('Quickdraw order was canceled')
                self.ids.status_box.text = 'Last Quickdraw order was canceled '

                break


    def flip(self, button):
        global order_side
        global num_contracts
        global buy_order
        button.disabled = True
        if open_position == True:

            symbol = buy_order[0]
            self.place_sell_order(symbol, num_contracts)
            if order_side == "long":
                buy_order = self.QuickdrawBuy("short", num_contracts)
                order_side = "short"
            elif order_side == "short":
                buy_order = self.QuickdrawBuy("long", num_contracts)
                order_side = "long"
            else:
                print("Error in order_side variable: It is neither long or short")
        elif open_position == False:
            self.ids.status_box.text = 'No open positions to flip'
        else:
            self.ids.status_box.text = 'open position variable is none'
         
        button.disabled = False


    def closeall(self, button):
        button.disabled = True

        if open_position == True:

            symbol = buy_order[0]
            self.place_sell_order(symbol, num_contracts)
            self.ids.status_box.text = 'All options closed'
        elif open_position == False:
            self.ids.status_box.text = 'No open options to close'

        button.disabled = False


    def ticker_submit(self):
        self.ids.ticker_box.text = self.ids.ticker_input.text


class TraderApp(App):

    def build(self):
        self.title = 'Options Trader'
        #Window.size = (530, 370) # width, height
        Window.size = (600, 400) # width, height

        main_box = MainBox()

        return main_box

if __name__ == '__main__':
    TraderApp().run()

