import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext
from utils.session import get_session
from utils.localization import SHORT_DAYS
from states import (
    CHOOSING_SERVICES, CHOOSING_DATE, CHOOSING_HOUR, CHOOSING_MINUTES, CONFIRM_BOOKING
)
from datetime import datetime, timedelta
from utils.api import get_available_minutes
import calendar

logger = logging.getLogger(__name__)

def build_grid(buttons, row_size=3):
    keyboard = []
    for i in range(0, len(buttons), row_size):
        keyboard.append(buttons[i:i+row_size])
    return keyboard

async def choose_day(update: Update, context: CallbackContext):
    """
    Список дат + кнопка "Изменить услуги"
    """
    user_id = update.effective_user.id
    session = get_session(user_id)

    salon_id = session.get("salon_id")
    if not salon_id:
        await update.effective_message.reply_text("Salon ID missing in session.")
        return

    reservDays = session.get("reservDays", 7)
    now = datetime.now()
    dates = []
    for i in range(reservDays):
        d = now + timedelta(days=i)
        dates.append(d)

    dayNames = SHORT_DAYS["ru"]  # or use user language
    buttons = []
    for d in dates:
        wday = d.weekday()  # 0..6
        day_abbr = dayNames[wday]
        ddmm = d.strftime("%d.%m")
        iso = d.strftime("%Y-%m-%d")
        text = f"{day_abbr}, {ddmm}"
        cb = f"day_{iso}"
        buttons.append(InlineKeyboardButton(text, callback_data=cb))

    kb = build_grid(buttons, row_size=3)
    # last row: [Изменить услуги]
    kb.append([InlineKeyboardButton("Изменить услуги", callback_data="change_services")])

    await update.effective_message.reply_text(
        "Выберите день:",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return CHOOSING_DATE

async def handle_day_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    await query.answer()

    user_id = query.from_user.id
    session = get_session(user_id)

    if data == "change_services":
        from handlers.services import choose_services
        return await choose_services(update, context)

    if not data.startswith("day_"):
        await query.message.reply_text("Invalid day format.")
        return CHOOSING_DATE

    chosen_date = data.split("_")[1]
    session["chosen_date"] = chosen_date

    booking_details = session.get("booking_details", [])
    total_duration = sum(cat.get("duration", 0) for cat in booking_details) or 30

    hours_list = list(range(9,23))
    payload = {
        "salon_id": session["salon_id"],
        "date": chosen_date,
        "hours": hours_list,
        "booking_details": booking_details,
        "total_service_duration": total_duration
    }
    logger.warning("[handle_day_selection] sending => %r", payload)
    try:
        # data_json = get_available_minutes(payload)
        # logger.warning("[handle_day_selection] got => %r", data_json)
        # logger.info("GETTING AVAILABLE MINUTES")
        # logger.info(payload)
        # response = get_available_minutes(payload)
        # logger.info("RESPONSE STARTING")
        # logger.info(response)
        # logger.info("RESPONSE END PRINTING")
        # data_json = response.json()
        # avail = data_json.get("available_minutes", {})

        response = get_available_minutes(payload)  # это requests.Response
        data_json = response.json()                # теперь парсим JSON
        avail = data_json.get("available_minutes", {})
    except Exception as e:
        logger.error("Error get_available_minutes: %s", e)
        await query.message.reply_text("Ошибка сервера.")
        return CHOOSING_DATE

    avail = data_json.get("available_minutes", {})
    valid_hours = []
    for h in hours_list:
        if avail.get(str(h)):
            valid_hours.append(h)

    if not valid_hours:
        await query.message.reply_text("Нет доступных часов для этого дня.")
        return CHOOSING_DATE

    hour_buttons = []
    for h in valid_hours:
        cb = f"hour_{h}"
        txt = f"≈ {h}:00"
        hour_buttons.append(InlineKeyboardButton(txt, callback_data=cb))

    # final row: [Изменить день, Изменить услуги]
    hour_buttons.append(InlineKeyboardButton("Изменить день", callback_data="change_day"))
    hour_buttons.append(InlineKeyboardButton("Изменить услуги", callback_data="change_services"))

    kb = build_grid(hour_buttons, row_size=2)
    await query.message.reply_text(
        f"Вы выбрали день {chosen_date}. Выберите примерный час:",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return CHOOSING_HOUR

async def handle_hour_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    await query.answer()

    user_id = query.from_user.id
    session = get_session(user_id)

    if data == "change_day":
        return await choose_day(update, context)
    if data == "change_services":
        from handlers.services import choose_services
        return await choose_services(update, context)

    if not data.startswith("hour_"):
        await query.message.reply_text("Некорректный выбор часа.")
        return CHOOSING_HOUR

    chosen_hour = data.split("_")[1]
    session["chosen_hour"] = chosen_hour
    chosen_date = session.get("chosen_date","")

    booking_details = session.get("booking_details", [])
    total_duration = sum(cat.get("duration",0) for cat in booking_details) or 30

    payload = {
        "salon_id": session["salon_id"],
        "date": chosen_date,
        "hours": [int(chosen_hour)],
        "booking_details": booking_details,
        "total_service_duration": total_duration
    }
    logger.warning("[handle_hour_selection] => %r", payload)
    try:
        response = get_available_minutes(payload)  # это requests.Response
        data_json = response.json() 
        logger.warning("[handle_hour_selection] got => %r", data_json)
    except Exception as e:
        logger.error("Error get_avail_minutes hour: %s", e)
        await query.message.reply_text("Ошибка сервера (час).")
        return CHOOSING_HOUR

    avail = data_json.get("available_minutes", {})
    minute_list = avail.get(str(chosen_hour), [])

    if not minute_list:
        await query.message.reply_text("Нет доступных минут для этого часа.")
        return CHOOSING_HOUR

    # build minute buttons
    minute_buttons = []
    for m in minute_list:
        m_int = int(m)
        end_m = m_int + total_duration
        end_h = int(chosen_hour)
        if end_m>=60:
            end_h += end_m//60
            end_m = end_m%60
        start_str = f"{chosen_hour}:{m_int:02d}"
        end_str = f"{end_h}:{end_m:02d}"
        txt = f"{start_str}-{end_str}"
        cb = f"min_{chosen_hour}:{m_int:02d}"
        minute_buttons.append(InlineKeyboardButton(txt, callback_data=cb))

    # final row: [Изменить час, Изменить услуги]
    minute_buttons.append(InlineKeyboardButton("Изменить час", callback_data="change_hour"))
    minute_buttons.append(InlineKeyboardButton("Изменить услуги", callback_data="change_services"))

    kb = build_grid(minute_buttons, row_size=2)
    await query.message.reply_text(
        f"Вы выбрали час {chosen_hour}:00. Выберите точное время:",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return CHOOSING_MINUTES

async def handle_minute_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    await query.answer()

    user_id = query.from_user.id
    session = get_session(user_id)

    # Кнопки "Изменить час" / "Изменить услуги"
    if data == "change_hour":
        # Возвращаемся к выбору часа
        return await handle_day_selection(update, context)
    if data == "change_services":
        from handlers.services import choose_services
        return await choose_services(update, context)

    if not data.startswith("min_"):
        await query.message.reply_text("Некорректный формат минут.")
        return CHOOSING_MINUTES

    # Пример: data="min_14:20"
    hm_str = data.split("_", 1)[1]  # "14:20"
    session["chosen_time"] = hm_str

    # Получаем дату, время
    chosen_date = session.get("chosen_date", "")  # "2025-01-30"
    # Парсим дату, чтобы показать "30 января"
    try:
        dt_obj = datetime.strptime(chosen_date, "%Y-%m-%d")
        day_num = dt_obj.day
        month_num = dt_obj.month
        # Название месяца по-русски (или возьмите словарь). Можно и calendar:
        month_name = calendar.month_name[month_num]  # "January" по-английски
        # Или свой словарь:
        ru_months = [
            "января","февраля","марта","апреля","мая","июня",
            "июля","августа","сентября","октября","ноября","декабря"
        ]
        month_name_ru = ru_months[month_num-1]
        date_str = f"{day_num} {month_name_ru}"
    except ValueError:
        # На случай ошибки
        date_str = chosen_date

    # Время вместо "14:20" -> "14։20"
    time_str = hm_str.replace(":", "։")

    # Смотрим выбранного мастера (если есть)
    barber = session.get("chosen_barber")
    barber_name = barber["name"] if barber else "—"

    # Список выбранных услуг
    chosen_services = session.get("chosen_services", [])  # список ID в виде str
    services_list = session.get("services_list", [])      # полный список словарей
    # соберём названия
    chosen_names = []
    for svc in services_list:
        sid_str = str(svc["id"])
        if sid_str in chosen_services:
            chosen_names.append(svc["name"])

    # Или если у вас уже booking_details собран, можно извлечь названия оттуда.
    # Но чаще удобнее здесь: chosen_names = ...
    if chosen_names:
        services_str = ", ".join(chosen_names)
    else:
        services_str = "не выбраны"

    # Формируем текст
    text = (
        f"Вы выбрали: {date_str} {time_str}\n"
        f"Мастер: {barber_name}\n"
        f"Услуги: {services_str}\n"
        "Нажмите 'Подтвердить' или 'Отменить'."
    )

    await query.message.reply_text(text)

    # Кнопки "Подтвердить"/"Отменить"
    kb = [
        [
            InlineKeyboardButton("Подтвердить", callback_data="confirm_booking"),
            InlineKeyboardButton("Отменить", callback_data="cancel_booking")
        ]
    ]
    await query.message.reply_text(
        "Подтвердить бронирование?",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return CONFIRM_BOOKING