import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext
from utils.session import get_session
from utils.localization import SHORT_DAYS
from states import CHOOSING_SERVICES, CHOOSING_DATE, CHOOSING_HOUR, CHOOSING_MINUTES, CONFIRM_BOOKING
from datetime import datetime, timedelta
from utils.api import get_available_minutes
import requests

logger = logging.getLogger(__name__)

def build_grid(buttons, row_size=3):
    keyboard = []
    for i in range(0, len(buttons), row_size):
        keyboard.append(buttons[i:i+row_size])
    return keyboard

async def choose_day(update: Update, context: CallbackContext):
    """
    Показывает список дат и кнопку "Изменить услуги"
    """
    user_id = update.effective_user.id
    session = get_session(user_id)

    salon_id = session.get("salon_id")
    if not salon_id:
        await update.effective_message.reply_text("Salon ID missing in session.")
        return

    reservDays = session.get("reservDays", 7)
    now = datetime.now()
    dates = [now + timedelta(days=i) for i in range(reservDays)]

    dayNames = SHORT_DAYS["ru"]
    buttons = []
    for d in dates:
        wday = d.weekday()
        day_abbr = dayNames[wday]
        ddmm = d.strftime("%d.%m")
        iso = d.strftime("%Y-%m-%d")
        text = f"{day_abbr}, {ddmm}"
        cb = f"day_{iso}"
        buttons.append(InlineKeyboardButton(text, callback_data=cb))

    kb = build_grid(buttons, row_size=3)
    # Добавляем фиксированную строку
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

    chosen_date = data.split("_", 1)[1]
    session["chosen_date"] = chosen_date

    # После выбора дня показываем часы
    return await show_hours(update, context, chosen_date)

async def show_hours(update: Update, context: CallbackContext, chosen_date: str):
    """
    Вычисляет доступные часы для выбранного дня и выводит их.
    """
    user_id = update.callback_query.from_user.id
    session = get_session(user_id)
    booking_details = session.get("booking_details", [])
    total_duration = sum(cat.get("duration", 0) for cat in booking_details) or 30

    hours_list = list(range(9, 23))
    payload = {
        "salon_id": session["salon_id"],
        "date": chosen_date,
        "hours": hours_list,
        "booking_details": booking_details,
        "total_service_duration": total_duration
    }
    logger.warning("[show_hours] sending => %r", payload)
    try:
        response = get_available_minutes(payload)
        data_json = response.json()
        avail = data_json.get("available_minutes", {})
    except Exception as e:
        logger.error("Error get_available_minutes: %s", e)
        await update.callback_query.message.reply_text("Ошибка сервера.")
        return CHOOSING_DATE

    valid_hours = [h for h in hours_list if avail.get(str(h))]
    if not valid_hours:
        await update.callback_query.message.reply_text("Нет доступных часов для этого дня.")
        return CHOOSING_DATE

    hour_buttons = []
    for h in valid_hours:
        cb = f"hour_{h}"
        txt = f"≈ {h}:00"
        hour_buttons.append(InlineKeyboardButton(txt, callback_data=cb))

    kb = build_grid(hour_buttons, row_size=2)
    # Фиксированная строка с кнопками
    kb.append([
        InlineKeyboardButton("Изменить день", callback_data="change_day"),
        InlineKeyboardButton("Изменить услуги", callback_data="change_services")
    ])

    await update.callback_query.message.reply_text(
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

    # Если нажата кнопка "change_day" или "change_services", обрабатываем их отдельно:
    if data == "change_day":
        return await choose_day(update, context)
    if data == "change_services":
        from handlers.services import choose_services
        return await choose_services(update, context)

    if not data.startswith("hour_"):
        await query.message.reply_text("Некорректный выбор часа.")
        return CHOOSING_HOUR

    try:
        chosen_hour = int(data.split("_", 1)[1])
    except ValueError:
        await query.message.reply_text("Некорректный формат выбранного часа.")
        return CHOOSING_HOUR

    session["chosen_hour"] = chosen_hour
    chosen_date = session.get("chosen_date", "")

    # Определяем режим бронирования для телеграм (например, в сессии сохранён параметр "appointment_mod")
    appointment_mod = session.get("appointment_mod", "handler")
    logger.warning("Telegram bot: appointment_mod = %r", appointment_mod)

    # Если режим auto, вместо стандартного показа минут вызываем API get_nearest_available_time
    if appointment_mod == "auto":

        total_duration = session.get("total_service_duration", 30)
        booking_details = session.get("booking_details", [])
        payload = {
            "salon_id": session["salon_id"],
            "date": chosen_date,
            "chosen_hour": chosen_hour,
            "booking_details": booking_details,
            "total_service_duration": total_duration
        }
        logger.info("[handle_hour_selection] Payload for auto mode: %r", payload)
        try:
            # Здесь можно использовать requests (синхронно) или aiohttp/async requests; для примера используем requests
            api_url = f"https://reservon.am/api/salons/get_nearest_available_time/"
            resp = requests.post(api_url, json=payload)
            if resp.status_code != 200:
                await query.message.reply_text(f"Ошибка сервера: {resp.status_code}")
                return CHOOSING_HOUR
            data_json = resp.json()
            logger.info("[handle_hour_selection] Received: %r", data_json)
        except Exception as e:
            logger.error("Ошибка вызова API get_nearest_available_time: %s", e)
            await query.message.reply_text("Ошибка получения доступного времени.")
            return CHOOSING_HOUR

        # Извлекаем варианты
        nearest_before = data_json.get("nearest_before")
        nearest_after = data_json.get("nearest_after")

        # Преобразуем nearest_before
        h1, m1 = map(int, nearest_before.replace("։", ":").split(":"))
        diff_minutes = 0

        if "nearest_after" in data and nearest_after:
            h2, m2 = map(int, nearest_after.replace("։", ":").split(":"))
            diff_minutes = (h2 * 60 + m2) - (h1 * 60 + m1)

        print("Ближайшее время:", nearest_before, nearest_after, diff_minutes)

         # Форматируем дату для вывода (например, "30 января")
        chosen_date = session.get("chosen_date", "")

        # Определяем выбранное время
        chosen_time = None
        if nearest_after and nearest_before and (nearest_before == nearest_after or diff_minutes < 30):
            later_time = nearest_after if nearest_after > nearest_before else nearest_before
            chosen_time = later_time
        elif nearest_before:
            chosen_time = nearest_before
        elif nearest_after:
            chosen_time = nearest_after
        else:
            await query.message.reply_text("Нет доступного времени для бронирования в этот час.")
            return CHOOSING_HOUR

        # Определяем hm_str как выбранное время
        hm_str = chosen_time
        session["chosen_time"] = hm_str  # сохраняем выбранное время в сессии

        # Форматируем дату для вывода (например, "30 января")
        chosen_date = session.get("chosen_date", "")
        try:
            dt_obj = datetime.strptime(chosen_date, "%Y-%m-%d")
            day_num = dt_obj.day
            month_num = dt_obj.month
            ru_months = [
                "января", "февраля", "марта", "апреля", "мая", "июня",
                "июля", "августа", "сентября", "октября", "ноября", "декабря"
            ]
            month_name_ru = ru_months[month_num - 1]
            date_str = f"{day_num} {month_name_ru}"
        except ValueError:
            date_str = chosen_date

        # Форматируем время, заменяя двоеточие на символ "։"
        time_str = hm_str.replace(":", "։")
        barber = session.get("chosen_barber")
        barber_name = barber["name"] if barber else "—"

        chosen_services = session.get("chosen_services", [])
        services_list = session.get("services_list", [])
        chosen_names = [svc["name"] for svc in services_list if str(svc["id"]) in chosen_services]
        services_str = ", ".join(chosen_names) if chosen_names else "не выбраны"

        text = (
            f"Вы выбрали: {date_str} {time_str}\n\n"
            f"Мастер: {barber_name}\n"
            f"Услуги: {services_str}"
        )

        # Формируем inline-клавиатуру
        buttons = []
        # Если доступен только один вариант (мы уже выбрали chosen_time), показываем одну кнопку
        buttons.append(InlineKeyboardButton(
            f"Подтвердить заказ во {hm_str}",
            callback_data=f"confirm_{hm_str}"
        ))
        # Добавляем кнопки для изменения выбора
        buttons.append(InlineKeyboardButton("Изменить час", callback_data="change_hour"))
        buttons.append(InlineKeyboardButton("Изменить услуги", callback_data="change_services"))
        kb = InlineKeyboardMarkup([[btn] for btn in buttons])
        await query.message.reply_text(
            f"{text}\n\nВыберите время для подтверждения заказа:",
            reply_markup=kb
        )
        return CONFIRM_BOOKING

    else:
        # Режим handler — стандартная логика: например, запрашиваем доступные минуты через get_available_minutes
        payload = {
            "salon_id": session["salon_id"],
            "date": chosen_date,
            "hours": [chosen_hour],
            "booking_details": session.get("booking_details", []),
            "total_service_duration": session.get("total_service_duration", 30)
        }
        logger.info("[handle_hour_selection] Payload for handler mode: %r", payload)
        try:
            response = get_available_minutes(payload)
            data_json = response.json()
            logger.info("[handle_hour_selection] Got available minutes: %r", data_json)
        except Exception as e:
            logger.error("Error in get_available_minutes: %s", e)
            await query.message.reply_text("Ошибка сервера (час).")
            return CHOOSING_HOUR

        avail = data_json.get("available_minutes", {})
        minute_list = avail.get(str(chosen_hour), [])
        if not minute_list:
            await query.message.reply_text("Нет доступных минут для этого часа.")
            return CHOOSING_HOUR

        # Строим клавиатуру для выбора минут (как ранее)
        minute_buttons = []
        for m in minute_list:
            m_int = int(m)
            end_m = m_int + session.get("total_service_duration", 30)
            end_h = chosen_hour
            if end_m >= 60:
                end_h += end_m // 60
                end_m = end_m % 60
            start_str = f"{chosen_hour}:{m_int:02d}"
            end_str = f"{end_h}:{end_m:02d}"
            txt = f"{start_str}-{end_str}"
            cb = f"min_{chosen_hour}:{m_int:02d}"
            minute_buttons.append(InlineKeyboardButton(txt, callback_data=cb))
        kb = InlineKeyboardMarkup([[btn] for btn in minute_buttons] +
                                  [[InlineKeyboardButton("Изменить час", callback_data="change_hour"),
                                    InlineKeyboardButton("Изменить услуги", callback_data="change_services")]])
        await query.message.reply_text(
            f"Вы выбрали час {chosen_hour}:00. Выберите точное время:",
            reply_markup=kb
        )
        return CHOOSING_MINUTES

async def handle_minute_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    await query.answer()

    user_id = query.from_user.id
    session = get_session(user_id)

    if data == "change_hour":
        # Вместо попытки изменить update.callback_query.data, просто вызываем show_hours
        chosen_date = session.get("chosen_date", "")
        return await show_hours(update, context, chosen_date)
    if data == "change_services":
        from handlers.services import choose_services
        return await choose_services(update, context)

    if not data.startswith("min_"):
        await query.message.reply_text("Некорректный формат минут.")
        return CHOOSING_MINUTES

    # Пример: data = "min_14:20"
    hm_str = data.split("_", 1)[1]  # "14:20"
    session["chosen_time"] = hm_str

    # Форматируем дату для вывода (например, "30 января")
    chosen_date = session.get("chosen_date", "")
    try:
        dt_obj = datetime.strptime(chosen_date, "%Y-%m-%d")
        day_num = dt_obj.day
        month_num = dt_obj.month
        ru_months = [
            "января", "февраля", "марта", "апреля", "мая", "июня",
            "июля", "августа", "сентября", "октября", "ноября", "декабря"
        ]
        month_name_ru = ru_months[month_num - 1]
        date_str = f"{day_num} {month_name_ru}"
    except ValueError:
        date_str = chosen_date

    time_str = hm_str.replace(":", "։")
    barber = session.get("chosen_barber")
    barber_name = barber["name"] if barber else "—"

    chosen_services = session.get("chosen_services", [])
    services_list = session.get("services_list", [])
    chosen_names = [svc["name"] for svc in services_list if str(svc["id"]) in chosen_services]
    services_str = ", ".join(chosen_names) if chosen_names else "не выбраны"

    text = (
        f"Вы выбрали: {date_str} {time_str}\n\n"
        f"Мастер: {barber_name}\n"
        f"Услуги: {services_str}"
    )

    await query.message.reply_text(text)

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

async def handle_change_hour(update: Update, context: CallbackContext):
    """Возврат к выбору часа."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    session = get_session(user_id)
    chosen_date = session.get("chosen_date", "")
    # Возвращаемся к выбору часов, например, вызывая show_hours:
    return await show_hours(update, context, chosen_date)

async def handle_change_services(update: Update, context: CallbackContext):
    """Возврат к выбору услуг."""
    query = update.callback_query
    await query.answer()
    from handlers.services import choose_services
    return await choose_services(update, context)
