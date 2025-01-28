# handlers/language.py
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext
from utils.localization import get_texts, LANGUAGES
from utils.session import set_user_language, get_user_language
from states import CHOOSING_LANGUAGE, CHOOSING_SALON, CHOOSING_BARBERS, CHOOSING_SERVICES, CHOOSING_DATE, CHOOSING_HOUR, CHOOSING_MINUTES
from utils.session import  get_session

import logging

logger = logging.getLogger(__name__)

LANGUAGE_BUTTONS = [
    [KeyboardButton("Русский"), KeyboardButton("Հայերեն"), KeyboardButton("English")]
]

LANGUAGE_KEYBOARD = ReplyKeyboardMarkup(
    LANGUAGE_BUTTONS, resize_keyboard=True, one_time_keyboard=False
)

from handlers.salon import ask_for_salon
from handlers.barbers import handle_barber_selection
from handlers.services import handle_service_selection

async def handle_language_command(update: Update, context: CallbackContext):
    logger.info('Команда /language вызвана')
    user_id = update.effective_user.id
    current_state = context.user_data.get('current_state')
    
    # Сохранение текущего состояния
    if current_state:
        context.user_data['previous_state'] = current_state
    else:
        context.user_data['previous_state'] = None

    # Отправка сообщения с выбором языка
    texts = get_texts(get_user_language(user_id))
    await update.message.reply_text(
        texts["choose_language"],
        reply_markup=LANGUAGE_KEYBOARD
    )

    # Переход в состояние выбора языка
    return CHOOSING_LANGUAGE

async def handle_language_selection(update: Update, context: CallbackContext):
    print('handle_language_selection вызван')
    logger.info('handle_language_selection вызван')
    user_id = update.effective_user.id
    selected_language = update.message.text

    if selected_language in LANGUAGES:
        lang_code = LANGUAGES[selected_language]
        set_user_language(user_id, lang_code)
        texts = get_texts(lang_code)
        await update.message.reply_text(texts["language_set"], reply_markup=LANGUAGE_KEYBOARD)

        # Восстановление предыдущего состояния
        previous_state = context.user_data.get('previous_state')
        if previous_state:
            logger.info(f"Восстановление состояния: {previous_state}")
            # В зависимости от предыдущего состояния, повторно отправляем соответствующий запрос
            if previous_state == CHOOSING_SALON:
                return await ask_for_salon(update, context)
            elif previous_state == CHOOSING_BARBERS:
                # Переотправка списка барберов
                barbers = get_session(user_id).get('barbers_list', [])
                for barber in barbers:
                    compressed_image = compress_image(barber["avatar"])
                    await update.message.reply_photo(
                        photo=compressed_image,
                        caption=f"<b>{barber['name']}</b>\n{barber['description']}",
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton(text=f"Выбрать {barber['name']}", callback_data=f"barber_{barber['id']}")]
                        ])
                    )
                return CHOOSING_BARBERS
            elif previous_state == CHOOSING_SERVICES:
                # Повторный запрос на выбор услуг
                return await handle_service_selection(update, context)
            # elif previous_state == CHOOSING_DATE:
            #     # Повторный запрос даты
            #     return await received_date(update, context)
            # elif previous_state == CHOOSING_HOUR:
            #     # Повторный запрос часа
            #     return await received_hour(update, context)
            # elif previous_state == CHOOSING_MINUTES:
            #     # Повторный запрос минут
            #     return await received_minutes(update, context)
            else:
                # Если предыдущее состояние неизвестно, перейти к выбору салона
                return CHOOSING_SALON
        else:
            # Если предыдущее состояние неизвестно, перейти к выбору салона
            return CHOOSING_SALON
    else:
        lang = get_user_language(user_id)
        texts = get_texts(lang)
        await update.message.reply_text(texts["select_language_error"], reply_markup=LANGUAGE_KEYBOARD)
        return CHOOSING_LANGUAGE

def compress_image(image_url, size=(128, 128)):
    """Функция для сжатия изображения до указанного размера."""
    import requests
    from PIL import Image
    from io import BytesIO

    response = requests.get(image_url)
    image = Image.open(BytesIO(response.content))
    image.thumbnail(size)  # Устанавливаем размер
    output = BytesIO()
    image.save(output, format="JPEG")
    output.seek(0)
    return output
