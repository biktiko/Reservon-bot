import logging
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, 
    KeyboardButton
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
import requests

from dotenv import load_dotenv
import os

# Загрузка переменных окружения из .env файла
load_dotenv()

# Constants for conversation states
CHOOSING_LANGUAGE = 0
CHOOSING_SALON = 1
CHOOSING_OPTION = 2
CHOOSING_SERVICES = 3
CHOOSING_BARBERS = 4
CHOOSING_DATE = 5
CHOOSING_HOUR = 6
CHOOSING_MINUTES = 7
CONFIRMATION = 8

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# We'll keep user data in memory for simplicity. 
# For production, consider a database or redis.
user_session = {}

LANGUAGES = {
    "Русский": "ru",
    "Հայերեն": "hy",
    "English": "en"
}

DEFAULT_LANGUAGE = "ru"

def get_texts(lang_code):
    """
    Returns dictionary of localized strings.
    This is a simplified approach.
    """
    translations = {
        "ru": {
            "welcome": "Добро пожаловать в Reservon Bot!",
            "choose_language": "Выберите язык:",
            "language_set": "Язык установлен: Русский",
            "ask_salon": "Выберите салон:",
            "ask_option": "Что хотите сделать?",
            "option_services": "Выбрать услуги",
            "option_barbers": "Выбрать мастеров",
            "option_date": "Выбрать дату и время",
            "confirm_services": "Услуги выбраны. Подтвердить?",
            "confirm_barbers": "Мастера выбраны. Подтвердить?",
            "ask_date": "Выберите день (пример: 2025-01-12):",
            "ask_hour": "Выберите час (0-23):",
            "ask_minutes": "Выберите минуты (например, 05, 10, 15, ...):",
            "date_chosen": "Дата и время выбраны: ",
            "services_chosen": "Услуги выбраны: ",
            "barbers_chosen": "Мастера выбраны: ",
            "salon_chosen": "Салон выбран: ",
            "back_to_menu": "Вернуться в меню",
            "done": "Завершить",
            "final_confirmation": "Подтвердить бронирование?",
            "booking_done": "Бронирование успешно!",
            "language_prompt": "Пожалуйста, выберите язык:",
            "select_language_error": "Пожалуйста, выберите доступный язык."
        },
        "hy": {
            "welcome": "Բարի գալուստ Reservon Bot!",
            "choose_language": "Ընտրեք լեզուն:",
            "language_set": "Լեզուն ընտրված է: Հայերեն",
            "ask_salon": "Ընտրեք սալոնը:",
            "ask_option": "Ի՞նչ եք ուզում անել:",
            "option_services": "Ընտրել ծառայություններ",
            "option_barbers": "Ընտրել վարպետներ",
            "option_date": "Ընտրել ամսաթիվ եւ ժամ",
            "confirm_services": "Ծառայություններն ընտրված են: Հաստատե՞լ",
            "confirm_barbers": "Վարպետները ընտրված են: Հաստատե՞լ",
            "ask_date": "Ընտրեք օրը (օր. 2025-01-12):",
            "ask_hour": "Ընտրեք ժամը (0-23):",
            "ask_minutes": "Ընտրեք րոպեները (օր. 05, 10, 15, ...):",
            "date_chosen": "Ամսաթիվը եւ ժամը ընտրված են: ",
            "services_chosen": "Ծառայություններն ընտրված են: ",
            "barbers_chosen": "Վարպետներն ընտրված են: ",
            "salon_chosen": "Սալոնը ընտրված է: ",
            "back_to_menu": "Վերադառնալ մենյու",
            "done": "Ավարտել",
            "final_confirmation": "Հաստատե՞լ ամրագրումը",
            "booking_done": "Ամրագրումը հաջողվեց!",
            "language_prompt": "Խնդրում ենք ընտրել լեզուն:",
            "select_language_error": "Խնդրում ենք ընտրել հասանելի լեզուն:"
        },
        "en": {
            "welcome": "Welcome to Reservon Bot!",
            "choose_language": "Choose a language:",
            "language_set": "Language set: English",
            "ask_salon": "Choose a salon:",
            "ask_option": "What do you want to do?",
            "option_services": "Choose services",
            "option_barbers": "Choose barbers",
            "option_date": "Choose date & time",
            "confirm_services": "Services chosen. Confirm?",
            "confirm_barbers": "Barbers chosen. Confirm?",
            "ask_date": "Choose a day (e.g. 2025-01-12):",
            "ask_hour": "Choose hour (0-23):",
            "ask_minutes": "Choose minutes (e.g. 05, 10, 15, ...):",
            "date_chosen": "Date & time chosen: ",
            "services_chosen": "Services chosen: ",
            "barbers_chosen": "Barbers chosen: ",
            "salon_chosen": "Salon chosen: ",
            "back_to_menu": "Back to menu",
            "done": "Done",
            "final_confirmation": "Confirm booking?",
            "booking_done": "Booking successful!",
            "language_prompt": "Please select a language:",
            "select_language_error": "Please select a valid language."
        }
    }
    return translations.get(lang_code, translations[DEFAULT_LANGUAGE])

# Utility to get user language
def get_user_language(user_id):
    # default: "ru"
    return user_session.get(user_id, {}).get("lang", DEFAULT_LANGUAGE)

# Utility to set user language
def set_user_language(user_id, lang_code):
    user_session.setdefault(user_id, {})
    user_session[user_id]["lang"] = lang_code

# Define the language selection keyboard
LANGUAGE_BUTTONS = [
    [KeyboardButton("Русский"), KeyboardButton("Հայերեն"), KeyboardButton("English")]
]

LANGUAGE_KEYBOARD = ReplyKeyboardMarkup(
    LANGUAGE_BUTTONS, resize_keyboard=True, one_time_keyboard=False
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /start command handler
    """
    user_id = update.effective_user.id
    # Set default language or keep existing
    if "lang" not in user_session.get(user_id, {}):
        set_user_language(user_id, DEFAULT_LANGUAGE)
    
    lang = get_user_language(user_id)
    texts = get_texts(lang)

    # Show welcome message with language keyboard
    await update.message.reply_text(texts["welcome"], reply_markup=LANGUAGE_KEYBOARD)

    # Ask for language selection
    await update.message.reply_text(
        texts["choose_language"],
        reply_markup=LANGUAGE_KEYBOARD
    )
    return CHOOSING_LANGUAGE

async def choose_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Language inline button callback
    """
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    if data.startswith("lang_"):
        lang_code = data.split("_")[1]
        set_user_language(user_id, lang_code)
        texts = get_texts(lang_code)
        await query.answer(texts["language_set"], show_alert=False)
        await query.edit_message_text(texts["language_set"])
        
        # Now proceed to choose a salon
        return await ask_for_salon(update, context)

async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle language selection from custom keyboard
    """
    user_id = update.effective_user.id
    selected_language = update.message.text

    if selected_language in LANGUAGES:
        lang_code = LANGUAGES[selected_language]
        set_user_language(user_id, lang_code)
        texts = get_texts(lang_code)
        await update.message.reply_text(texts["language_set"], reply_markup=LANGUAGE_KEYBOARD)
        # Proceed to choose a salon
        return await ask_for_salon(update, context)
    else:
        lang = get_user_language(user_id)
        texts = get_texts(lang)
        await update.message.reply_text(texts["select_language_error"], reply_markup=LANGUAGE_KEYBOARD)
        return CHOOSING_LANGUAGE

async def ask_for_salon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show list of salons (fetched from your main API) and let user pick
    """
    user_id = update.effective_user.id if update.effective_user else update.callback_query.from_user.id
    lang = get_user_language(user_id)
    texts = get_texts(lang)

    response = requests.get("https://reservon.am/api/salons")
    salons_data = response.json()
    
    # Example salons_data:
    # salons_data = [
    #     {"id": 1, "name": "Salon A"},
    #     {"id": 2, "name": "Salon B"},
    #     {"id": 3, "name": "Salon C"}
    # ]

    keyboard = []
    for s in salons_data:
        salon_id = s["id"]
        salon_name = s["name"]
        keyboard.append([InlineKeyboardButton(salon_name, callback_data=f"salon_{salon_id}")])

    await update.effective_message.reply_text(
        texts["ask_salon"],
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CHOOSING_SALON

async def choose_salon_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Callback for salon choice
    """
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    lang = get_user_language(user_id)
    texts = get_texts(lang)

    if data.startswith("salon_"):
        salon_id = data.split("_")[1]
        # Store in session
        user_session.setdefault(user_id, {})
        user_session[user_id]["salon_id"] = salon_id
        
        await query.answer(texts["salon_chosen"] + salon_id, show_alert=False)
        await query.edit_message_text(texts["salon_chosen"] + salon_id)
        
        return await show_main_options(query, context)

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
            InlineKeyboardButton(texts["option_date"], callback_data="opt_date"),
            InlineKeyboardButton("Изменить язык", callback_data="change_language")  # Добавляем кнопку для смены языка
        ]
    ]
    await query.message.reply_text(
        texts["ask_option"],
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CHOOSING_OPTION

async def main_options_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles user's choice among the 3 main options
    """
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    lang = get_user_language(user_id)
    texts = get_texts(lang)

    if data == "opt_services":
        salon_id = user_session[user_id].get("salon_id")
        response = requests.get(f"https://reservon.am/api/salon/{salon_id}/services")
        services = response.json()
        # Example services:
        # services = [
        #     {"id": 2, "name": "Service X"},
        #     {"id": 4, "name": "Service Y"},
        #     {"id": 5, "name": "Service Z"},
        # ]
        # We'll store them in session for ID lookup
        user_session[user_id]["services_list"] = services
        keyboard = []
        for svc in services:
            kb_text = svc["name"]
            kb_cb = f"pickservice_{svc['id']}"
            keyboard.append([InlineKeyboardButton(kb_text, callback_data=kb_cb)])
        # Add a "Done" button
        keyboard.append([InlineKeyboardButton(texts["done"], callback_data="services_done")])

        await query.message.reply_text(texts["option_services"], reply_markup=InlineKeyboardMarkup(keyboard))
        return CHOOSING_SERVICES

    elif data == "opt_barbers":
        # Fetch barbers from API
        salon_id = user_session[user_id].get("salon_id")
        response = requests.get(f"https://reservon.am/api/salon/{salon_id}/barbers")
        barbers = response.json()
        # Example barbers:
        # barbers = [
        #     {"id": 1, "name": "Barber A"},
        #     {"id": 2, "name": "Barber B"}
        # ]
        user_session[user_id]["barbers_list"] = barbers
        kb = []
        for b in barbers:
            kb.append([InlineKeyboardButton(b["name"], callback_data=f"pickbarber_{b['id']}")])
        kb.append([InlineKeyboardButton(texts["done"], callback_data="barbers_done")])
        await query.message.reply_text(texts["option_barbers"], reply_markup=InlineKeyboardMarkup(kb))
        return CHOOSING_BARBERS

    elif data == "opt_date":
        # Ask for date
        await query.message.reply_text(texts["ask_date"])
        return CHOOSING_DATE

    elif data == "change_language":
        # Отображаем клавиатуру выбора языка
        await query.message.reply_text(
            get_texts(lang)["language_prompt"],
            reply_markup=LANGUAGE_KEYBOARD
        )
        return CHOOSING_LANGUAGE

async def pick_service_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle user picking a service
    """
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    lang = get_user_language(user_id)
    texts = get_texts(lang)

    if data.startswith("pickservice_"):
        svc_id = data.split("_")[1]
        # Add to user_session
        chosen_services = user_session[user_id].get("chosen_services", [])
        if svc_id not in chosen_services:
            chosen_services.append(svc_id)
        user_session[user_id]["chosen_services"] = chosen_services
        await query.answer("Service added")
        return CHOOSING_SERVICES

    elif data == "services_done":
        # Done picking services
        # Show chosen services
        chosen_ids = user_session[user_id].get("chosen_services", [])
        # Convert IDs -> names
        all_services = user_session[user_id]["services_list"]
        chosen_names = []
        for cid in chosen_ids:
            for s in all_services:
                if str(s["id"]) == cid:
                    chosen_names.append(s["name"])
        user_session[user_id]["chosen_services_names"] = chosen_names
        
        lang = get_user_language(user_id)
        texts = get_texts(lang)
        msg = texts["services_chosen"] + ", ".join(chosen_names) if chosen_names else "No services chosen"
        
        await query.message.reply_text(msg, reply_markup=LANGUAGE_KEYBOARD)
        return await show_main_options(query, context)

async def pick_barber_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle user picking a barber
    """
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    lang = get_user_language(user_id)
    texts = get_texts(lang)

    if data.startswith("pickbarber_"):
        barber_id = data.split("_")[1]
        chosen_barbers = user_session[user_id].get("chosen_barbers", [])
        if barber_id not in chosen_barbers:
            chosen_barbers.append(barber_id)
        user_session[user_id]["chosen_barbers"] = chosen_barbers
        await query.answer("Barber added")
        return CHOOSING_BARBERS

    elif data == "barbers_done":
        # Done picking barbers
        chosen_ids = user_session[user_id].get("chosen_barbers", [])
        all_barbers = user_session[user_id]["barbers_list"]
        chosen_names = []
        for cid in chosen_ids:
            for b in all_barbers:
                if str(b["id"]) == cid:
                    chosen_names.append(b["name"])
        user_session[user_id]["chosen_barbers_names"] = chosen_names
        
        lang = get_user_language(user_id)
        texts = get_texts(lang)
        msg = texts["barbers_chosen"] + ", ".join(chosen_names) if chosen_names else "No barbers chosen"
        
        await query.message.reply_text(msg, reply_markup=LANGUAGE_KEYBOARD)
        return await show_main_options(query, context)

async def received_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    User typed a date, ask for hour
    """
    user_id = update.effective_user.id
    date_text = update.message.text.strip()
    # In reality, parse and validate
    user_session[user_id]["chosen_date"] = date_text

    lang = get_user_language(user_id)
    texts = get_texts(lang)
    await update.message.reply_text(texts["ask_hour"], reply_markup=LANGUAGE_KEYBOARD)
    return CHOOSING_HOUR

async def received_hour(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    User typed an hour, ask for minutes
    """
    user_id = update.effective_user.id
    hour_text = update.message.text.strip()
    user_session[user_id]["chosen_hour"] = hour_text

    lang = get_user_language(user_id)
    texts = get_texts(lang)
    await update.message.reply_text(texts["ask_minutes"], reply_markup=LANGUAGE_KEYBOARD)
    return CHOOSING_MINUTES

async def received_minutes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    User typed minutes, we finalize date/time
    """
    user_id = update.effective_user.id
    min_text = update.message.text.strip()
    lang = get_user_language(user_id)
    texts = get_texts(lang)

    date_ = user_session[user_id].get("chosen_date", "")
    hour_ = user_session[user_id].get("chosen_hour", "")
    user_session[user_id]["chosen_minutes"] = min_text

    # Example final string
    final_datetime = f"{date_} {hour_}:{min_text}"
    user_session[user_id]["final_datetime"] = final_datetime

    await update.message.reply_text(texts["date_chosen"] + final_datetime, reply_markup=LANGUAGE_KEYBOARD)
    # Return to main menu
    return CHOOSING_OPTION

# Command to change language at any time
async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    texts = get_texts(lang)
    await update.message.reply_text(
        texts["language_prompt"],
        reply_markup=LANGUAGE_KEYBOARD
    )
    return CHOOSING_LANGUAGE

def main():
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_LANGUAGE: [
                CallbackQueryHandler(choose_language_callback, pattern="^lang_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_language_selection)
            ],
            CHOOSING_SALON: [
                CallbackQueryHandler(choose_salon_callback, pattern="^salon_.*")
            ],
            CHOOSING_OPTION: [
                CallbackQueryHandler(main_options_callback, pattern="^(opt_services|opt_barbers|opt_date|change_language)$")
            ],
            CHOOSING_SERVICES: [
                CallbackQueryHandler(pick_service_callback, pattern="^(pickservice_|services_done)")
            ],
            CHOOSING_BARBERS: [
                CallbackQueryHandler(pick_barber_callback, pattern="^(pickbarber_|barbers_done)")
            ],
            CHOOSING_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, received_date)
            ],
            CHOOSING_HOUR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, received_hour)
            ],
            CHOOSING_MINUTES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, received_minutes)
            ],
        },
        fallbacks=[
            CommandHandler("language", change_language)
        ]
    )

    app.add_handler(conv_handler)

    # Start the bot
    app.run_polling()

if __name__ == "__main__":
    main()
