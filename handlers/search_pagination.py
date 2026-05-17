# -*- coding: utf-8 -*-

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from handlers.process_handler import search_cache, format_result


async def search_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("_")
    user_id = int(data[2])
    action = data[3]

    cache_key = f"search_{user_id}"
    if cache_key not in search_cache:
        await query.edit_message_text("❌ Результаты устарели. Повторите поиск.")
        return

    cache_data = search_cache[cache_key]
    results = cache_data['results']
    query_text = cache_data['query']
    current_page = cache_data['current_page']
    total_pages = cache_data['total_pages']
    remaining = cache_data['remaining']

    if action == "next" and current_page + 1 < total_pages:
        current_page += 1
    elif action == "prev" and current_page > 0:
        current_page -= 1
    else:
        return

    cache_data['current_page'] = current_page
    search_cache[cache_key] = cache_data

    output = f"🔍 РЕЗУЛЬТАТЫ ПОИСКА\n"
    output += f"📝 Запрос: {query_text}\n"
    output += "=" * 45 + "\n\n"
    output += format_result(results[current_page])
    output += f"\n\n📊 Результат: {current_page + 1} из {total_pages}"
    output += f"\n💰 Осталось запросов: {remaining}"

    keyboard = []
    if total_pages > 1:
        nav_buttons = [
            InlineKeyboardButton("◀️", callback_data=f"search_page_{user_id}_prev"),
            InlineKeyboardButton(f"{current_page + 1}/{total_pages}", callback_data="info"),
            InlineKeyboardButton("▶️", callback_data=f"search_page_{user_id}_next")
        ]
        keyboard.append(nav_buttons)
    keyboard.append([InlineKeyboardButton("❌ Закрыть", callback_data=f"search_close_{user_id}")])

    await query.edit_message_text(
        text=output,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def search_close_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.delete_message()

    data = query.data.split("_")
    user_id = int(data[2])
    cache_key = f"search_{user_id}"
    if cache_key in search_cache:
        del search_cache[cache_key]