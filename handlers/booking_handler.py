import logging
from telegram import Update
from telegram.ext import CallbackContext
from utils.session import get_session
import requests
from states import CONFIRM_BOOKING, ASK_TG_PHONE

logger = logging.getLogger(__name__)

async def confirm_booking(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    session = get_session(user_id)

    # Если телефон ещё не получен => спросим
    if "phone_number" not in session:
        from handlers.phone import ask_telegram_phone
        return await ask_telegram_phone(update, context)

    # Иначе телефон есть => оформляем
    await confirm_booking_logic(session, query.message)
    return CONFIRM_BOOKING

async def confirm_booking_logic(session, message):
    """
    Реальная логика POST на /book/.
    session - словарь user_data
    message - чтобы отправить ответ
    """
    salon_id = session["salon_id"]
    chosen_date = session["chosen_date"]
    chosen_time = session["chosen_time"]
    booking_details = session.get("booking_details", [])
    total_dur = session.get("total_service_duration", 30)

    # Считаем endTime
    if not chosen_date or not chosen_time:
        await message.reply_text("Дата/время не выбраны.")
        return

    h, m = chosen_time.split(":")
    startH = int(h)
    startM = int(m)
    end_min_total = startH*60 + startM + total_dur
    endH = end_min_total // 60
    endM = end_min_total % 60
    endTime_str = f"{endH:02d}:{endM:02d}"

    payload = {
        "salon_id": salon_id,
        "date": chosen_date,
        "time": chosen_time,
        "booking_details": booking_details,
        "total_service_duration": total_dur,
        "endTime": endTime_str,
        "user_comment": "",
        "salonMod": "category",
        "phone_number": session["phone_number"], 
    }

    logger.warning("[confirm_booking_logic] => %r", payload)

    url = f"https://reservon.am/api/salons/{salon_id}/book/"
    try:
        resp = requests.post(url, json=payload)
        if resp.status_code >= 400:
            await message.reply_text(f"Ошибка бронирования: {resp.status_code}\n{resp.text}")
            return
        data = resp.json()
        if data.get("success"):
            await message.reply_text("Бронирование успешно!")
        else:
            await message.reply_text("Не удалось создать бронирование: " + str(data))
    except Exception as e:
        logger.error("Exception in confirm_booking_logic: %s", e)
        await message.reply_text("Ошибка при запросе бронирования.")
        
async def cancel_booking(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Вы отменили бронирование.")
    return CONFIRM_BOOKING