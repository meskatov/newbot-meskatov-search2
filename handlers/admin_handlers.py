# -*- coding: utf-8 -*-

import json
import os
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database.balance_db import user_balance
from database.users_db import users_db
from database.archive_db import search_archive
from database.history_db import requests_history
from utils.queue_system import request_queue

# ================= ФАЙЛ ДЛЯ ХРАНЕНИЯ РОЛЕЙ =================
ROLES_FILE = "admin_roles.json"


class AdminRoles:
    def __init__(self):
        self.roles = {}
        self.load_roles()

    def load_roles(self):
        if os.path.exists(ROLES_FILE):
            try:
                with open(ROLES_FILE, 'r', encoding='utf-8') as f:
                    self.roles = json.load(f)
            except:
                self.roles = {}
        else:
            self.roles = {"meskatov": "master"}
            self.save_roles()

    def save_roles(self):
        try:
            with open(ROLES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.roles, f, ensure_ascii=False, indent=2)
        except:
            pass

    def get_role(self, username):
        if not username:
            return "user"
        return self.roles.get(username.lower(), "user")

    def set_role(self, username, role):
        username_lower = username.lower()
        if role not in ["master", "main_admin", "admin", "media", "user"]:
            return False
        if role == "master" and username_lower != "meskatov":
            return False
        self.roles[username_lower] = role
        self.save_roles()
        return True

    def remove_role(self, username):
        username_lower = username.lower()
        if username_lower in self.roles and username_lower != "meskatov":
            del self.roles[username_lower]
            self.save_roles()
            return True
        return False

    def get_all_admins(self):
        admins = []
        for username, role in self.roles.items():
            if role != "user":
                admins.append({"username": username, "role": role})
        return admins


admin_roles = AdminRoles()


def safe_username(username):
    if username is None:
        return "no_username"
    return username


def load_requests_log():
    REQUESTS_LOG_FILE = "requests_log.json"
    if os.path.exists(REQUESTS_LOG_FILE):
        try:
            with open(REQUESTS_LOG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"requests": [], "total_count": 0}


def has_permission(username, permission):
    role = admin_roles.get_role(username)
    permissions = {
        "master": ["all"],
        "main_admin": ["give_requests", "add_admin", "remove_admin", "broadcast", "punish", "queue", "stats", "top",
                       "users", "history", "archive"],
        "admin": ["give_requests", "users", "top", "admins_list", "queue", "stats", "history", "archive", "punish"],
        "media": ["give_requests", "queue", "stats", "history", "archive"]
    }
    if role == "master":
        return True
    if permission in permissions.get(role, []):
        return True
    return False


# ================= КНОПКИ =================
def get_admin_keyboard(username):
    role = admin_roles.get_role(username)
    keyboard = []

    row = []
    if has_permission(username, "stats"):
        row.append(InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"))
    if has_permission(username, "history"):
        row.append(InlineKeyboardButton("📜 История", callback_data="admin_history"))
    if row:
        keyboard.append(row)

    row = []
    if has_permission(username, "archive"):
        row.append(InlineKeyboardButton("🗄 Архив", callback_data="admin_archive"))
    if has_permission(username, "give_requests"):
        row.append(InlineKeyboardButton("📦 Выдать", callback_data="admin_give_menu"))
    if row:
        keyboard.append(row)

    row = []
    if has_permission(username, "queue"):
        row.append(InlineKeyboardButton("⏳ Очередь", callback_data="admin_queue_menu"))
    if has_permission(username, "broadcast"):
        row.append(InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast"))
    if row:
        keyboard.append(row)

    row = []
    if has_permission(username, "users"):
        row.append(InlineKeyboardButton("👥 Юзеры", callback_data="admin_users_list"))
    if has_permission(username, "top"):
        row.append(InlineKeyboardButton("🏆 Топ", callback_data="admin_top"))
    if row:
        keyboard.append(row)

    row = []
    if has_permission(username, "admins_list"):
        row.append(InlineKeyboardButton("👑 Админы", callback_data="admin_admins_menu"))
    if has_permission(username, "punish"):
        row.append(InlineKeyboardButton("⚖️ Наказания", callback_data="admin_punish_menu"))
    if row:
        keyboard.append(row)

    if role == "master":
        keyboard.append([InlineKeyboardButton("💾 База", callback_data="admin_user_database"),
                         InlineKeyboardButton("🔐 Секрет", callback_data="admin_secret_info")])

    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(keyboard)


def get_queue_keyboard(username):
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_queue_stats"),
         InlineKeyboardButton("📋 Список", callback_data="admin_queue_list")]
    ]
    if has_permission(username, "queue"):
        keyboard.append([InlineKeyboardButton("🗑 Очистить", callback_data="admin_queue_clear")])
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="admin_back")])
    return InlineKeyboardMarkup(keyboard)


def get_admins_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ Добавить админа", callback_data="admin_add_menu")],
        [InlineKeyboardButton("➖ Удалить админа", callback_data="admin_remove_menu")],
        [InlineKeyboardButton("📋 Список админов", callback_data="admin_list_admins")],
        [InlineKeyboardButton("◀️ Назад", callback_data="admin_back")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_add_admin_keyboard():
    keyboard = [
        [InlineKeyboardButton("⭐ Главный админ", callback_data="add_role_main_admin")],
        [InlineKeyboardButton("🔹 Админ", callback_data="add_role_admin")],
        [InlineKeyboardButton("📺 Медийка", callback_data="add_role_media")],
        [InlineKeyboardButton("◀️ Назад", callback_data="admin_admins_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_remove_admin_keyboard():
    admins = admin_roles.get_all_admins()
    keyboard = []
    for admin in admins:
        if admin["username"] != "meskatov":
            role_names = {"main_admin": "Главный админ", "admin": "Админ", "media": "Медийка"}
            role_text = role_names.get(admin["role"], admin["role"])
            keyboard.append([InlineKeyboardButton(f"❌ @{admin['username']} ({role_text})",
                                                  callback_data=f"remove_admin_{admin['username']}")])
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="admin_admins_menu")])
    return InlineKeyboardMarkup(keyboard)


def get_punish_keyboard(user_id, username):
    keyboard = [
        [InlineKeyboardButton("📉 Снять 5 запросов", callback_data=f"punish_remove5_{user_id}")],
        [InlineKeyboardButton("📉 Снять 10 запросов", callback_data=f"punish_remove10_{user_id}")],
        [InlineKeyboardButton("📉 Снять 25 запросов", callback_data=f"punish_remove25_{user_id}")],
        [InlineKeyboardButton("📉 Снять 50 запросов", callback_data=f"punish_remove50_{user_id}")],
        [InlineKeyboardButton("🗑 Обнулить всё", callback_data=f"punish_clear_{user_id}")],
        [InlineKeyboardButton("🔨 Бан", callback_data=f"punish_ban_{user_id}")],
        [InlineKeyboardButton("🔓 Разбан", callback_data=f"punish_unban_{user_id}")],
        [InlineKeyboardButton("👑 Разжаловать", callback_data=f"punish_demote_{user_id}")],
        [InlineKeyboardButton("➕ Выдать 10 запросов", callback_data=f"punish_add10_{user_id}")],
        [InlineKeyboardButton("➕ Выдать 50 запросов", callback_data=f"punish_add50_{user_id}")],
        [InlineKeyboardButton("◀️ Назад", callback_data="admin_users_list")]
    ]
    return InlineKeyboardMarkup(keyboard)


# ================= ОСНОВНАЯ АДМИН ПАНЕЛЬ =================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_username = safe_username(update.effective_user.username)
    role = admin_roles.get_role(user_username)

    if role == "user":
        await update.message.reply_text("⛔ Доступ запрещен.")
        return

    log = load_requests_log()
    users_count = len(user_balance.balances)
    total_given = sum(d.get('total_received', 0) for d in user_balance.balances.values())
    total_used = sum(d.get('total_used', 0) for d in user_balance.balances.values())
    total_users_db, total_searches_db = users_db.get_stats()

    role_names = {"master": "👑 МАСТЕР-АДМИН", "main_admin": "⭐ ГЛАВНЫЙ АДМИН", "admin": "🔹 АДМИН", "media": "📺 МЕДИЙКА"}

    text = f"{role_names.get(role, 'АДМИН ПАНЕЛЬ')}\n\n"
    text += f"📊 Всего запросов: {log['total_count']}\n"
    text += f"👥 Пользователей: {users_count}\n"
    text += f"🔍 Поисков: {total_searches_db}\n"
    text += f"📦 Выдано: {total_given}\n"
    text += f"📉 Использовано: {total_used}\n"
    text += f"✅ Осталось: {total_given - total_used}\n"
    text += f"⏳ Очередь: {request_queue.get_queue_stats()['waiting']}\n"
    text += f"⚙️ В работе: {request_queue.get_queue_stats()['processing']}"

    await update.message.reply_text(text, reply_markup=get_admin_keyboard(user_username))


# ================= УПРАВЛЕНИЕ АДМИНАМИ =================
async def admin_admins_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_username = safe_username(query.from_user.username)
    if admin_roles.get_role(user_username) not in ["master", "main_admin"]:
        await query.edit_message_text("⛔ У вас нет прав.")
        return

    await query.edit_message_text("👑 УПРАВЛЕНИЕ АДМИНАМИ", reply_markup=get_admins_menu_keyboard())


async def admin_add_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_username = safe_username(query.from_user.username)
    if admin_roles.get_role(user_username) not in ["master", "main_admin"]:
        await query.edit_message_text("⛔ Нет прав.")
        return

    await query.edit_message_text("➕ ДОБАВЛЕНИЕ АДМИНА\n\nВыберите роль:", reply_markup=get_add_admin_keyboard())


async def add_role_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_username = safe_username(query.from_user.username)
    if admin_roles.get_role(user_username) not in ["master", "main_admin"]:
        await query.edit_message_text("⛔ Нет прав.")
        return

    role_map = {
        "add_role_main_admin": "main_admin",
        "add_role_admin": "admin",
        "add_role_media": "media"
    }
    context.user_data['pending_role'] = role_map.get(query.data)
    context.user_data['awaiting_admin_username'] = True
    await query.edit_message_text("Введите @username пользователя:")


async def admin_remove_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_username = safe_username(query.from_user.username)
    if admin_roles.get_role(user_username) not in ["master", "main_admin"]:
        await query.edit_message_text("⛔ Нет прав.")
        return

    await query.edit_message_text("➖ УДАЛЕНИЕ АДМИНА", reply_markup=get_remove_admin_keyboard())


async def remove_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_username = safe_username(query.from_user.username)
    if admin_roles.get_role(user_username) not in ["master", "main_admin"]:
        await query.edit_message_text("⛔ Нет прав.")
        return

    admin_to_remove = query.data.replace("remove_admin_", "")

    if admin_to_remove == "meskatov":
        await query.edit_message_text("❌ Нельзя удалить мастер-админа!")
        return

    if admin_roles.remove_role(admin_to_remove):
        await query.edit_message_text(f"✅ Администратор @{admin_to_remove} удален.")
    else:
        await query.edit_message_text("❌ Ошибка.")


async def admin_list_admins_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    admins = admin_roles.get_all_admins()
    if not admins:
        await query.edit_message_text("Список пуст.")
        return

    role_names = {"master": "👑 МАСТЕР-АДМИН", "main_admin": "⭐ ГЛАВНЫЙ АДМИН", "admin": "🔹 АДМИН", "media": "📺 МЕДИЙКА"}
    text = "👑 СПИСОК АДМИНИСТРАТОРОВ\n\n"
    for admin in admins:
        text += f"{role_names.get(admin['role'], admin['role'])} @{admin['username']}\n"

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(
        [[InlineKeyboardButton("◀️ Назад", callback_data="admin_admins_menu")]]))


async def handle_add_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_admin_username'):
        return

    target = update.message.text.strip().replace("@", "").lower()
    pending_role = context.user_data.get('pending_role')

    if not pending_role:
        context.user_data['awaiting_admin_username'] = False
        return

    user_username = safe_username(update.effective_user.username)
    if admin_roles.get_role(user_username) not in ["master", "main_admin"]:
        await update.message.reply_text("⛔ Нет прав.")
        context.user_data['awaiting_admin_username'] = False
        return

    if admin_roles.set_role(target, pending_role):
        role_names = {"main_admin": "ГЛАВНЫЙ АДМИН", "admin": "АДМИН", "media": "МЕДИЙКА"}
        await update.message.reply_text(f"✅ @{target} назначен {role_names.get(pending_role, pending_role)}!")
    else:
        await update.message.reply_text("❌ Ошибка.")

    context.user_data['awaiting_admin_username'] = False
    context.user_data['pending_role'] = None


# ================= НАКАЗАНИЯ =================
async def admin_punish_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.data.split("_")[2]
    user_data = user_balance.get_full_user_data(int(user_id))
    username = user_data.get('username', 'unknown')

    text = f"⚖️ НАКАЗАНИЕ ПОЛЬЗОВАТЕЛЯ @{username}\n\n"
    text += f"🆔 ID: {user_id}\n"
    text += f"💰 Запросов: {user_data.get('requests', 0)}\n"
    text += f"👑 Роль: {admin_roles.get_role(username)}\n\n"
    text += "Выберите действие:"

    await query.edit_message_text(text, reply_markup=get_punish_keyboard(user_id, username))


async def punish_remove5_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = int(query.data.split("_")[2])

    old = user_balance.get_balance(user_id)
    new = max(0, old - 5)
    user_balance.balances[str(user_id)]['requests'] = new
    user_balance.save_balances()

    await query.edit_message_text(f"✅ Снято 5 запросов.\n📊 Было: {old} → Стало: {new}")


async def punish_remove10_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = int(query.data.split("_")[2])

    old = user_balance.get_balance(user_id)
    new = max(0, old - 10)
    user_balance.balances[str(user_id)]['requests'] = new
    user_balance.save_balances()

    await query.edit_message_text(f"✅ Снято 10 запросов.\n📊 Было: {old} → Стало: {new}")


async def punish_remove25_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = int(query.data.split("_")[2])

    old = user_balance.get_balance(user_id)
    new = max(0, old - 25)
    user_balance.balances[str(user_id)]['requests'] = new
    user_balance.save_balances()

    await query.edit_message_text(f"✅ Снято 25 запросов.\n📊 Было: {old} → Стало: {new}")


async def punish_remove50_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = int(query.data.split("_")[2])

    old = user_balance.get_balance(user_id)
    new = max(0, old - 50)
    user_balance.balances[str(user_id)]['requests'] = new
    user_balance.save_balances()

    await query.edit_message_text(f"✅ Снято 50 запросов.\n📊 Было: {old} → Стало: {new}")


async def punish_add10_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = int(query.data.split("_")[2])

    old = user_balance.get_balance(user_id)
    user_data = user_balance.get_full_user_data(user_id)
    new = user_balance.add_requests(user_id, user_data.get('username'), 10)

    await query.edit_message_text(f"✅ Добавлено 10 запросов.\n📊 Было: {old} → Стало: {new}")


async def punish_add50_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = int(query.data.split("_")[2])

    old = user_balance.get_balance(user_id)
    user_data = user_balance.get_full_user_data(user_id)
    new = user_balance.add_requests(user_id, user_data.get('username'), 50)

    await query.edit_message_text(f"✅ Добавлено 50 запросов.\n📊 Было: {old} → Стало: {new}")


async def punish_clear_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = int(query.data.split("_")[2])

    user_balance.balances[str(user_id)]['requests'] = 0
    user_balance.save_balances()

    await query.edit_message_text(f"✅ Все запросы обнулены.")


async def punish_ban_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = int(query.data.split("_")[2])

    user_balance.balances[str(user_id)]['requests'] = 0
    user_balance.balances[str(user_id)]['banned'] = True
    user_balance.save_balances()

    await query.edit_message_text(f"🔨 Пользователь забанен.")


async def punish_unban_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = int(query.data.split("_")[2])

    if 'banned' in user_balance.balances[str(user_id)]:
        del user_balance.balances[str(user_id)]['banned']
        user_balance.save_balances()

    await query.edit_message_text(f"🔓 Пользователь разбанен.")


async def punish_demote_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = int(query.data.split("_")[2])

    user_data = user_balance.get_full_user_data(user_id)
    username = user_data.get('username')

    if username and admin_roles.remove_role(username):
        await query.edit_message_text(f"👑 Пользователь @{username} разжалован.")
    else:
        await query.edit_message_text(f"⚠️ Пользователь не админ.")


# ================= СТАТИСТИКА, ИСТОРИЯ, АРХИВ =================
async def admin_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    log = load_requests_log()
    users_count = len(user_balance.balances)
    total_given = sum(d.get('total_received', 0) for d in user_balance.balances.values())
    total_used = sum(d.get('total_used', 0) for d in user_balance.balances.values())
    total_users_db, total_searches_db = users_db.get_stats()

    text = f"📊 СТАТИСТИКА БОТА\n\n📝 Запросов: {log['total_count']}\n👥 Пользователей: {users_count}\n🔍 Поисков: {total_searches_db}\n📦 Выдано: {total_given}\n📉 Использовано: {total_used}\n✅ Осталось: {total_given - total_used}\n⏳ Очередь: {request_queue.get_queue_stats()['waiting']}"
    await query.edit_message_text(text)


async def admin_history_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    log = load_requests_log()
    if not log['requests']:
        await query.edit_message_text("📜 История пуста")
        return
    text = "📜 ПОСЛЕДНИЕ 20 ЗАПРОСОВ\n\n"
    for req in log['requests'][-20:]:
        text += f"👤 @{req['username']}: {req['query']}\n🕐 {req['timestamp']}\n\n"
    await query.edit_message_text(text[:4000])


async def admin_archive_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    all_searches = search_archive.get_all_searches(30)
    if not all_searches:
        await query.edit_message_text("🗄 Архив пуст")
        return
    text = "🗄 АРХИВ ПОИСКОВ\n\n"
    for i, s in enumerate(all_searches[:30], 1):
        text += f"{i}. @{s['username']}: {s['query'][:50]}\n"
    await query.edit_message_text(text[:4000])


async def admin_give_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = "📦 ВЫДАЧА ЗАПРОСОВ\n\n/give_self <количество>\n/add_requests @username <количество>\n/add_requests <ID> <количество>"
    await query.edit_message_text(text)


async def admin_requests_history_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = "📋 ИСТОРИЯ ВЫДАЧ\n\nФункция в разработке"
    await query.edit_message_text(text)


async def admin_queue_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_username = safe_username(query.from_user.username)
    await query.edit_message_text("⏳ УПРАВЛЕНИЕ ОЧЕРЕДЬЮ", reply_markup=get_queue_keyboard(user_username))


async def admin_queue_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    stats = request_queue.get_queue_stats()
    text = f"📊 СТАТИСТИКА ОЧЕРЕДИ\n\n⏳ В очереди: {stats['waiting']}\n⚙️ В обработке: {stats['processing']}"
    await query.edit_message_text(text)


async def admin_queue_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    qlist = request_queue.get_queue_list(20)
    text = "📋 ЗАПРОСЫ В ОЧЕРЕДИ\n\n" + ("\n".join(qlist) if qlist else "Очередь пуста")
    await query.edit_message_text(text)


async def admin_queue_clear_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not has_permission(safe_username(query.from_user.username), "queue"):
        await query.edit_message_text("⛔ Нет прав")
        return
    count = request_queue.clear_queue()
    await query.edit_message_text(f"✅ Очищено {count} запросов")


async def admin_broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("📢 РАССЫЛКА\n\n/broadcast <текст>")


async def admin_top_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    top_users = user_balance.get_top_users(15)
    if not top_users:
        await query.edit_message_text("🏆 Нет данных")
        return
    text = "🏆 ТОП-15\n\n"
    for i, u in enumerate(top_users, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        text += f"{medal} @{u['username']}: {u['total_used']} поисков\n"
    await query.edit_message_text(text)


async def admin_users_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    users = user_balance.get_all_users()
    if not users:
        await query.edit_message_text("👥 Список пуст")
        return
    text = "👥 ПОЛЬЗОВАТЕЛИ\n\n"
    keyboard = []
    for uid_str, data in list(users.items())[:25]:
        username = data.get('username', 'unknown')
        requests_left = data.get('requests', 0)
        text += f"🆔 {uid_str} | @{username}: {requests_left} запросов\n"
        if has_permission(safe_username(query.from_user.username), "punish"):
            keyboard.append([InlineKeyboardButton(f"⚖️ Наказать @{username}", callback_data=f"punish_user_{uid_str}")])
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="admin_back")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def admin_user_database_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if admin_roles.get_role(safe_username(query.from_user.username)) != "master":
        await query.edit_message_text("⛔ Только мастер-админ")
        return
    users = users_db.get_all_users()
    text = f"💾 БАЗА ДАННЫХ\n\nВсего: {len(users)} пользователей"
    await query.edit_message_text(text)


async def admin_secret_info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if admin_roles.get_role(safe_username(query.from_user.username)) != "master":
        await query.edit_message_text("⛔ Только мастер-админ")
        return
    await query.edit_message_text("🔐 СЕКРЕТНАЯ ПАНЕЛЬ\n\n/secret <пароль>")


async def admin_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await admin_panel(update, context)


# ================= КОМАНДЫ =================
async def give_self_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_username = safe_username(update.effective_user.username)
    if not has_permission(user_username, "give_requests"):
        await update.message.reply_text("⛔ Доступ запрещен.")
        return
    if not context.args:
        await update.message.reply_text("📝 /give_self <количество>")
        return
    try:
        amount = int(context.args[0])
        user_id = update.effective_user.id
        username = safe_username(update.effective_user.username)
        new_balance = user_balance.add_requests(user_id, username, amount)
        await update.message.reply_text(f"✅ Выдано {amount} запросов. Стало: {new_balance}")
    except:
        await update.message.reply_text("❌ Ошибка")


async def add_requests_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_username = safe_username(update.effective_user.username)
    if not has_permission(user_username, "give_requests"):
        await update.message.reply_text("⛔ Доступ запрещен.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("📝 /add_requests @username <количество>")
        return
    target = context.args[0]
    try:
        amount = int(context.args[1])
    except:
        await update.message.reply_text("❌ Ошибка")
        return
    target_id = None
    if target.startswith('@'):
        target_username = target[1:].lower()
        target_id = user_balance.find_user_by_username(target_username)
    else:
        try:
            target_id = int(target)
        except:
            await update.message.reply_text("❌ Неверный формат")
            return
    if not target_id:
        await update.message.reply_text(f"⚠️ Пользователь не найден")
        return
    user_data = user_balance.get_full_user_data(target_id)
    old_balance = user_balance.get_balance(target_id)
    new_balance = user_balance.add_requests(target_id, user_data.get('username'), amount)
    await update.message.reply_text(
        f"✅ Выдано {amount} запросов @{user_data.get('username')}\n📊 {old_balance} → {new_balance}")


async def add_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_username = safe_username(update.effective_user.username)
    if admin_roles.get_role(user_username) not in ["master", "main_admin"]:
        await update.message.reply_text("⛔ Нет прав")
        return
    if len(context.args) < 2:
        await update.message.reply_text("📝 /add_admin @username main_admin/admin/media")
        return
    target = context.args[0].replace("@", "").lower()
    role = context.args[1].lower()
    if role not in ["main_admin", "admin", "media"]:
        await update.message.reply_text("❌ Роль: main_admin, admin, media")
        return
    if admin_roles.set_role(target, role):
        role_names = {"main_admin": "ГЛАВНЫЙ АДМИН", "admin": "АДМИН", "media": "МЕДИЙКА"}
        await update.message.reply_text(f"✅ @{target} назначен {role_names.get(role)}")
    else:
        await update.message.reply_text("❌ Ошибка")


async def remove_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_username = safe_username(update.effective_user.username)
    if admin_roles.get_role(user_username) not in ["master", "main_admin"]:
        await update.message.reply_text("⛔ Нет прав")
        return
    if not context.args:
        await update.message.reply_text("📝 /remove_admin @username")
        return
    target = context.args[0].replace("@", "").lower()
    if target == "meskatov":
        await update.message.reply_text("❌ Нельзя удалить мастер-админа")
        return
    if admin_roles.remove_role(target):
        await update.message.reply_text(f"✅ @{target} удален")
    else:
        await update.message.reply_text("❌ Ошибка")


async def list_admins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admins = admin_roles.get_all_admins()
    if not admins:
        await update.message.reply_text("Список пуст")
        return
    role_names = {"master": "👑", "main_admin": "⭐", "admin": "🔹", "media": "📺"}
    text = "👑 АДМИНИСТРАТОРЫ\n\n"
    for a in admins:
        text += f"{role_names.get(a['role'], '')} @{a['username']}\n"
    await update.message.reply_text(text)


async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_username = safe_username(update.effective_user.username)
    if not has_permission(user_username, "broadcast"):
        await update.message.reply_text("⛔ Доступ запрещен")
        return
    if not context.args:
        await update.message.reply_text("📝 /broadcast <текст>")
        return
    message = ' '.join(context.args)
    keyboard = [[InlineKeyboardButton("✅ ДА", callback_data="broadcast_confirm"),
                 InlineKeyboardButton("❌ НЕТ", callback_data="broadcast_cancel")]]
    await update.message.reply_text(f"⚠️ Отправить всем?\n\n{message}\n\n👥 {len(user_balance.balances)} пользователей",
                                    reply_markup=InlineKeyboardMarkup(keyboard))
    context.user_data['broadcast_message'] = message


async def broadcast_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    message = context.user_data.get('broadcast_message', '')
    if not message:
        await query.edit_message_text("❌ Нет сообщения")
        return
    await query.edit_message_text("📤 Рассылка...")
    sent = 0
    for user_id_str in user_balance.balances:
        try:
            await context.bot.send_message(chat_id=int(user_id_str), text=f"📢 РАССЫЛКА\n\n{message}")
            sent += 1
            await asyncio.sleep(0.05)
        except:
            pass
    await query.edit_message_text(f"✅ Отправлено: {sent}")


async def broadcast_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Отменено")


async def secret_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_username = safe_username(update.effective_user.username)
    if admin_roles.get_role(user_username) != "master":
        await update.message.reply_text("⛔ Только мастер-админ")
        return
    from utils.helpers import SECRET_ADMIN_PASSWORD
    if not context.args or context.args[0] != SECRET_ADMIN_PASSWORD:
        await update.message.reply_text(f"🔐 Пароль: {SECRET_ADMIN_PASSWORD}")
        return
    log = load_requests_log()
    text = f"🔓 СЕКРЕТНАЯ ПАНЕЛЬ\n\n📊 Всего запросов: {log['total_count']}\n👥 Пользователей: {len(user_balance.balances)}"
    await update.message.reply_text(text)