import logging
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters
)
from telegram import BotCommand
import asyncio

from config import TELEGRAM_BOT_TOKEN
from handlers.language import handle_language_command, handle_language_selection
from handlers.salon import ask_for_salon, choose_salon_callback
from handlers.options import show_main_menu, main_options_callback
from handlers.services import choose_services, handle_service_selection
from handlers.barbers import handle_barber_selection, handle_change_barber
from handlers.datetime_handler import (
    handle_day_selection,
    handle_hour_selection,
    handle_minute_selection,
)
from handlers.booking_handler import confirm_booking, cancel_booking
from handlers.phone import handle_telegram_phone

from states import (
    CHOOSING_LANGUAGE,
    CHOOSING_SALON,
    CHOOSING_BARBERS,
    CHOOSING_SERVICES,
    CHOOSING_DATE,
    CHOOSING_HOUR,
    CHOOSING_MINUTES,
    CONFIRM_BOOKING,
    ASK_TG_PHONE
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.WARNING
)
logger = logging.getLogger(__name__)

async def set_bot_commands(application):
    commands = [
        BotCommand("start", "Start the bot"),
        # BotCommand("language", "Change the language"),
    ]
    await application.bot.set_my_commands(commands)

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(set_bot_commands(app))

    language_handler = CommandHandler("language", handle_language_command)
    app.add_handler(language_handler)

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", ask_for_salon)],
        states={
            CHOOSING_LANGUAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_language_selection)
            ],
            CHOOSING_SALON: [
                CallbackQueryHandler(choose_salon_callback, pattern="^salon_.*")
            ],
            CHOOSING_BARBERS: [
                CallbackQueryHandler(handle_barber_selection, pattern="^barber_.*")
            ],
            CHOOSING_SERVICES: [
                CommandHandler("services", choose_services),
                CallbackQueryHandler(handle_service_selection, pattern="^(svc_\\d+|services_done)$"),
                CallbackQueryHandler(handle_change_barber, pattern="^change_barber$")
            ],
            CHOOSING_DATE: [
                CallbackQueryHandler(
                    handle_day_selection, 
                    pattern="^(day_\\d{4}-\\d{2}-\\d{2}|change_day|change_services)$"
                )
            ],
            CHOOSING_HOUR: [
                CallbackQueryHandler(
                    handle_hour_selection, 
                    pattern="^(hour_\\d+|change_day|change_services)$"
                )
            ],
            CHOOSING_MINUTES: [
                CallbackQueryHandler(
                    handle_minute_selection, 
                    pattern="^(min_\\d+:\\d{2}|change_hour|change_services)$"
                )
            ],
            CONFIRM_BOOKING: [
                CallbackQueryHandler(confirm_booking, pattern="^confirm_booking$"),
                CallbackQueryHandler(cancel_booking, pattern="^cancel_booking$")
            ],
            ASK_TG_PHONE: [
                MessageHandler(filters.CONTACT | filters.TEXT, handle_telegram_phone)
            ]
        },
        fallbacks=[
            CommandHandler("start", ask_for_salon)
        ],
        allow_reentry=True,
        per_user=True,
        per_chat=False
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
