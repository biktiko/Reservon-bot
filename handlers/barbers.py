# handlers/barbers.py
from telegram import ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import CallbackContext
# from utils.api import get_barbers
from utils.localization import get_texts
from utils.api import get_salon_details
from utils.session import get_user_language, get_session
from handlers.services import choose_services
import logging

logger = logging.getLogger(__name__)

from states import CHOOSING_BARBERS, CHOOSING_SERVICES

async def choose_barbers(update, context: CallbackContext):
    user_id = update.effective_user.id
    session = get_session(user_id)
    salon_id = session.get("salon_id")

    data = get_salon_details(salon_id)
    print('data')
    print(data)
    barbers = data["barbers"]
    session["barbers_list"] = barbers

    texts = get_texts(get_user_language(user_id))
    # Создаём кнопки для каждого мастера
    buttons = [[KeyboardButton(barber["name"])] for barber in barbers]
    buttons.append([KeyboardButton(texts["done"])])  # Кнопка "Завершить"

    keyboard = ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=False)

    await update.effective_message.reply_text("Выберите мастеров (отправьте текстовое сообщение каждого мастера). Нажмите 'Завершить' когда закончите.", reply_markup=keyboard)
    return CHOOSING_BARBERS

async def handle_barber_selection(update, context: CallbackContext):

      # Сохранение текущего состояния
    context.user_data['current_state'] = CHOOSING_BARBERS

    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    # print(data['service'])
    session = get_session(user_id)

    texts = get_texts(get_user_language(user_id))

    # Получаем список мастеров из сессии
    barbers = session.get("barbers_list", [])

    if data.startswith("barber_"):
        barber_id = int(data.split("_")[1])
        barber = next((b for b in barbers if b["id"] == barber_id), None)

        if not barber:
            await query.answer("Ошибка: мастер не найден!", show_alert=True)
            return CHOOSING_BARBERS

        # Сохраняем выбранного мастера в сес\ии
        session["chosen_barber"] = barber

        # Подтверждаем выбор
        await query.answer(f"{texts['barber_chosen']} {barber['name']}", show_alert=False)
        await query.message.reply_text(
            f"{texts['barber_chosen']} {barber['name']}"
        )

        # Переход к следующему шагу (например, выбору услуг)
        # return CHOOSING_SERVICES
    
        return await choose_services(update, context)
