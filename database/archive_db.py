# -*- coding: utf-8 -*-

import json
import os
from datetime import datetime


class SearchArchive:
    def __init__(self):
        self.archive_file = "search_archive.json"
        self.archives = {}
        self.load_archives()

    def load_archives(self):
        if os.path.exists(self.archive_file):
            try:
                with open(self.archive_file, 'r', encoding='utf-8') as f:
                    self.archives = json.load(f)
            except:
                self.archives = {}

    def save_archives(self):
        try:
            with open(self.archive_file, 'w', encoding='utf-8') as f:
                json.dump(self.archives, f, ensure_ascii=False, indent=2)
        except:
            pass

    def add_search(self, username, query, result_preview):
        entry = {
            'username': username,
            'query': query,
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'result_preview': result_preview[:200]
        }

        date_key = datetime.now().strftime("%Y-%m-%d")
        if date_key not in self.archives:
            self.archives[date_key] = []

        self.archives[date_key].append(entry)

        # Ограничиваем архив 30 днями
        keys = sorted(self.archives.keys())
        while len(keys) > 30:
            del self.archives[keys[0]]
            keys = keys[1:]

        self.save_archives()

    def get_all_searches(self, limit=30):
        all_searches = []
        for date, searches in sorted(self.archives.items(), reverse=True):
            for search in reversed(searches):
                all_searches.append(search)
                if len(all_searches) >= limit:
                    return all_searches
        return all_searches


search_archive = SearchArchive()