# handlers/salon.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import CallbackContext
from utils.api import get_salons, get_salon_details
from utils.localization import get_texts
from utils.session import set_user_language, get_user_language, get_session
from handlers.barbers import choose_barbers
from PIL import Image
import requests
from io import BytesIO

from states import CHOOSING_SALON, CHOOSING_BARBERS, CHOOSING_SERVICES

async def ask_for_salon(update, context: CallbackContext):

    context.user_data['current_state'] = CHOOSING_SALON
    
    user_id = update.effective_user.id if update.effective_user else update.callback_query.from_user.id
    lang = get_user_language(user_id)
    texts = get_texts(lang)

    salons_data = get_salons()

    keyboard = []
    for salon in salons_data:
        salon_id = salon["id"]
        salon_name = salon["name"]
        keyboard.append([InlineKeyboardButton(salon_name, callback_data=f"salon_{salon_id}")])

    await update.effective_message.reply_text(
        texts["ask_salon"],
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CHOOSING_SALON

async def choose_salon_callback(update, context: CallbackContext):
    context.user_data['current_state'] = CHOOSING_SALON

    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    lang = get_user_language(user_id)
    texts = get_texts(lang)

    if data.startswith("salon_"):
        salons_data = get_salons()
        salon_id = data.split("_")[1]
        salon = next((s for s in salons_data if str(s["id"]) == salon_id), None)
        if not salon:
            await query.answer("Салон не найден", show_alert=True)
            return

        salon_name = salon["name"]
        session = get_session(user_id)
        session["salon_id"] = salon_id  # Записываем в сессию

        await query.answer(texts["salon_chosen"] + salon_name, show_alert=False)
        await query.edit_message_text(texts["salon_chosen"] + salon_name)

        # Теперь вместо цикла — просто получите barbers, сохраните их в сессии (если нужно),
        # и вызывайте вашу новую функцию:
        barbers_data = get_salon_details(salon_id).get("barbers", [])
        session["barbers_list"] = barbers_data

        # Переходим к выбору барберов через handlers/barbers.py
        return await choose_barbers(update, context)


def compress_image(image_url, size=(128, 128)):
    """Функция для сжатия изображения до указанного размера."""
    response = requests.get(image_url)
    image = Image.open(BytesIO(response.content))
    image.thumbnail(size)  # Устанавливаем размер
    output = BytesIO()
    image.save(output, format="JPEG")
    output.seek(0)
    return output