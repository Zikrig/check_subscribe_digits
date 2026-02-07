from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.config import settings
from app.services.channels import get_all_channels

async def subscription_keyboard(bot, user_id: int):
    buttons = []
    channels = await get_all_channels()
    
    for ch in channels:
        if not ch.is_active:
            continue
            
        try:
            member = await bot.get_chat_member(ch.id, user_id)
            subscribed = member.status in ["member", "administrator", "creator"]
        except:
            subscribed = False

        emoji = "✅" if subscribed else "❌"
        display_name = ch.name or ch.username  # Используем name если есть, иначе username
        url = ch.link or f"https://t.me/{ch.username.lstrip('@')}"  # Используем link если есть
        text = f"{emoji} {display_name}"
        url_button = InlineKeyboardButton(text=text, url=url)
        buttons.append([url_button])

    check_button = InlineKeyboardButton(text="Я подписался", callback_data="check_subs")
    buttons.append([check_button])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_date_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да", callback_data="dob_confirm_yes")],
            [InlineKeyboardButton(text="❌ Нет", callback_data="dob_confirm_no")],
        ]
    )


def next_keyboard(step: str):
    """
    step: "mission" | "combo" | "final"
    """
    mapping = {
        "mission": "next_mission",
        "combo": "next_combo",
        "final": "next_final",
    }
    cb = mapping.get(step)
    if not cb:
        raise ValueError("Unknown step")
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Далее", callback_data=cb)]])


def share_and_promo_keyboard(bot_username: str, promo_link: str | None = None):
    share_url = f"https://t.me/share/url?url=https://t.me/{bot_username.lstrip('@')}"
    rows = [[InlineKeyboardButton(text="Поделиться ботом", url=share_url)]]
    if promo_link:
        rows.append([InlineKeyboardButton(text="Акция", url=promo_link)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def day_keyboard():
    """
    1..31 на кнопках. Callback data: pick_day_XX
    """
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for d in range(1, 32):
        row.append(InlineKeyboardButton(text=str(d), callback_data=f"pick_day_{d}"))
        if len(row) == 7:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def month_keyboard():
    """
    Месяцы на кнопках. Callback data: pick_month_XX
    """
    months = [
        (1, "Январь"),
        (2, "Февраль"),
        (3, "Март"),
        (4, "Апрель"),
        (5, "Май"),
        (6, "Июнь"),
        (7, "Июль"),
        (8, "Август"),
        (9, "Сентябрь"),
        (10, "Октябрь"),
        (11, "Ноябрь"),
        (12, "Декабрь"),
    ]

    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for m, title in months:
        row.append(InlineKeyboardButton(text=title, callback_data=f"pick_month_{m}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)