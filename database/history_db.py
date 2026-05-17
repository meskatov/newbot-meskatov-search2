# -*- coding: utf-8 -*-

import json
import os
from datetime import datetime, timedelta


class RequestsHistory:
    def __init__(self):
        self.history_file = "requests_history.json"
        self.history = []
        self.load_history()

    def load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
            except:
                self.history = []

    def save_history(self):
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history[-1000:], f, ensure_ascii=False, indent=2)
        except:
            pass

    def add_request(self, admin_username, target_username, amount):
        self.history.append({
            'admin': admin_username,
            'target': target_username,
            'amount': amount,
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        self.save_history()

    def get_today_stats(self):
        today = datetime.now().strftime("%Y-%m-%d")
        total_requests = 0
        total_amount = 0
        for req in self.history:
            if req['date'].startswith(today):
                total_requests += 1
                total_amount += req['amount']
        return {'total_requests': total_requests, 'total_amount': total_amount}

    def get_yesterday_stats(self):
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        total_requests = 0
        total_amount = 0
        for req in self.history:
            if req['date'].startswith(yesterday):
                total_requests += 1
                total_amount += req['amount']
        return {'total_requests': total_requests, 'total_amount': total_amount}

    def get_week_stats(self):
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        total_requests = 0
        total_amount = 0
        for req in self.history:
            if req['date'] >= week_ago:
                total_requests += 1
                total_amount += req['amount']
        return {'total_requests': total_requests, 'total_amount': total_amount}


requests_history = RequestsHistory()