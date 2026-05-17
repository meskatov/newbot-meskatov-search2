# -*- coding: utf-8 -*-

import json
import os
from datetime import datetime


class UsersDatabase:
    def __init__(self):
        self.db_file = "users_database.json"
        self.users = {}
        self.load_users()

    def load_users(self):
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    self.users = json.load(f)
            except:
                self.users = {}

    def save_users(self):
        try:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, ensure_ascii=False, indent=2)
        except:
            pass

    def add_user(self, user_id, username, first_name=None, last_name=None):
        user_id_str = str(user_id)
        if user_id_str not in self.users:
            self.users[user_id_str] = {
                'user_id': user_id,
                'username': username,
                'first_name': first_name or '',
                'last_name': last_name or '',
                'first_seen': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'total_searches': 0,
                'searches': []
            }
            self.save_users()
            return True
        return False

    def add_search(self, user_id, username, query, result_preview):
        user_id_str = str(user_id)
        if user_id_str not in self.users:
            self.add_user(user_id, username)

        self.users[user_id_str]['total_searches'] = self.users[user_id_str].get('total_searches', 0) + 1
        self.users[user_id_str]['searches'].append({
            'query': query,
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'result_preview': result_preview[:200]
        })

        if len(self.users[user_id_str]['searches']) > 50:
            self.users[user_id_str]['searches'] = self.users[user_id_str]['searches'][-50:]

        self.save_users()

    def get_user_info(self, user_id):
        user_id_str = str(user_id)
        return self.users.get(user_id_str)

    def get_user_searches(self, user_id, limit=10):
        user_id_str = str(user_id)
        if user_id_str in self.users:
            return self.users[user_id_str].get('searches', [])[-limit:]
        return []

    def get_all_users(self):
        return self.users

    def get_stats(self):
        total_users = len(self.users)
        total_searches = sum(u.get('total_searches', 0) for u in self.users.values())
        return total_users, total_searches


users_db = UsersDatabase()