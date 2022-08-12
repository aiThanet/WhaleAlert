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

        logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
        

    def check_owner_in_list(self, tran):
        return ((tran['to'].get('owner','').upper() in self.ex_check_list) or (tran['from'].get('owner','').upper() in self.ex_check_list)) and (tran['to'].get('owner','') != tran['from'].get('owner',''))

    def get_bnb_price(self, line_notify=True):
        res = requests.get('https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BNBUSDT')
        res_json = res.json()
        price = "{:.2f}".format(float(res_json.get('markPrice',0)))
        if line_notify:
            self.line_notify.send(f"BNB Mark Price: {price}")
        return price

    def print_bnb_price(self):
        if self.get_price_until >= self.run_count and self.last_print_price > (self.run_count + (60//self.sleep_time)):
            self.get_bnb_price()
            self.last_print_price = self.run_count

    def run(self, time):
        self.run_count += 1
        self.print_bnb_price()
        
        query = {
            'start': time,
            'min_value': self.min_usd,
            'api_key': self.api_key
        }
        query = '&'.join([f'{q}={query[q]}' for q in query])
        res = requests.get(self.url + '?' + query)
        res_json = res.json()
        if(res_json.get('result','') != 'success'):
            logging.error(res_json)
        transactions = res_json.get('transactions',[])

        results = []
        for tran in transactions:
            if tran['symbol'].upper() in self.sym_check_list and int(tran['timestamp']) > self.prev_timestamp:
                _from = 'Unknown' if tran['from']['owner_type'] == 'unknown' else tran['from']['owner'].upper()
                _to = 'Unknown' if tran['to']['owner_type'] == 'unknown' else tran['to']['owner'].upper()
                logging.info(f'{"{:,}".format(int(tran["amount"]))} {tran["symbol"].upper()} ({"{:,}".format(int(tran["amount_usd"]))} USD) transfer from {_from} to {_to}')
                if self.check_owner_in_list(tran):
                    results.append({
                        'symbol': tran['symbol'].upper(),
                        'from': _from,
                        'to': _to,
                        'amount': int(tran['amount']),
                        'amount_usd': int(tran['amount_usd']),
                        'timestamp': tran['timestamp'],
                        'datetime': datetime.fromtimestamp(int(tran['timestamp'])).strftime("%d-%m-%Y %H:%M:%S")
                    })
                    if _to == 'BINANCE':
                        self.get_price_until = self.run_count + ((60//self.sleep_time) * 10)
                        if self.run_count > self.last_print_price:
                            self.get_bnb_price()

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


