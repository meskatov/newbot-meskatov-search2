#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import sys
import os
import json
import logging
import requests
import signal
from datetime import datetime

# Отключаем лишние логи
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("telegram").setLevel(logging.ERROR)
logging.getLogger("httpcore").setLevel(logging.ERROR)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from telegram.request import HTTPXRequest

from handlers.user_handlers import (
    start as user_start, search_handler, handle_search_query, profile_menu,
    profile_stats_callback, profile_history_callback, profile_balance_callback, profile_buy_callback,
    back_to_menu_callback
)
from handlers.admin_handlers import (
    admin_panel, admin_stats_callback, admin_history_callback, admin_archive_callback,
    admin_give_menu_callback, admin_requests_history_callback, admin_queue_menu_callback,
    admin_queue_stats_callback, admin_queue_list_callback, admin_queue_clear_callback,
    admin_broadcast_callback, admin_admins_menu_callback, admin_top_callback,
    admin_users_list_callback, admin_user_database_callback, admin_secret_info_callback,
    admin_back_callback, give_self_command, add_requests_command, add_admin_command,
    remove_admin_command, list_admins_command, broadcast_message, broadcast_confirm_callback,
    broadcast_cancel_callback, secret_admin, admin_punish_menu_callback,
    punish_remove5_callback, punish_remove10_callback, punish_remove25_callback,
    punish_remove50_callback, punish_clear_callback, punish_ban_callback,
    punish_unban_callback, punish_demote_callback, handle_add_admin_input,
    admin_add_menu_callback, add_role_callback, admin_remove_menu_callback,
    remove_admin_callback, admin_list_admins_callback, punish_add10_callback, punish_add50_callback
)
from handlers.search_pagination import search_page_callback, search_close_callback

# ================= НАСТРОЙКИ ПОДКЛЮЧЕНИЯ =================
REQUEST_KWARGS = {
    "connect_timeout": 60.0,
    "read_timeout": 60.0,
    "write_timeout": 60.0,
    "pool_timeout": 60.0,
}

custom_request = HTTPXRequest(**REQUEST_KWARGS)

# ================= ТОКЕН БОТА =================
TELEGRAM_TOKEN = "8653236048:AAGf5myZsJA7AoexDVVtCXQ5R6eMVltRrQE"

# ================= НАСТРОЙКИ ПРОВЕРКИ ПОДПИСКИ =================
REQUIRED_CHANNEL_LINK = "https://t.me/meskatov_search_info"
CHANNEL_CHAT_ID = "-1003947433117"
VERIFIED_USERS_FILE = "verified_users.json"


class VerificationDatabase:
    def __init__(self):
        self.verified_users = {}
        self.load_verified_users()

    def load_verified_users(self):
        if os.path.exists(VERIFIED_USERS_FILE):
            try:
                with open(VERIFIED_USERS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.verified_users = data.get('verified_users', {})
                    print(f"Загружено {len(self.verified_users)} подтвержденных пользователей")
            except:
                self.verified_users = {}
        else:
            self.verified_users = {}
            self.save_verified_users()

    def save_verified_users(self):
        try:
            with open(VERIFIED_USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    'verified_users': self.verified_users,
                    'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'total_count': len(self.verified_users)
                }, f, ensure_ascii=False, indent=2)
        except:
            pass

    def is_verified(self, user_id):
        user_id_str = str(user_id)
        if user_id_str in self.verified_users:
            return self.verified_users[user_id_str].get('verified', False)
        return False

    def add_verified_user(self, user_id, username=None):
        user_id_str = str(user_id)
        self.verified_users[user_id_str] = {
            'user_id': user_id,
            'username': username,
            'verified': True,
            'verified_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'last_check': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.save_verified_users()
        print(f"Пользователь {user_id} добавлен в базу верификации")
        return True


verification_db = VerificationDatabase()


async def check_subscription(user_id, username=None):
    try:
        if verification_db.is_verified(user_id):
            return True

        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getChatMember"
        params = {"chat_id": CHANNEL_CHAT_ID, "user_id": user_id}
        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                status = data.get("result", {}).get("status")
                if status in ["creator", "administrator", "member"]:
                    verification_db.add_verified_user(user_id, username)
                    return True
        return False
    except:
        return False


async def subscription_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "no_username"

    if await check_subscription(user_id, username):
        await user_start(update, context)
        return

    keyboard = [
        [InlineKeyboardButton("📢 Подписаться на канал", url=REQUIRED_CHANNEL_LINK)],
        [InlineKeyboardButton("✅ Проверить подписку", callback_data="check_subscription")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"🔒 Доступ к боту ограничен!\n\nДля использования бота подпишитесь на канал:\n👉 {REQUIRED_CHANNEL_LINK}\n\nПосле подписки нажмите Проверить подписку."
    await update.message.reply_text(text, reply_markup=reply_markup)


async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    username = query.from_user.username or "no_username"

    if await check_subscription(user_id, username):
        keyboard = [[InlineKeyboardButton("🔍 Перейти в бот", callback_data="go_to_bot")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "✅ Подписка подтверждена!\n\nТеперь у вас есть доступ к боту."
        await query.edit_message_text(text, reply_markup=reply_markup)
    else:
        keyboard = [
            [InlineKeyboardButton("📢 Подписаться на канал", url=REQUIRED_CHANNEL_LINK)],
            [InlineKeyboardButton("🔄 Проверить еще раз", callback_data="check_subscription")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "❌ Вы не подписаны на канал!\n\nПодпишитесь и нажмите Проверить еще раз."
        await query.edit_message_text(text, reply_markup=reply_markup)


async def go_to_bot_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.delete_message()
    await user_start(update, context)


async def post_init(app):
    from utils.queue_system import queue_processor
    asyncio.create_task(queue_processor(app))
    print("Обработчик очереди запущен")


async def shutdown(application):
    from utils.queue_system import request_queue
    print("Остановка бота...")
    await request_queue.shutdown()
    await application.stop()
    await application.shutdown()


def main():
    print("=" * 50)
    print("Бот meskatov search запускается...")
    print(f"Канал для подписки: {REQUIRED_CHANNEL_LINK}")
    print("=" * 50)

    if not os.path.exists("base_user"):
        os.makedirs("base_user")
        print("Создана папка base_user")

    try:
        app = Application.builder().token(TELEGRAM_TOKEN).request(custom_request).build()

        # Команды
        app.add_handler(CommandHandler("start", subscription_check))
        app.add_handler(CommandHandler("help", subscription_check))

        # Админ команды
        app.add_handler(CommandHandler("give_self", give_self_command))
        app.add_handler(CommandHandler("add_requests", add_requests_command))
        app.add_handler(CommandHandler("add_admin", add_admin_command))
        app.add_handler(CommandHandler("remove_admin", remove_admin_command))
        app.add_handler(CommandHandler("list_admins", list_admins_command))
        app.add_handler(CommandHandler("broadcast", broadcast_message))
        app.add_handler(CommandHandler("users", admin_users_list_callback))
        app.add_handler(CommandHandler("secret", secret_admin))

        # Кнопки меню
        app.add_handler(MessageHandler(filters.Regex("^(🔍 Поиск)$"), search_handler))
        app.add_handler(MessageHandler(filters.Regex("^(👤 Профиль)$"), profile_menu))
        app.add_handler(MessageHandler(filters.Regex("^(👑 Админ панель)$"), admin_panel))

        # Обработчик текста (поиск)
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search_query))

        # Callback обработчики подписки
        app.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="check_subscription"))
        app.add_handler(CallbackQueryHandler(go_to_bot_callback, pattern="go_to_bot"))

        # Профиль
        app.add_handler(CallbackQueryHandler(profile_stats_callback, pattern="profile_stats"))
        app.add_handler(CallbackQueryHandler(profile_history_callback, pattern="profile_history"))
        app.add_handler(CallbackQueryHandler(profile_balance_callback, pattern="profile_balance"))
        app.add_handler(CallbackQueryHandler(profile_buy_callback, pattern="profile_buy"))

        # Админ панель
        app.add_handler(CallbackQueryHandler(admin_stats_callback, pattern="admin_stats"))
        app.add_handler(CallbackQueryHandler(admin_history_callback, pattern="admin_history"))
        app.add_handler(CallbackQueryHandler(admin_archive_callback, pattern="admin_archive"))
        app.add_handler(CallbackQueryHandler(admin_give_menu_callback, pattern="admin_give_menu"))
        app.add_handler(CallbackQueryHandler(admin_requests_history_callback, pattern="admin_requests_history"))
        app.add_handler(CallbackQueryHandler(admin_queue_menu_callback, pattern="admin_queue_menu"))
        app.add_handler(CallbackQueryHandler(admin_queue_stats_callback, pattern="admin_queue_stats"))
        app.add_handler(CallbackQueryHandler(admin_queue_list_callback, pattern="admin_queue_list"))
        app.add_handler(CallbackQueryHandler(admin_queue_clear_callback, pattern="admin_queue_clear"))
        app.add_handler(CallbackQueryHandler(admin_broadcast_callback, pattern="admin_broadcast"))
        app.add_handler(CallbackQueryHandler(admin_admins_menu_callback, pattern="admin_admins_menu"))
        app.add_handler(CallbackQueryHandler(admin_top_callback, pattern="admin_top"))
        app.add_handler(CallbackQueryHandler(admin_users_list_callback, pattern="admin_users_list"))
        app.add_handler(CallbackQueryHandler(admin_user_database_callback, pattern="admin_user_database"))
        app.add_handler(CallbackQueryHandler(admin_secret_info_callback, pattern="admin_secret_info"))
        app.add_handler(CallbackQueryHandler(admin_back_callback, pattern="admin_back"))

        # Управление админами
        app.add_handler(CallbackQueryHandler(admin_add_menu_callback, pattern="admin_add_menu"))
        app.add_handler(CallbackQueryHandler(add_role_callback, pattern="add_role_"))
        app.add_handler(CallbackQueryHandler(admin_remove_menu_callback, pattern="admin_remove_menu"))
        app.add_handler(CallbackQueryHandler(remove_admin_callback, pattern="remove_admin_"))
        app.add_handler(CallbackQueryHandler(admin_list_admins_callback, pattern="admin_list_admins"))

        # Наказания
        app.add_handler(CallbackQueryHandler(admin_punish_menu_callback, pattern="punish_user_"))
        app.add_handler(CallbackQueryHandler(punish_remove5_callback, pattern="punish_remove5_"))
        app.add_handler(CallbackQueryHandler(punish_remove10_callback, pattern="punish_remove10_"))
        app.add_handler(CallbackQueryHandler(punish_remove25_callback, pattern="punish_remove25_"))
        app.add_handler(CallbackQueryHandler(punish_remove50_callback, pattern="punish_remove50_"))
        app.add_handler(CallbackQueryHandler(punish_clear_callback, pattern="punish_clear_"))
        app.add_handler(CallbackQueryHandler(punish_ban_callback, pattern="punish_ban_"))
        app.add_handler(CallbackQueryHandler(punish_unban_callback, pattern="punish_unban_"))
        app.add_handler(CallbackQueryHandler(punish_demote_callback, pattern="punish_demote_"))
        app.add_handler(CallbackQueryHandler(punish_add10_callback, pattern="punish_add10_"))
        app.add_handler(CallbackQueryHandler(punish_add50_callback, pattern="punish_add50_"))

        # Рассылка
        app.add_handler(CallbackQueryHandler(broadcast_confirm_callback, pattern="broadcast_confirm"))
        app.add_handler(CallbackQueryHandler(broadcast_cancel_callback, pattern="broadcast_cancel"))

        # Пагинация поиска
        app.add_handler(CallbackQueryHandler(search_page_callback, pattern="search_page_"))
        app.add_handler(CallbackQueryHandler(search_close_callback, pattern="search_close_"))

        # Назад в меню
        app.add_handler(CallbackQueryHandler(back_to_menu_callback, pattern="back_to_menu"))

        # Обработчик ввода для добавления админа (ДО обработчика текста!)
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_admin_input))

        # Запуск
        app.post_init = post_init

        # Обработка сигналов
        loop = asyncio.get_event_loop()
        for sig in [signal.SIGINT, signal.SIGTERM]:
            try:
                loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(app)))
            except NotImplementedError:
                pass

        print("Бот успешно запущен!")
        print("=" * 50)

        app.run_polling()

    except Exception as e:
        print(f"Ошибка при запуске: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()