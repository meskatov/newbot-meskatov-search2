# -*- coding: utf-8 -*-

import json
import os

ADMINS_FILE = "admins.json"
MASTER_ADMIN = "meskatov"
SECRET_ADMIN_PASSWORD = "meskatov_secret_2024"

def load_admins():
    if os.path.exists(ADMINS_FILE):
        try:
            with open(ADMINS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_admins(admins):
    try:
        with open(ADMINS_FILE, 'w', encoding='utf-8') as f:
            json.dump(admins, f, ensure_ascii=False, indent=2)
    except:
        pass

def is_admin(username):
    if not username:
        return False
    if username.lower() == MASTER_ADMIN.lower():
        return True
    admins = load_admins()
    return username.lower() in admins

def add_admin(username):
    if username.lower() == MASTER_ADMIN.lower():
        return False
    admins = load_admins()
    if username.lower() in admins:
        return False
    admins.append(username.lower())
    save_admins(admins)
    return True

def remove_admin(username):
    if username.lower() == MASTER_ADMIN.lower():
        return False
    admins = load_admins()
    if username.lower() in admins:
        admins.remove(username.lower())
        save_admins(admins)
        return True
    return False

def get_admins_list():
    admins = load_admins()
    if MASTER_ADMIN.lower() not in admins:
        admins.insert(0, MASTER_ADMIN.lower())
    return admins