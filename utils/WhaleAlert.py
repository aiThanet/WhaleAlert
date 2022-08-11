from dotenv import load_dotenv
from line_notify import LineNotify
from datetime import datetime
from utils import utils

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

        self.schedule = int(os.environ.get('MINUTE_SCHEDULE', 5))
        self.min_usd = int(os.environ.get('MIN_USD_VALUE', 500000))

        self.sym_check_list = utils.load_env_list('SYM_CHECK_LIST')
        self.ex_check_list = utils.load_env_list('EXCHANGE_CHECK_LIST')
        
        self.prev_timestamp = 0
        self.hashes = []

    def check_owner_in_list(self, tran):
        return (tran['to'].get('owner','').upper() in self.ex_check_list) or (tran['from'].get('owner','').upper() in self.ex_check_list)

    def run(self, time):
        query = {
            'start': time,
            'min_value': self.min_usd,
            'api_key': self.api_key
        }
        query = '&'.join([f'{q}={query[q]}' for q in query])
        res = requests.get(self.url + '?' + query)
        transactions = res.json().get('transactions',[])

        

        results = []
        for tran in transactions:
            if tran['symbol'].upper() in self.sym_check_list and self.check_owner_in_list(tran):
                if int(tran['timestamp']) > self.prev_timestamp: 
                    results.append({
                        'symbol': tran['symbol'].upper(),
                        'from': 'Unknown' if tran['from']['owner_type'] == 'unknown' else tran['from']['owner'].upper(),
                        'to': 'Unknown' if tran['to']['owner_type'] == 'unknown' else tran['to']['owner'].upper(),
                        'amount': int(tran['amount']),
                        'amount_usd': int(tran['amount_usd']),
                        'timestamp': tran['timestamp'],
                        'datetime': datetime.fromtimestamp(int(tran['timestamp'])).strftime("%d-%m-%Y %H:%M:%S")
                    })

        if len(results) > 0:
            self.prev_timestamp = max([int(tran["timestamp"]) for tran in results])

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


