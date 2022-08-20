from dotenv import load_dotenv
from line_notify import LineNotify
from datetime import datetime
from utils import utils

import logging
import requests
import json
import os

class WhaleAlert:
    def __init__(self):
        self.initialize()

    def initialize(self):
        load_dotenv(verbose=True)
        self.api_key = os.environ.get('API_KEY', '')
        self.url = "https://api.whale-alert.io/v1/transactions"
        
        self.line_token = os.environ.get('LINE_TOKEN', '')
        self.line_notify = LineNotify(self.line_token)

        self.lookback = int(os.environ.get('MINUTE_LOOKBACK', 5))
        self.min_usd = int(os.environ.get('MIN_USD_VALUE', 500000))
        self.sleep_time = int(os.environ.get('SLEEP_TIME', 10))

        self.sym_check_list = utils.load_env_list('SYM_CHECK_LIST')
        self.ex_check_list = utils.load_env_list('EXCHANGE_CHECK_LIST')
        
        self.prev_timestamp = 0
        self.run_count = 0
        self.last_print_price = 0
        self.get_price_until = 0
        self.last_mark_price = {}
        self.data = []

        logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
        

    def check_owner_in_list(self, tran):
        return ((tran['to'].get('owner','').upper() in self.ex_check_list) or (tran['from'].get('owner','').upper() in self.ex_check_list)) and (tran['to'].get('owner','') != tran['from'].get('owner',''))

    def get_coin_price(self, sym='BNB'):
        res = requests.get(f'https://fapi.binance.com/fapi/v1/premiumIndex?symbol={sym}USDT')
        res_json = res.json()
        cur_price = float(res_json.get('markPrice',0))
        
        return cur_price

    def send_line_all_prices(self, price_dict):
        now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        txt = f' {now}\n------------------------------\n'

        for sym in price_dict:
            cur_price = price_dict[sym]
            price = "{:.2f}".format(cur_price)
            change = 0 if self.last_mark_price.get(sym, 0) == 0 else (((cur_price - self.last_mark_price.get(sym, 0))/self.last_mark_price.get(sym, 0)) * 100)
            change_display = '' if change == 0 else ('(' + ('🟩+' if change > 0 else '🟥') + f'{"{:.2f}".format(change)}%)')
            txt += f'{sym} Mark Price: {price} {change_display}\nLast Mark Price: {"{:.2f}".format(self.last_mark_price.get(sym, 0))}\n'
            self.last_mark_price[sym] = cur_price
        
        self.line_notify.send(txt)
        

    def print_all_prices(self, notify=True):
            bnb_price = self.get_coin_price(sym='BNB')
            btc_price = self.get_coin_price(sym='BTC')
            price_dict = {
                'BNB': bnb_price,
                'BTC': btc_price
            }
            if notify:
                self.send_line_all_prices(price_dict)
            self.last_print_price = self.run_count
            return price_dict

    def write_log(self, txt):
        with open('prices.txt', 'a') as f:
            f.write(txt)

    def run(self, time):
        self.run_count += 1
        if self.get_price_until >= self.run_count and self.run_count >= (self.last_print_price + (60//self.sleep_time)):
            prices = self.print_all_prices(notify=False)
            for i in range(len(self.data)-1, -1, -1):
                if self.run_count <= self.data[i]['end']:
                    self.data[i]['btc'].append(prices['BTC'])
                    self.data[i]['bnb'].append(prices['BNB'])
                else:
                    txt = f"{self.data[i]['symbol']},{self.data[i]['from']} {self.data[i]['to']},{self.data[i]['amount']},{self.data[i]['amount_usd']},{self.data[i]['datetime']}"
                   
                    btcs = ','.join(self.data[i]['btc'])
                    bnbs = ','.join(self.data[i]['bnb'])
                    txt += f",{btcs},{bnbs}\n"

                    self.write_log(txt)

                    del self.data[i]

        
        query = {
            'start': time,
            'min_value': self.min_usd,
            'api_key': self.api_key
        }
        query = '&'.join([f'{q}={query[q]}' for q in query])
        res = requests.get(self.url + '?' + query)
        try:
            res_json = res.json()
        except:
            return
        if(res_json.get('result','') != 'success'):
            logging.error(res_json)
        transactions = res_json.get('transactions',[])

        results = []
        for tran in transactions:
            if tran['symbol'].upper() in self.sym_check_list and int(tran['timestamp']) > self.prev_timestamp:
                _from = 'Unknown' if tran['from']['owner_type'] == 'unknown' else tran['from']['owner'].upper()
                _to = 'Unknown' if tran['to']['owner_type'] == 'unknown' else tran['to']['owner'].upper()
                logging.info(f'{"{:,}".format(int(tran["amount"]))} {tran["symbol"].upper()} ({"{:,}".format(int(tran["amount_usd"]))} USD) transfer from {_from} to {_to}')
                if self.check_owner_in_list(tran) and _from == 'Unknown' and _to == 'BINANCE':
                    res = {
                        'symbol': tran['symbol'].upper(),
                        'from': _from,
                        'to': _to,
                        'amount': int(tran['amount']),
                        'amount_usd': int(tran['amount_usd']),
                        'timestamp': tran['timestamp'],
                        'datetime': datetime.fromtimestamp(int(tran['timestamp'])).strftime("%d-%m-%Y %H:%M:%S")
                    }
                    results.append(res)
                    self.get_price_until = self.run_count + ((60//self.sleep_time) * 10) + 1
                    
                    prices = self.print_all_prices()
                    res['btc'] = [prices['BTC']]
                    res['bnb'] = [prices['BNB']]
                    res['start'] = self.run_count
                    res['end'] = self.get_price_until

                    self.data.append(res)

        if len(transactions) > 0:
            self.prev_timestamp = max([int(tran["timestamp"]) for tran in transactions])

        for res in results:
            self.send_line_notify(res)

    def get_level(self,amount):
        if amount < 1_000_000:
            return '🦐'
        elif amount < 5_000_000:
            return '🐙🐙'
        elif amount < 10_000_000:
            return '🐳🐳🐳'
        else:
            return '🚨' * (amount//10_000_000)

    def send_line_notify(self, res):
        txt = ''
        level = self.get_level(res['amount_usd'])
        txt += f' {res["datetime"]}\n-----\n{level}\n'
        txt += f'{"{:,}".format(res["amount"])} {res["symbol"]}\n'
        txt += f'[{"{:,}".format(res["amount_usd"])} USD]\n'
        txt += f'-----\ntransferred from\n'
        txt += f'#{res["from"]} to #{res["to"]}'

        self.line_notify.send(txt)


