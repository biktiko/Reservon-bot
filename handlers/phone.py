# handlers/phone.py

import logging
from telegram import ReplyKeyboardRemove, Update
from telegram.ext import CallbackContext
from utils.session import get_session
from states import ASK_TG_PHONE, CONFIRM_BOOKING
from handlers.booking_handler import confirm_booking_logic

logger = logging.getLogger(__name__)

async def ask_telegram_phone(update: Update, context: CallbackContext):
    """
    Показываем кнопку request_contact. 
    """
    from telegram import ReplyKeyboardMarkup, KeyboardButton

    kb = [[
        KeyboardButton("Поделиться номером телефона", request_contact=True),
        KeyboardButton("Отмена")
    ]]
    markup = ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True)
    await update.effective_message.reply_text(
        "Поделитесь номером телефона или нажмите 'Отмена':",
        reply_markup=markup
    )
    return ASK_TG_PHONE

async def handle_telegram_phone(update: Update, context: CallbackContext):
    """
    Обрабатываем результат: contact или "Отмена".
    """
    message = update.effective_message
    user_id = update.effective_user.id
    session = get_session(user_id)

    contact = update.message.contact
    if contact:
        phone_number = contact.phone_number
        session["phone_number"] = phone_number
        logger.info(f"Получен номер: {phone_number}")
        await message.reply_text(
            f"Спасибо! Ваш номер: {phone_number}\nОформляем бронирование...",
            reply_markup=ReplyKeyboardRemove()
        )

        # Сразу оформляем бронирование
        # вызываем confirm_booking_logic
        await confirm_booking_logic(session, message)
        # Возвращаемся в CONFIRM_BOOKING (или другое)
        return CONFIRM_BOOKING

    # Если нажал "Отмена"
    text = message.text
    if text == "Отмена":
        await message.reply_text("Вы отменили бронирование", reply_markup=ReplyKeyboardRemove())
        return CONFIRM_BOOKING

    # Иначе просим повторить
    await message.reply_text("Нажмите кнопку 'Поделиться номером' или 'Отмена'.")
    return ASK_TG_PHONE
