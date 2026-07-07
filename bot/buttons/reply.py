from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def location_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Joylashuvimni yuborish", request_location=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )