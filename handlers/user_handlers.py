# -*- coding: utf-8 -*-

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes

from database.balance_db import user_balance
from database.users_db import users_db
from utils.helpers import is_admin
from utils.queue_system import request_queue


def safe_username(username):
    if username is None:
        return "no_username"
    return username


def get_main_menu(username):
    keyboard = [
        [KeyboardButton("🔍 Поиск")],
        [KeyboardButton("👤 Профиль")],
    ]
    if is_admin(username):
        keyboard.append([KeyboardButton("👑 Админ панель")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_profile_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 Моя статистика", callback_data="profile_stats")],
        [InlineKeyboardButton("📜 История поисков", callback_data="profile_history")],
        [InlineKeyboardButton("💰 Остаток запросов", callback_data="profile_balance")],
        [InlineKeyboardButton("🛒 Покупка запросов", callback_data="profile_buy")],
        [InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = safe_username(update.effective_user.username)
    first_name = update.effective_user.first_name
    last_name = update.effective_user.last_name

    users_db.add_user(user_id, username, first_name, last_name)
    user_balance.ensure_user(user_id, username, first_name, last_name)
    balance = user_balance.get_balance(user_id)

    text = f"🔍 meskatov search\n\n"
    text += f"👤 Добро пожаловать, @{username}!\n"
    text += f"💰 Осталось запросов: {balance}\n\n"
    text += "📌 Используйте кнопки меню для навигации.\n"
    text += "💡 Отправьте номер телефона, ФИО или Email для поиска."

    reply_markup = get_main_menu(username)
    await update.message.reply_text(text, reply_markup=reply_markup)


async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔎 Введите запрос для поиска:\n\n"
        "📝 Примеры:\n"
        "• Номер: 79149381129\n"
        "• ФИО: Иванов Иван\n"
        "• Email: test@mail.ru"
    )


async def handle_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Если ожидаем ввод username для добавления админа - не обрабатываем как поиск
    if context.user_data.get('awaiting_admin_username'):
        return

    query = update.message.text.strip()

    if query.startswith('/'):
        return
    if query in ["🔍 Поиск", "👤 Профиль", "👑 Админ панель", "Поиск", "Профиль", "Админ панель"]:
        return

    user_id = update.effective_user.id
    username = safe_username(update.effective_user.username)
    first_name = update.effective_user.first_name
    last_name = update.effective_user.last_name
    chat_id = update.effective_chat.id

    users_db.add_user(user_id, username, first_name, last_name)
    user_balance.ensure_user(user_id, username, first_name, last_name)

    balance = user_balance.get_balance(user_id)
    if balance <= 0:
        await update.message.reply_text("❌ У вас закончились запросы. Обратитесь к администратору.")
        return

    # Уменьшаем баланс
    user_balance.use_request(user_id)

    # Добавляем запрос в очередь
    req_id, msg = request_queue.add_request(user_id, username, query, chat_id)
    if req_id:
        await update.message.reply_text(f"✅ {msg}")
    else:
        user_balance.add_requests(user_id, username, 1)
        await update.message.reply_text(f"❌ {msg}")


async def profile_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = safe_username(update.effective_user.username)

    data = user_balance.get_full_user_data(user_id)
    user_info = users_db.get_user_info(user_id)

    text = f"👤 ПРОФИЛЬ\n\n"
    text += f"🆔 ID: {user_id}\n"
    text += f"📛 Username: @{username}\n"
    if user_info:
        text += f"📅 Впервые: {user_info.get('first_seen', 'Неизвестно')}\n"
        text += f"🔍 Поисков: {user_info.get('total_searches', 0)}\n"
    text += f"💰 Доступно: {data.get('requests', 0)}\n"
    text += f"📦 Получено: {data.get('total_received', 0)}\n"
    text += f"📉 Использовано: {data.get('total_used', 0)}\n"

    reply_markup = get_profile_keyboard()
    await update.message.reply_text(text, reply_markup=reply_markup)


async def profile_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = user_balance.get_full_user_data(user_id)
    user_info = users_db.get_user_info(user_id)
    text = f"📊 СТАТИСТИКА\n\n🔍 Поисков: {user_info.get('total_searches', 0) if user_info else 0}\n💰 Доступно: {data.get('requests', 0)}\n📦 Получено: {data.get('total_received', 0)}\n📉 Использовано: {data.get('total_used', 0)}"
    await query.edit_message_text(text)


async def profile_history_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    searches = users_db.get_user_searches(user_id, 10)
    if not searches:
        await query.edit_message_text("📜 У вас пока нет истории поисков.")
        return
    text = "📜 ИСТОРИЯ ПОИСКОВ\n\n"
    for i, s in enumerate(searches[:10], 1):
        text += f"{i}. 🔍 {s['query']}\n   🕐 {s['date']}\n   📄 {s['result_preview'][:50]}\n\n"
    if len(text) > 4000:
        text = text[:4000] + "\n... (обрезано)"
    await query.edit_message_text(text)


async def profile_balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    balance = user_balance.get_balance(user_id)
    text = f"💰 ОСТАТОК ЗАПРОСОВ\n\n✅ У вас осталось: {balance} запросов"
    await query.edit_message_text(text)


async def profile_buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = "🛒 ПОКУПКА ЗАПРОСОВ\n\n💰 Купить запросы можно у @meskatov\n\n📋 ПРАЙС-ЛИСТ:\n• 50 запросов = 15 звезд\n• 100 запросов = 25 звезд\n• 250 запросов = 50 звезд\n• 500 запросов = 90 звезд\n\n⭐ Звезды - внутренняя валюта VK Coin"
    await query.edit_message_text(text)


async def back_to_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.delete_message()
    user_id = query.from_user.id
    username = safe_username(query.from_user.username)
    balance = user_balance.get_balance(user_id)
    text = f"🔍 meskatov search\n\n👤 @{username}\n💰 Осталось: {balance}\n\n📌 Используйте кнопки меню"
    reply_markup = get_main_menu(username)
    await context.bot.send_message(chat_id=query.message.chat_id, text=text, reply_markup=reply_markup)