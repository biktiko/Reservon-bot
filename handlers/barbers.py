# handlers/barbers.py
from telegram import ReplyKeyboardMarkup, KeyboardButton, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
# from utils.api import get_barbers
from utils.localization import get_texts
from utils.api import get_salon_details
from utils.session import get_user_language, get_session
from handlers.services import choose_services
import logging


logger = logging.getLogger(__name__)

from states import CHOOSING_BARBERS, CHOOSING_SERVICES

async def choose_barbers(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id if query else update.effective_user.id

    session = get_session(user_id)
    salon_id = session.get("salon_id")
    if not salon_id:
        await query.message.reply_text("Не выбран салон.")
        return

    salon_data = get_salon_details(salon_id)
    barbers_mod = salon_data.get("telegram_barbersMod", "with_images") 
    barbers = salon_data.get("barbers", [])

    if barbers_mod == "without_images":
        # Без фотографий — просто кнопки (row_size=2), сразу уходим на CHOOSING_SERVICES
        buttons = []
        for barber in barbers:
            barber_name = barber.get("name", "Без имени")
            barber_id = barber.get("id", 0)
            cb_data = f"barber_{barber_id}"
            buttons.append(InlineKeyboardButton(barber_name, callback_data=cb_data))

        keyboard = []
        row_size = 2
        for i in range(0, len(buttons), row_size):
            keyboard.append(buttons[i:i+row_size])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Выберите мастера:", reply_markup=reply_markup)

        # Здесь либо:
        return CHOOSING_BARBERS
        # или сразу CHOOSING_SERVICES, если хотите, чтобы сервисы выбирались тут же
        # но обычно логичнее дождаться нажатия "barber_xxx" и обработать
        # handle_barber_selection, который затем переведёт в CHOOSING_SERVICES.
        # Поэтому возвращаем CHOOSING_BARBERS.

    else:
        # === WITH IMAGES ===
        # Для каждого барбера отправляем отдельное сообщение (фото+описание+кнопка)
        for barber in barbers:
            barber_name = barber.get("name", "No name")
            barber_id = barber.get("id", 0)
            barber_desc = barber.get("description") or ""
            avatar_url = barber.get("avatar")  # например "https://example.com/image.jpg"
            # caption
            caption = f"<b>{barber_name}</b>\n{barber_desc}"

            # Кнопка "Выбрать"
            cb_data = f"barber_{barber_id}"
            button = InlineKeyboardButton(f"Выбрать {barber_name}", callback_data=cb_data)
            markup = InlineKeyboardMarkup([[button]])

            # Отправляем фото
            # Если avatar_url - это путь на Ваш сервер, убедитесь, что URL доступен извне
            await query.message.reply_photo(
                photo=avatar_url,
                caption=caption,
                parse_mode="HTML",
                reply_markup=markup
            )

        # Опционально, в конце, можно добавить какую-то кнопку "Пропустить" или "Нет барбера"
        # Но не обязательно.
        return CHOOSING_BARBERS
    
async def handle_change_barber(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer("Вы меняете мастера.")
    # Возвращаем пользователя в состояние выбора мастера,
    # вызывая функцию choose_barbers (она уже есть в handlers/barbers.py)
    from handlers.barbers import choose_barbers
    return await choose_barbers(update, context)

async def handle_barber_selection(update, context: CallbackContext):

    logger.info("handle_barber_selection")
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
