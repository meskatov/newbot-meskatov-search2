# -*- coding: utf-8 -*-

import json
import os
from datetime import datetime


class UserBalance:
    def __init__(self):
        self.balances_file = "user_balances.json"
        self.balances = {}
        self.load_balances()

    def load_balances(self):
        if os.path.exists(self.balances_file):
            try:
                with open(self.balances_file, 'r', encoding='utf-8') as f:
                    self.balances = json.load(f)
                print(f"Загружено {len(self.balances)} пользователей")
            except:
                self.balances = {}
        else:
            self.balances = {}
            self.save_balances()

    def save_balances(self):
        try:
            with open(self.balances_file, 'w', encoding='utf-8') as f:
                json.dump(self.balances, f, ensure_ascii=False, indent=2)
        except:
            pass

    def ensure_user(self, user_id, username=None, first_name=None, last_name=None):
        user_id_str = str(user_id)
        if user_id_str not in self.balances:
            self.balances[user_id_str] = {
                'requests': 10,
                'total_received': 10,
                'total_used': 0,
                'username': username or 'unknown',
                'first_name': first_name or '',
                'last_name': last_name or '',
                'joined_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.save_balances()
            print(f"✅ Новый пользователь: {user_id} (@{username}) - выдано 10 запросов")
            return True
        return False

    def get_balance(self, user_id):
        user_id_str = str(user_id)
        if user_id_str in self.balances:
            return self.balances[user_id_str].get('requests', 0)
        return 0

    def add_requests(self, user_id, username, amount):
        user_id_str = str(user_id)
        self.ensure_user(user_id, username)

        if user_id_str not in self.balances:
            self.balances[user_id_str] = {'requests': 0, 'total_received': 0, 'total_used': 0,
                                          'username': username or 'unknown'}

        self.balances[user_id_str]['requests'] = self.balances[user_id_str].get('requests', 0) + amount
        self.balances[user_id_str]['total_received'] = self.balances[user_id_str].get('total_received', 0) + amount
        self.balances[user_id_str]['username'] = username or self.balances[user_id_str].get('username', 'unknown')
        self.save_balances()
        return self.balances[user_id_str]['requests']

    def use_request(self, user_id):
        user_id_str = str(user_id)
        if user_id_str in self.balances:
            if self.balances[user_id_str].get('requests', 0) > 0:
                self.balances[user_id_str]['requests'] -= 1
                self.balances[user_id_str]['total_used'] = self.balances[user_id_str].get('total_used', 0) + 1
                self.save_balances()
                return True
        return False

    def get_full_user_data(self, user_id):
        user_id_str = str(user_id)
        if user_id_str in self.balances:
            return self.balances[user_id_str]
        return {'requests': 0, 'total_received': 0, 'total_used': 0, 'username': 'unknown'}

    def get_all_users(self):
        return self.balances

    def get_top_users(self, limit=15):
        users = []
        for user_id, data in self.balances.items():
            users.append({
                'user_id': user_id,
                'username': data.get('username', 'unknown'),
                'total_used': data.get('total_used', 0),
                'requests_left': data.get('requests', 0)
            })
        users.sort(key=lambda x: x['total_used'], reverse=True)
        return users[:limit]

    def find_user_by_username(self, username):
        if not username:
            return None
        username_lower = username.lower()
        for user_id, data in self.balances.items():
            if data.get('username', '').lower() == username_lower:
                return int(user_id)
        return None


user_balance = UserBalance()