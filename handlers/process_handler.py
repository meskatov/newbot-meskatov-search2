# -*- coding: utf-8 -*-

import re
import requests
import os
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# ================= НАСТРОЙКИ API (ТОЛЬКО РАБОЧИЕ) =================
INFINITY_API_URL = "https://infinity-check.online/find.php"
INFINITY_TOKEN = "R8fK2Lm9QWv3E7ZpD1yU4C6VtX5H0BJs"

DEPSEARCH_API_URL = "https://api.depsearch.sbs/search"
DEPSEARCH_TOKEN = "WDTHx2vqZGE38gchBe7oAewzB9ZPNpxU"

BIGBASE_URL = "https://bigbase.top/api/search"
BIGBASE_TOKEN = "BOqMzQ63vPTPKs7gfUDrJru62SX2JaqC"

# Папка для HTML отчетов
HTML_REPORTS_DIR = "search_reports"

if not os.path.exists(HTML_REPORTS_DIR):
    os.makedirs(HTML_REPORTS_DIR)


def clean_text(text):
    if not isinstance(text, str):
        text = str(text)
    text = text.replace('_', '.')
    text = text.replace('*', 'x')
    text = text.replace('[', '(')
    text = text.replace(']', ')')
    return text


def detect_query_type(query):
    query_clean = re.sub(r'[\s\+\(\)\-]', '', query)

    if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', query):
        return "email", query
    if query.startswith('@') and len(query) > 1:
        return "telegram", query[1:]
    if re.match(r'^[А-Яа-я\s]{4,}$', query):
        return "fio", query
    if query_clean.isdigit() and len(query_clean) >= 10:
        phone_clean = query_clean
        if phone_clean.startswith('8'):
            phone_clean = '7' + phone_clean[1:]
        elif len(phone_clean) == 10:
            phone_clean = '7' + phone_clean
        return "phone", phone_clean
    return "text", query


def search_infinity(query, query_type, clean_query):
    try:
        params = {"token": INFINITY_TOKEN}
        if query_type == "email":
            params["email"] = clean_query
        elif query_type == "phone":
            params["phone"] = clean_query
        elif query_type == "fio":
            params["fio"] = clean_query
        else:
            params["nick"] = clean_query

        response = requests.get(INFINITY_API_URL, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get("results"):
                return data["results"]
        return None
    except Exception as e:
        print(f"Infinity error: {e}")
        return None


def search_depsearch(query):
    try:
        headers = {"Authorization": f"Bearer {DEPSEARCH_TOKEN}"}
        params = {"q": query}
        response = requests.get(DEPSEARCH_API_URL, headers=headers, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and data.get("results"):
                return data["results"]
            elif isinstance(data, dict):
                return [data]
        return None
    except Exception as e:
        print(f"Depsearch error: {e}")
        return None


def search_bigbase(query):
    try:
        headers = {"Authorization": BIGBASE_TOKEN, "Content-Type": "application/json"}
        payload = {"search": query}
        response = requests.post(BIGBASE_URL, headers=headers, json=payload, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and data.get("data"):
                return data["data"]
            elif isinstance(data, dict) and data.get("results"):
                return data["results"]
        return None
    except Exception as e:
        print(f"Bigbase error: {e}")
        return None


def format_result(item):
    if not isinstance(item, dict):
        return f"📄 {clean_text(str(item))}\n"

    lines = []
    lines.append("┌" + "─" * 40 + "┐")

    # ФИО
    fio = None
    for key in ['fio', 'full_name', 'fullname', 'name', 'ФИО']:
        if item.get(key) and str(item.get(key)).strip():
            fio = clean_text(str(item[key]))
            break
    if not fio and item.get('last_name'):
        name_parts = []
        if item.get('last_name'):
            name_parts.append(item.get('last_name'))
        if item.get('first_name'):
            name_parts.append(item.get('first_name'))
        if name_parts:
            fio = ' '.join(name_parts)

    if fio:
        lines.append(f"│ 👤 ФИО: {fio}")

    # Телефон
    for key in ['phone', 'phone_number', 'phones', 'mobile', 'Телефон', 'number']:
        if item.get(key):
            val = item[key]
            if isinstance(val, list):
                val = ', '.join([str(v) for v in val if v])
            if str(val).strip():
                lines.append(f"│ 📞 Телефон: {clean_text(str(val))}")
            break

    # Email
    for key in ['email', 'emails', 'mail', 'Email']:
        if item.get(key):
            val = item[key]
            if isinstance(val, list):
                val = ', '.join([str(v) for v in val if v])
            if str(val).strip():
                lines.append(f"│ 📧 Email: {clean_text(str(val))}")
            break

    # Адрес
    for key in ['address', 'addresses', 'location', 'city', 'Адрес']:
        if item.get(key) and str(item.get(key)).strip():
            lines.append(f"│ 📍 Адрес: {clean_text(str(item[key]))}")
            break

    # Дата рождения
    for key in ['bdate', 'birth_date', 'birthday', 'date_of_birth']:
        if item.get(key) and str(item.get(key)).strip():
            lines.append(f"│ 🎂 Дата рождения: {clean_text(str(item[key]))}")
            break

    # ИНН, Паспорт
    if item.get('inn') and str(item.get('inn')).strip():
        lines.append(f"│ 🆔 ИНН: {clean_text(str(item['inn']))}")
    if item.get('passport') and str(item.get('passport')).strip():
        lines.append(f"│ 🛂 Паспорт: {clean_text(str(item['passport']))}")

    # Оператор
    if item.get('operator') and str(item.get('operator')).strip():
        lines.append(f"│ 📡 Оператор: {clean_text(str(item['operator']))}")

    if len(lines) == 1:
        lines.append(f"│ 📄 {clean_text(str(item))}")

    lines.append("└" + "─" * 40 + "┘")
    return "\n".join(lines)


search_cache = {}


async def process_request(app, request):
    print(f"🔥 Обработка: {request['query']}")

    from database.balance_db import user_balance

    try:
        query = request['query']
        query_type, clean_query = detect_query_type(query)
        all_results = []

        await app.bot.send_message(
            chat_id=request['chat_id'],
            text=f"🔎 Поиск: {query}\n⏳ Подождите..."
        )

        # Infinity API
        result = search_infinity(query, query_type, clean_query)
        if result:
            all_results.extend(result)
            print(f"Infinity: {len(result)} результатов")

        # DepSearch API
        result = search_depsearch(query)
        if result:
            all_results.extend(result)
            print(f"DepSearch: {len(result)} результатов")

        # BigBase API
        result = search_bigbase(query)
        if result:
            all_results.extend(result)
            print(f"BigBase: {len(result)} результатов")

        # Убираем дубликаты
        unique = []
        seen = set()
        for item in all_results:
            if isinstance(item, dict):
                key = f"{item.get('fio', '')}{item.get('phone', '')}{item.get('email', '')}"
                if key not in seen:
                    seen.add(key)
                    unique.append(item)
            else:
                unique.append(item)

        remaining = user_balance.get_balance(request['user_id'])

        if unique:
            cache_key = f"search_{request['user_id']}"
            search_cache[cache_key] = {
                'results': unique,
                'query': query,
                'current_page': 0,
                'total_pages': len(unique),
                'remaining': remaining,
                'username': request['username']
            }

            output = f"🔍 РЕЗУЛЬТАТЫ ПОИСКА\n"
            output += f"📝 Запрос: {query}\n"
            output += "=" * 45 + "\n\n"
            output += format_result(unique[0])
            output += f"\n\n📊 Результат: 1 из {len(unique)}"
            output += f"\n💰 Осталось запросов: {remaining}"

            keyboard = []
            if len(unique) > 1:
                keyboard.append([
                    InlineKeyboardButton("◀️", callback_data=f"search_page_{request['user_id']}_prev"),
                    InlineKeyboardButton(f"1/{len(unique)}", callback_data="info"),
                    InlineKeyboardButton("▶️", callback_data=f"search_page_{request['user_id']}_next")
                ])
            keyboard.append([InlineKeyboardButton("❌ Закрыть", callback_data=f"search_close_{request['user_id']}")])

            await app.bot.send_message(
                chat_id=request['chat_id'],
                text=output,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            # Возвращаем запрос
            user_balance.add_requests(request['user_id'], request['username'], 1)
            remaining = user_balance.get_balance(request['user_id'])

            await app.bot.send_message(
                chat_id=request['chat_id'],
                text=f"❌ НИЧЕГО НЕ НАЙДЕНО\n\n📝 Запрос: {query}\n💰 Запрос возвращен. Осталось: {remaining}"
            )

    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()

        user_balance.add_requests(request['user_id'], request['username'], 1)
        remaining = user_balance.get_balance(request['user_id'])

        await app.bot.send_message(
            chat_id=request['chat_id'],
            text=f"❌ ОШИБКА: {str(e)[:100]}\n\n💰 Запрос возвращен. Осталось: {remaining}"
        )