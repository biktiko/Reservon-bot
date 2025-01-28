import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext
from utils.api import get_salon_details
from utils.session import get_user_language, get_session
from states import CHOOSING_SERVICES
from handlers.datetime_handler import choose_day

logger = logging.getLogger(__name__)

async def choose_services(update, context: CallbackContext):
    """
    Показывает услуги в сетке (toggle).
    Кнопка "Готово" -> handle_service_selection -> формирует booking_details -> choose_day.
    """
    if update.callback_query:
        query = update.callback_query
        user_id = query.from_user.id
        message = query.message
    else:
        user_id = update.effective_user.id
        message = update.effective_message

    session = get_session(user_id)
    salon_id = session.get("salon_id")
    if not salon_id:
        await message.reply_text("Salon not found in session.")
        return

    salon_data = get_salon_details(salon_id)
    services = salon_data.get("services", [])
    print(services)

    session["services_list"] = services
    # Если хотим сбрасывать выбранные услуги при каждом вызове
    # session["chosen_services"] = []

    kb = build_services_keyboard(services, session.get("chosen_services", []))
    await message.reply_text(
        "Выберите услуги и нажмите готово.",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return CHOOSING_SERVICES

def build_services_keyboard(services, chosen_ids, row_size=2):
    """
    Строит кнопки по row_size=2.
    Если услуга выбрана -> "✔" префикс.
    Последняя кнопка -> "Готово" (на всю ширину).
    """
    buttons = []
    for svc in services:
        sid_str = str(svc["id"])
        prefix = "✔ " if sid_str in chosen_ids else ""
        text = prefix + svc["name"]
        cb_data = f"svc_{sid_str}"
        buttons.append(InlineKeyboardButton(text, callback_data=cb_data))

    # Создаем клавиатуру с кнопками услуг
    keyboard = []
    for i in range(0, len(buttons), row_size):
        keyboard.append(buttons[i:i+row_size])

    # Добавляем кнопку "Готово" на всю ширину
    keyboard.append([InlineKeyboardButton("Готово", callback_data="services_done")])

    return keyboard

async def handle_service_selection(update: Update, context: CallbackContext):
    """
    Toggle услугу (svc_xx) или "services_done" -> формируем booking_details и переходим к choose_day.
    """
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    session = get_session(user_id)

    services = session.get("services_list", [])
    chosen_ids = session.get("chosen_services", [])

    if data == "services_done":
        # Формируем booking_details
        if chosen_ids:
            from utils.functions import parse_duration_to_minutes

            sum_duration = 0
            service_objects = []
            chosen_names = []
            for svc in services:
                sid_str = str(svc["id"])
                if sid_str in chosen_ids:
                    category_id = svc.get("category")
                    chosen_names.append(svc["name"])
                    dur_minutes = parse_duration_to_minutes(svc.get("duration"))
                    sum_duration += dur_minutes
                    service_objects.append({
                        "serviceId": svc["id"],
                        "duration": dur_minutes,
                        "categoryId": category_id
                    })

            booking_details = [{
                "categoryId": category_id,
                "services": service_objects,
                "barberId":  session["chosen_barber"]["id"],
                "duration": sum_duration
            }]

            session["booking_details"] = booking_details
            session["total_service_duration"] = sum_duration

            if chosen_names:
                await query.message.reply_text(
                    f"Вы выбрали: {', '.join(chosen_names)} (общая длит. ~{sum_duration} мин)"
                )
            else:
                await query.message.reply_text("Вы ничего не выбрали (неизв. ошибка).")
        else:
            # Ничего не выбрано
            session["booking_details"] = []
            session["total_service_duration"] = 30
            await query.message.reply_text("Вы не выбрали ни одной услуги. (Будет 30 мин по умолч.)")

        # Идём к дате
        from handlers.datetime_handler import choose_day
        return await choose_day(update, context)

    elif data.startswith("svc_"):
        sid_str = data.split("_")[1]
        if sid_str in chosen_ids:
            chosen_ids.remove(sid_str)
        else:
            chosen_ids.append(sid_str)
        session["chosen_services"] = chosen_ids

        new_kb = build_services_keyboard(services, chosen_ids)
        await query.edit_message_reply_markup(InlineKeyboardMarkup(new_kb))
        return CHOOSING_SERVICES

    else:
        await query.answer("Неизвестная команда")
        return CHOOSING_SERVICES
