import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardRemove

from bot.buttons.inline import maps_inline_keyboard
from bot.buttons.reply import location_keyboard
from bot.gas_finder import find_nearest_station

logger = logging.getLogger(__name__)

router = Router(name="main")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Assalomu alaykum! 👋\n\n"
        "Men sizga eng yaqin *propan (LPG)* yoki *metan (CNG)* "
        "zapravkasini topib beraman.\n\n"
        "Buning uchun pastdagi tugma orqali joylashuvingizni yuboring.",
        reply_markup=location_keyboard(),
    )


@router.message(F.location)
async def handle_location(message: Message) -> None:
    loc = message.location

    searching_msg = await message.answer(
        "🔍 Yaqin atrofdagi zapravkalar qidirilmoqda, biroz kuting...",
        reply_markup=ReplyKeyboardRemove(),
    )

    station = await find_nearest_station(loc.latitude, loc.longitude)

    if station is None:
        try:
            await searching_msg.edit_text(
                "😔 Afsuski, atrofingizda (60 km radiusda) propan/metan "
                "zapravkasi topilmadi. Iltimos, boshqa joydan urinib ko'ring."
            )
        except TelegramBadRequest as exc:
            logger.warning("Xabarni tahrirlab bo'lmadi: %s", exc)
            await message.answer(
                "😔 Afsuski, atrofingizda (60 km radiusda) propan/metan "
                "zapravkasi topilmadi. Iltimos, boshqa joydan urinib ko'ring."
            )
        return

    dist_text = (
        f"{station['distance_km'] * 1000:.0f} m"
        if station["distance_km"] < 1
        else f"{station['distance_km']:.1f} km"
    )

    text = (
        f"✅ Eng yaqin zapravka topildi!\n\n"
        f"⛽ *{station['name']}*\n"
        f"🔧 Yoqilg'i turi: {station['fuel_type']}\n"
        f"📏 Masofa: {dist_text}"
    )

    try:
        await searching_msg.edit_text(
            text,
            reply_markup=maps_inline_keyboard(station["lat"], station["lon"]),
        )
    except TelegramBadRequest as exc:
        logger.warning("Xabarni tahrirlab bo'lmadi: %s", exc)
        await message.answer(
            text,
            reply_markup=maps_inline_keyboard(station["lat"], station["lon"]),
        )

    await message.answer_location(latitude=station["lat"], longitude=station["lon"])


@router.message()
async def handle_other(message: Message) -> None:
    """Lokatsiyadan boshqa har qanday xabarga javob."""
    await message.answer(
        "Iltimos, joylashuvingizni pastdagi tugma orqali yuboring 👇",
        reply_markup=location_keyboard(),
    )