import re
import requests
from datetime import datetime, timedelta

from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove,
    InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
)
from telegram.ext import (
    Application, ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)
from asgiref.sync import sync_to_async

from states import ADMIN_PHONE, ADMIN_SELECT_BARBER, ADMIN_SELECT_SALON, ADMIN_WAIT_COMMAND

def parse_booking_command(text, default_duration=30):
    """
    Разбирает команду бронирования, возвращая словарь с:
      - start_time: время начала (формат HH:MM; время можно вводить с ":" или "։", будет нормализовано в "։")
      - end_time: время окончания (либо вычисленное из длительности)
      - duration: длительность в минутах
      - date: дата бронирования в формате YYYY-MM-DD (можно вводить с разделителем "․" или ".")
      - comment: дополнительный комментарий
    Примеры:
      "10:30-10:40 11.02"
      "11.02 10:30-11:40"
      "15.02 10:30 20 Comment"
    """
    tokens = text.split()
    # Нормализуем токены времени:
    for i, token in enumerate(tokens):
        # Если токен соответствует формату "HH:MM", заменяем ":" на "։"
        if re.fullmatch(r'\d{1,2}:\d{2}', token):
            tokens[i] = token.replace(":", "։")
        # Если токен содержит диапазон, например "10:30-10:40"
        elif "-" in token:
            parts = token.split("-")
            if len(parts) == 2:
                new_parts = []
                for part in parts:
                    if re.fullmatch(r'\d{1,2}:\d{2}', part):
                        new_parts.append(part.replace(":", "։"))
                    else:
                        new_parts.append(part)
                tokens[i] = "-".join(new_parts)
    start_time = None
    end_time = None
    duration = None
    booking_date = None
    comment_tokens = []

    def is_time(token):
        # Проверяем, что время содержит символ "։" и соответствует формату, например, "14։20"
        return "։" in token and re.fullmatch(r'\d{1,2}։\d{2}', token) is not None

    def is_date(token):
        # Допускаем разделитель "․" или ".", например "15․02" или "15.02" (также "15․02․25")
        return re.fullmatch(r'\d{1,2}[․\.]\d{2}([․\.]\d{2,4})?', token) is not None

    def is_number(token):
        return re.fullmatch(r'\d+', token) is not None

    i = 0
    while i < len(tokens):
        token = tokens[i]
        # Если токен содержит диапазон времени, например "10։30-10։40"
        if "-" in token and ("։" in token):
            parts = token.split("-")
            if len(parts) == 2 and is_time(parts[0].strip()) and is_time(parts[1].strip()):
                start_time = parts[0].strip()
                end_time = parts[1].strip()
                i += 1
                continue
        if is_time(token):
            if not start_time:
                start_time = token
                i += 1
                continue
            elif not end_time:
                end_time = token
                i += 1
                continue
        if is_number(token) and start_time and duration is None:
            duration = int(token)
            i += 1
            # Если после числа сразу следует слово "минут" или "րոպե", пропускаем его
            if i < len(tokens) and tokens[i].lower() in ["минут", "րոպե"]:
                i += 1
            continue
        if is_date(token) and booking_date is None:
            # Заменяем точку на "․" для единообразия
            token = token.replace(".", "․")
            parts = token.split("․")
            try:
                day = int(parts[0])
                month = int(parts[1])
                if len(parts) == 3:
                    yr = int(parts[2])
                    if yr < 100:
                        yr += 2000
                else:
                    yr = datetime.today().year
                booking_date = datetime(yr, month, day).date()
            except Exception:
                booking_date = datetime.today().date()
            i += 1
            continue
        comment_tokens.append(token)
        i += 1

    if start_time and end_time and duration is None:
        fmt = "%H:%M"
        st_conv = start_time.replace("։", ":")
        et_conv = end_time.replace("։", ":")
        try:
            st = datetime.strptime(st_conv, fmt)
            et = datetime.strptime(et_conv, fmt)
            diff = (et - st).total_seconds() / 60
            if diff <= 0:
                diff += 24 * 60
            duration = int(diff)
        except Exception:
            duration = default_duration
    elif start_time and duration is None:
        duration = default_duration

    if booking_date is None:
        booking_date = datetime.today().date()
    if start_time:
        fmt = "%H:%M"
        st_conv = start_time.replace("։", ":")
        try:
            st_time_obj = datetime.strptime(st_conv, fmt).time()
            booking_dt = datetime.combine(booking_date, st_time_obj)
            # Если время на полученную дату уже прошло, то бронирование – на следующий день
            if booking_dt < datetime.now():
                booking_date += timedelta(days=1)
        except Exception:
            pass

    return {
        "start_time": start_time.replace("։", ":") if start_time else None,
        "end_time": end_time.replace("։", ":") if end_time else None,
        "duration": duration,
        "date": booking_date.strftime("%Y-%m-%d"),
        "comment": " ".join(comment_tokens).strip()
    }

def change_master_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("Сменить мастера", callback_data="admin_change_barber")]])

# 1. Запуск админ-сессии. Если номер уже сохранён, переходим сразу к выбору мастера.
async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if "phone_number" in context.user_data:
        if "salon" in context.user_data:
            return await admin_choose_barber(update, context)
        else:
            return await admin_handle_phone(update, context)
    kb = [
        [KeyboardButton("Поделиться номером телефона", request_contact=True)]
    ]
    markup = ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "Введите или поделитесь номером телефона для входа в админ панель:",
        reply_markup=markup
    )
    return ADMIN_PHONE

# 2. Обработка номера телефона и проверка через API
async def admin_handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.contact:
        phone_number = update.message.contact.phone_number
    else:
        phone_number = update.message.text.strip()
    context.user_data["phone_number"] = phone_number

    payload = {"phone_number": phone_number}
    url = "https://reservon.am/api/admin/verify/"
    try:
        resp = requests.post(url, json=payload)
    except Exception:
        await update.message.reply_text("Ошибка запроса к серверу.")
        return ConversationHandler.END

    if resp.status_code != 200:
        await update.message.reply_text("Ошибка проверки админ прав.")
        return ConversationHandler.END

    data = resp.json()
    if not data.get("success"):
        await update.message.reply_text("Вы не являетесь администратором ни одного салона.")
        return ConversationHandler.END

    salons = data.get("salons", [])
    if not salons:
        await update.message.reply_text("Нет салонов, за которые вы отвечаете.")
        return ConversationHandler.END

    if len(salons) == 1:
        context.user_data["salon"] = salons[0]
        await update.message.reply_text(f"Салон выбран: {salons[0]['name']}")
        return await admin_choose_barber(update, context)
    else:
        buttons = []
        for salon in salons:
            buttons.append([InlineKeyboardButton(salon["name"], callback_data=f"admin_salon_{salon['id']}")])
        markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text("Выберите салон:", reply_markup=markup)
        context.user_data["salons"] = salons
        return ADMIN_SELECT_SALON

# 3. Обработка выбора салона (если их несколько)
async def admin_select_salon(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data  # формат "admin_salon_<id>"
    match = re.match(r"admin_salon_(\d+)", data)
    if not match:
        await query.edit_message_text("Неверный выбор салона.")
        return ConversationHandler.END
    salon_id = match.group(1)
    selected_salon = next((s for s in context.user_data.get("salons", []) if str(s["id"]) == salon_id), None)
    if not selected_salon:
        await query.edit_message_text("Салон не найден.")
        return ConversationHandler.END
    context.user_data["salon"] = selected_salon
    await query.edit_message_text(f"Салон выбран: {selected_salon['name']}")
    return await admin_choose_barber(update, context)

# 4. Ручной выбор мастера из списка, полученного через API
async def admin_choose_barber(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    salon = context.user_data.get("salon")
    if not salon:
        await update.message.reply_text("Салон не найден в сессии.")
        return ConversationHandler.END
    url = f"https://reservon.am/api/salons/{salon['id']}/"
    try:
        resp = requests.get(url)
        if resp.status_code != 200:
            await update.message.reply_text("Не удалось получить данные салона.")
            return ADMIN_WAIT_COMMAND
        data = resp.json()
    except Exception:
        await update.message.reply_text("Ошибка запроса к серверу при получении мастеров.")
        return ADMIN_WAIT_COMMAND
    barbers = data.get("barbers", [])
    if not barbers:
        await update.message.reply_text("В салоне нет зарегистрированных мастеров.")
        return ADMIN_WAIT_COMMAND
    buttons = []
    for barber in barbers:
        buttons.append([InlineKeyboardButton(barber.get("name", "Без имени"), callback_data=f"admin_barber_{barber['id']}")])
    markup = InlineKeyboardMarkup(buttons)
    if update.message:
        await update.message.reply_text(
            "Выберите мастера, от имени которого создать бронирование.\n\n"
            "Пример команды: 14։10 15։00 20 Комментарий",
            reply_markup=markup
        )
    else:
        await update.callback_query.message.reply_text("Выберите мастера, от имени которого создать бронирование:", reply_markup=markup)
    return ADMIN_SELECT_BARBER

# 5. Обработка выбора мастера
async def admin_handle_barber_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    match = re.match(r"admin_barber_(\d+)", data)
    if not match:
        await query.edit_message_text("Неверный выбор мастера.")
        return ADMIN_WAIT_COMMAND
    barber_id = match.group(1)
    context.user_data["chosen_barber"] = barber_id
    await query.edit_message_text(
        "Мастер выбран. Теперь отправьте время нового бронирования.\n\n"
        
        "Примеры команды:\n"
        "11։40-12։00\n"
        "11։40 20 минут или 11։40 20\n"
        "10։30-10։40 11․02 или 11․02 10։30-11։40\n"
        "15․02 10։30 20\n\n"
        "После любой даты можно добавить комментарий։ например 10։30 20 Ashot 097242038",

        reply_markup=change_master_button()
    )
    return ADMIN_WAIT_COMMAND

# Обработчик кнопки "Сменить мастера"
async def admin_change_master(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await admin_choose_barber(update, context)

# 6. Обработка команды бронирования от админа
async def admin_booking_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    parsed = parse_booking_command(text)
    if not parsed or not parsed.get("start_time"):
        await update.message.reply_text("Неверный формат команды. Попробуйте ещё раз.", reply_markup=change_master_button())
        return ADMIN_WAIT_COMMAND

    salon = context.user_data.get("salon")
    phone_number = context.user_data.get("phone_number")
    if not salon or not phone_number:
        await update.message.reply_text("Отсутствуют необходимые данные.")
        return ConversationHandler.END

    chosen_barber = context.user_data.get("chosen_barber")
    if chosen_barber:
        booking_details = [{
            "categoryId": "0",  # Возможна доработка логики выбора категории
            "services": [],
            "barberId": str(chosen_barber),
            "duration": parsed["duration"]
        }]
    else:
        booking_details = []

    payload = {
        "salon_id": salon["id"],
        "date": parsed["date"],
        "time": parsed["start_time"],
        "booking_details": booking_details,
        "total_service_duration": parsed["duration"],
        "endTime": parsed["end_time"] if parsed.get("end_time") else "",
        "user_comment": parsed["comment"],
        "salonMod": "category",
        "phone_number": phone_number if phone_number.startswith("+") else ("+" + phone_number)
    }

    url = f"https://reservon.am/api/salons/{salon['id']}/book/"
    try:
        resp = requests.post(url, json=payload)
    except Exception:
        await update.message.reply_text("Ошибка запроса к серверу.", reply_markup=change_master_button())
        return ADMIN_WAIT_COMMAND

    if resp.status_code >= 400:
        try:
            error_data = resp.json()
            error_msg = error_data.get("error", "Неизвестная ошибка.")
        except Exception:
            error_msg = "Неизвестная ошибка."
        await update.message.reply_text(error_msg, reply_markup=change_master_button())
        return ADMIN_WAIT_COMMAND

    data = resp.json()
    if data.get("success"):
        await update.message.reply_text("Бронирование успешно создано!", reply_markup=change_master_button())
    else:
        await update.message.reply_text("Не удалось создать бронирование: " + str(data), reply_markup=change_master_button())
    await update.message.reply_text("Отправьте новую команду бронирования.", reply_markup=change_master_button())
    return ADMIN_WAIT_COMMAND

# 7. Завершение админ-сессии
async def admin_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Админ сессия завершена.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def get_admin_conv_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("admin", admin_start)],
        states={
            ADMIN_PHONE: [MessageHandler(filters.CONTACT | filters.TEXT, admin_handle_phone)],
            ADMIN_SELECT_SALON: [CallbackQueryHandler(admin_select_salon, pattern=r"^admin_salon_")],
            ADMIN_SELECT_BARBER: [
                CallbackQueryHandler(admin_handle_barber_selection, pattern=r"^admin_barber_")
            ],
            ADMIN_WAIT_COMMAND: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_booking_command),
                CallbackQueryHandler(admin_change_master, pattern=r"^admin_change_barber$")
            ]
        },
        fallbacks=[CommandHandler("cancel", admin_cancel)],
        allow_reentry=True
    )

