# -*- coding: utf-8 -*-

import asyncio
import json
import os
from collections import deque
from datetime import datetime

QUEUE_FILE = "queue_data.json"


class RequestQueue:
    def __init__(self):
        self.waiting_queue = deque()
        self.processing = {}
        self.request_counter = 0
        self._shutdown = False
        self.load_queue()

    def load_queue(self):
        if os.path.exists(QUEUE_FILE):
            try:
                with open(QUEUE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.waiting_queue = deque(data.get('waiting_queue', []))
                    self.request_counter = data.get('request_counter', 0)
            except:
                pass

    def save_queue(self):
        try:
            with open(QUEUE_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    'waiting_queue': list(self.waiting_queue),
                    'request_counter': self.request_counter
                }, f, ensure_ascii=False, indent=2)
        except:
            pass

    def add_request(self, user_id, username, query, chat_id):
        self.request_counter += 1
        request = {
            'id': self.request_counter,
            'user_id': user_id,
            'username': username,
            'query': query,
            'chat_id': chat_id,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.waiting_queue.append(request)
        self.save_queue()
        return request['id'], f"Запрос #{self.request_counter} добавлен в очередь. Ожидайте..."

    def get_next_request(self):
        if self.waiting_queue:
            return self.waiting_queue.popleft()
        return None

    def get_queue_stats(self):
        return {'waiting': len(self.waiting_queue), 'processing': len(self.processing)}

    def get_queue_list(self, limit=20):
        result = []
        for i, req in enumerate(list(self.waiting_queue)[:limit], 1):
            result.append(f"{i}. #{req['id']} @{req['username']}: {req['query'][:50]}")
        return result

    def clear_queue(self):
        count = len(self.waiting_queue)
        self.waiting_queue.clear()
        self.save_queue()
        return count

    async def shutdown(self):
        self._shutdown = True
        self.save_queue()


request_queue = RequestQueue()


async def queue_processor(app):
    from handlers.process_handler import process_request

    print("🔄 Обработчик очереди запущен")

    while not request_queue._shutdown:
        try:
            request = request_queue.get_next_request()

            if request:
                request_id = request['id']
                request_queue.processing[request_id] = True

                print(f"📝 Обработка #{request_id}: {request['query']}")

                try:
                    await process_request(app, request)
                except Exception as e:
                    print(f"Ошибка: {e}")
                    try:
                        await app.bot.send_message(
                            chat_id=request['chat_id'],
                            text=f"❌ Ошибка: {str(e)[:200]}"
                        )
                    except:
                        pass
                finally:
                    if request_id in request_queue.processing:
                        del request_queue.processing[request_id]
                    request_queue.save_queue()

            await asyncio.sleep(1)

        except Exception as e:
            print(f"Ошибка: {e}")
            await asyncio.sleep(5)

    print("Обработчик очереди остановлен")