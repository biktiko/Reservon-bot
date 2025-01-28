# utils/session.py
from utils.localization import DEFAULT_LANGUAGE

user_session = {}

def get_user_language(user_id):
    return user_session.get(user_id, {}).get("lang", DEFAULT_LANGUAGE)

def set_user_language(user_id, lang_code):
    user_session.setdefault(user_id, {})
    user_session[user_id]["lang"] = lang_code

def get_session(user_id):
    return user_session.setdefault(user_id, {})
