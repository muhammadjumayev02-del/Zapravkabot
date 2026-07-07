from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def maps_inline_keyboard(lat: float, lon: float) -> InlineKeyboardMarkup:
    maps_link = f"https://www.google.com/maps?q={lat},{lon}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗺 Google Maps'da ochish", url=maps_link)]
        ]
    )