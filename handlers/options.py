# handlers/options.py
from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from utils.localization import get_texts
from utils.session import get_user_language
# from utils.api import get_services, get_barbers

CHOOSING_OPTION = 2

# Обновляем основное меню с учётом языка
def get_main_menu_keyboard(lang_code):
    translations = {
        "ru": [["Забронировать услугу", "Просмотреть бронирования"], ["Изменить язык"]],
        "hy": [["Ամրագրել ծառայություն", "Տեսնել ամրագրումները"], ["Փոխել լեզուն"]],
        "en": [["Book a Service", "View Bookings"], ["Change Language"]]
    }
    buttons = translations.get(lang_code, translations["ru"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=False)

async def show_main_menu(update, context: CallbackContext):
    user_id = update.effective_user.id if update.effective_user else update.callback_query.from_user.id
    lang = get_user_language(user_id)
    texts = get_texts(lang)

    keyboard = get_main_menu_keyboard(lang)
    await update.effective_message.reply_text(
        texts["menu"],
        reply_markup=keyboard
    )
    return CHOOSING_OPTION

async def main_options_callback(update, context: CallbackContext):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    texts = get_texts(lang)
    message = update.message.text if update.message else update.callback_query.data

    if message in ["Book a Service", "Забронировать услугу", "Ամրագրել ծառայություն"]:
        from handlers.services import choose_services
        return await choose_services(update, context)

    elif message in ["View Bookings", "Просмотреть бронирования", "Տեսնել ամրագրումները"]:
        # Здесь можно добавить функционал для просмотра бронирований
        await update.effective_message.reply_text(texts["booking_done"], reply_markup=get_main_menu_keyboard(lang))
        return CHOOSING_OPTION

    elif message in ["Change Language", "Изменить язык", "Փոխել լեզուն"]:
        from handlers.language import LANGUAGE_KEYBOARD, get_texts
        await update.effective_message.reply_text(
            texts["language_prompt"],
            reply_markup=LANGUAGE_KEYBOARD
        )
        return 0  # CHOOSING_LANGUAGE

    else:
        await update.effective_message.reply_text("Пожалуйста, выберите доступную опцию.", reply_markup=get_main_menu_keyboard(lang))
        return CHOOSING_OPTION

async def show_main_options(query, context):
    """
    Show the 3 main options: choose services, barbers, date/time
    """
    user_id = query.from_user.id
    lang = get_user_language(user_id)
    texts = get_texts(lang)

    keyboard = [
        [
            InlineKeyboardButton(texts["option_services"], callback_data="opt_services"),
            InlineKeyboardButton(texts["option_barbers"], callback_data="opt_barbers")
        ],
        [
            InlineKeyboardButton(texts["option_date"], callback_data="opt_date")
        ]
    ]
    await query.message.reply_text(
        texts["ask_option"],
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CHOOSING_OPTION