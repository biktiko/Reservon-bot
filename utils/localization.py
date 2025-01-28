# utils/localization.py
LANGUAGES = {
    "Русский": "ru",
    "Հայերեն": "hy",
    "English": "en"
}

DEFAULT_LANGUAGE = "ru"

translations = {
    "ru": {
        "welcome": "Добро пожаловать в Reservon Bot!",
        "choose_language": "Выберите язык:",
        "language_set": "Язык установлен: Русский",
        "ask_salon": "Выберите салон:",
        "ask_option": "Что хотите сделать?",
        "option_services": "Выбрать услуги",
        "option_barbers": "Выбрать мастера",
        "option_date": "Выбрать дату и время",
        "confirm_services": "Услуги выбраны. Подтвердить?",
        "confirm_barbers": "Мастера выбраны. Подтвердить?",
        "ask_date": "Выберите день (пример: 2025-01-12):",
        "ask_hour": "Выберите час (0-23):",
        "ask_minutes": "Выберите минуты (например, 05, 10, 15, ...):",
        "date_chosen": "Дата и время выбраны: ",
        "services_chosen": "Услуги выбраны: ",
        "barber_chosen": "Вы выбрали мастера: ",
        "salon_chosen": "Салон выбран: ",
        "back_to_menu": "Вернуться в меню",
        "done": "Завершить",
        "final_confirmation": "Подтвердить бронирование?",
        "booking_done": "Бронирование успешно!",
        "language_prompt": "Пожалуйста, выберите язык:",
        "select_language_error": "Пожалуйста, выберите доступный язык.",
        "menu": "Главное меню:",
        "menu_book_service": "Забронировать услугу",
        "menu_view_bookings": "Просмотреть бронирования",
        "menu_change_language": "Изменить язык"
    },
    "hy": {
        "welcome": "Բարի գալուստ Reservon Bot!",
        "choose_language": "Ընտրեք լեզուն:",
        "language_set": "Լեզուն ընտրված է: Հայերեն",
        "ask_salon": "Ընտրեք սալոնը:",
        "ask_option": "Ի՞նչ եք ուզում անել:",
        "option_services": "Ընտրել ծառայություններ",
        "option_barbers": "Ընտրեք վարպետին",
        "option_date": "Ընտրել ամսաթիվ եւ ժամ",
        "confirm_services": "Ծառայություններն ընտրված են: Հաստատե՞լ",
        "confirm_barbers": "Վարպետները ընտրված են: Հաստատե՞լ",
        "ask_date": "Ընտրեք օրը (օր. 2025-01-12):",
        "ask_hour": "Ընտրեք ժամը (0-23):",
        "ask_minutes": "Ընտրեք րոպեները (օր. 05, 10, 15, ...):",
        "date_chosen": "Ամսաթիվը եւ ժամը ընտրված են: ",
        "services_chosen": "Ծառայություններն ընտրված են: ",
        "barber_chosen": "Դուք ընտրել եք - ",
        "salon_chosen": "Սալոնը ընտրված է: ",
        "back_to_menu": "Վերադառնալ մենյու",
        "done": "Ավարտել",
        "final_confirmation": "Հաստատե՞լ ամրագրումը",
        "booking_done": "Ամրագրումը հաջողվեց!",
        "language_prompt": "Խնդրում ենք ընտրել լեզուն:",
        "select_language_error": "Խնդրում ենք ընտրել հասանելի լեզուն.",
        "menu": "Գլխավոր մենյու:",
        "menu_book_service": "Ամրագրել ծառայություն",
        "menu_view_bookings": "Տեսնել ամրագրումները",
        "menu_change_language": "Փոխել լեզուն"
    },
    "en": {
        "welcome": "Welcome to Reservon Bot!",
        "choose_language": "Choose a language:",
        "language_set": "Language set: English",
        "ask_salon": "Choose a salon:",
        "ask_option": "What do you want to do?",
        "option_services": "Choose services",
        "option_barbers": "Choose barber",
        "option_date": "Choose date & time",
        "confirm_services": "Services chosen. Confirm?",
        "confirm_barbers": "Barbers chosen. Confirm?",
        "ask_date": "Choose a day (e.g. 2025-01-12):",
        "ask_hour": "Choose hour (0-23):",
        "ask_minutes": "Choose minutes (e.g. 05, 10, 15, ...):",
        "date_chosen": "Date & time chosen: ",
        "services_chosen": "Services chosen: ",
        "barber_chosen": "Barber chosen: ",
        "salon_chosen": "Salon chosen: ",
        "back_to_menu": "Back to menu",
        "done": "Done",
        "final_confirmation": "Confirm booking?",
        "booking_done": "Booking successful!",
        "language_prompt": "Please select a language:",
        "select_language_error": "Please select a valid language.",
        "menu": "Main Menu:",
        "menu_book_service": "Book a Service",
        "menu_view_bookings": "View Bookings",
        "menu_change_language": "Change Language"
    }
}

SHORT_DAYS = {
    "ru": ["пн", "вт", "ср", "чт", "пт", "сб", "вс"],
    "hy": ["երկ", "երք", "չրք", "հնգ", "ուրբ", "շբթ", "կիր"],
    "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
}

def get_texts(lang_code):
    return translations.get(lang_code, translations[DEFAULT_LANGUAGE])
