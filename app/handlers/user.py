import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.keyboards import (
    subscription_keyboard,
    confirm_date_keyboard,
    next_keyboard,
    share_keyboard,
    promo_keyboard,
    share_and_promo_keyboard,
    day_keyboard,
    month_keyboard,
)
from app.config import settings
from app.services.replics import get_replic
from app.services.channels import get_all_channels
from app.services.numerology import (
    validate_date,
    calc_consciousness,
    calc_mission,
)
from app.services.sheets import get_cached_table, update_table

router = Router()


class NumerologyFlow(StatesGroup):
    waiting_name = State()
    waiting_day = State()
    waiting_month = State()
    waiting_year = State()
    confirming_date = State()
    showing = State()


@router.message(F.text == "/start")
async def start_handler(message: Message, state: FSMContext):
    await state.clear()
    kb = await subscription_keyboard(message.bot, message.from_user.id)
    start_text = await get_replic("start_message")
    await message.answer(start_text, reply_markup=kb)
    if message.from_user.id in settings.ADMINS:
        await message.answer("Привет, админ! Используй /info для списка команд.")


async def _all_subscribed(bot, user_id: int) -> bool:
    channels = await get_all_channels()
    for ch in channels:
        if not ch.is_active:
            continue
        try:
            member = await bot.get_chat_member(ch.id, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except Exception:
            return False
    return True


@router.callback_query(F.data == "check_subs")
async def check_subs_callback(callback: CallbackQuery, state: FSMContext):
    kb = await subscription_keyboard(callback.bot, callback.from_user.id)

    if not await _all_subscribed(callback.bot, callback.from_user.id):
        not_subbed_text = await get_replic("not_subbed_message")
        await callback.message.edit_text(not_subbed_text, reply_markup=kb)
        await callback.answer()
        return

    # Подписки ок — начинаем нумерологический сценарий
    ok_text = await get_replic("subs_ok_message")
    ask_name = await get_replic("ask_name")
    await callback.message.edit_text(ok_text)
    await callback.message.answer(ask_name)
    await state.set_state(NumerologyFlow.waiting_name)
    await callback.answer()


@router.message(StateFilter(NumerologyFlow.waiting_name))
async def got_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    if not name:
        await message.answer("Напиши, пожалуйста, свое имя.")
        return

    await state.update_data(name=name)
    ask_day = await get_replic("ask_day")
    await message.answer(ask_day.format(name=name), reply_markup=day_keyboard())
    await state.set_state(NumerologyFlow.waiting_day)


@router.callback_query(StateFilter(NumerologyFlow.waiting_day), F.data.startswith("pick_day_"))
async def got_day_button(callback: CallbackQuery, state: FSMContext):
    try:
        day = int(callback.data.split("_")[2])
    except Exception:
        await callback.answer()
        return

    if not (1 <= day <= 31):
        await callback.answer()
        return

    data = await state.get_data()
    name = data["name"]
    await state.update_data(day=day)
    ask_month = await get_replic("ask_month")
    await callback.message.edit_text(ask_month.format(name=name), reply_markup=month_keyboard())
    await state.set_state(NumerologyFlow.waiting_month)
    await callback.answer()


@router.message(StateFilter(NumerologyFlow.waiting_day))
async def got_day(message: Message, state: FSMContext):
    await message.answer("Пожалуйста, выбери день рождения на кнопках ниже.", reply_markup=day_keyboard())


@router.callback_query(StateFilter(NumerologyFlow.waiting_month), F.data.startswith("pick_month_"))
async def got_month_button(callback: CallbackQuery, state: FSMContext):
    try:
        month = int(callback.data.split("_")[2])
    except Exception:
        await callback.answer()
        return

    if not (1 <= month <= 12):
        await callback.answer()
        return

    await state.update_data(month=month)
    ask_year = await get_replic("ask_year")
    await callback.message.edit_text(ask_year)
    await state.set_state(NumerologyFlow.waiting_year)
    await callback.answer()


@router.message(StateFilter(NumerologyFlow.waiting_month))
async def got_month(message: Message, state: FSMContext):
    await message.answer("Пожалуйста, выбери месяц рождения на кнопках ниже.", reply_markup=month_keyboard())


@router.message(StateFilter(NumerologyFlow.waiting_year))
async def got_year(message: Message, state: FSMContext):
    txt = (message.text or "").strip()
    if not (txt.isdigit() and len(txt) == 4):
        await message.answer("Год рождения нужен в формате ГГГГ (например: 1998).")
        return

    year = int(txt)
    current = __import__("datetime").date.today().year
    if not (1900 <= year <= current):
        await message.answer("Проверь год рождения (должен быть реальным).")
        return

    data = await state.get_data()
    name = data["name"]
    day = data["day"]
    month = data["month"]

    if not validate_date(day, month, year):
        await message.answer("Похоже, дата получилась некорректной. Давай заново: напиши день рождения.")
        await state.set_state(NumerologyFlow.waiting_day)
        return

    await state.update_data(year=year)
    date_str = f"{day:02d}.{month:02d}.{year:04d}"
    confirm_text = await get_replic("confirm_date")
    await message.answer(confirm_text.format(date=date_str), reply_markup=confirm_date_keyboard())
    await state.set_state(NumerologyFlow.confirming_date)


@router.callback_query(StateFilter(NumerologyFlow.confirming_date), F.data == "dob_confirm_no")
async def dob_confirm_no(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    name = data.get("name", "")
    await callback.message.edit_text("Хорошо, давай уточним дату. Напиши день рождения еще раз.")
    await state.set_state(NumerologyFlow.waiting_day)
    if name:
        await callback.message.answer((await get_replic("ask_day")).format(name=name), reply_markup=day_keyboard())
    await callback.answer()


@router.callback_query(StateFilter(NumerologyFlow.confirming_date), F.data == "dob_confirm_yes")
async def dob_confirm_yes(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    name = data["name"]
    day = data["day"]
    month = data["month"]
    year = data["year"]

    cons_num = calc_consciousness(day, month, year)
    mission_num = calc_mission(day, month, year)

    table = get_cached_table()
    if table is None:
        table = await update_table()

    cons_desc = table.consciousness.get(cons_num, "")
    mission_desc = table.mission.get(mission_num, "")
    combo_desc = table.combination.get((cons_num, mission_num), "")

    await state.update_data(
        cons_num=cons_num,
        mission_num=mission_num,
        combo_desc=combo_desc,
        cons_desc=cons_desc,
        mission_desc=mission_desc,
    )

    text = await get_replic("consciousness_message")
    # Оставляем подтверждение даты в истории (убираем только кнопки),
    # а результат отправляем отдельным сообщением, чтобы можно было перечитать.
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await callback.message.answer(
        text.format(name=name, num=cons_num, desc=cons_desc),
        reply_markup=next_keyboard("mission"),
    )
    await state.set_state(NumerologyFlow.showing)
    await callback.answer()


@router.callback_query(StateFilter(NumerologyFlow.showing), F.data == "next_mission")
async def show_mission(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    name = data["name"]
    mission_num = data["mission_num"]
    mission_desc = data["mission_desc"]

    text = await get_replic("mission_message")
    # Сохраняем прошлое сообщение, убираем кнопки и отправляем новое
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await callback.message.answer(
        text.format(name=name, num=mission_num, desc=mission_desc),
        reply_markup=next_keyboard("combo"),
    )
    await callback.answer()


@router.callback_query(StateFilter(NumerologyFlow.showing), F.data == "next_combo")
async def show_combo(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    combo_desc = data.get("combo_desc", "")
    text = await get_replic("combo_message")
    bot_username = (await callback.bot.get_me()).username or ""
    
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    # Сообщение о сочетании + кнопка "Поделиться ботом"
    await callback.message.answer(
        text.format(desc=combo_desc),
        reply_markup=share_keyboard(bot_username),
    )
    
    # Задержка 10 секунд перед отправкой сообщения об акции
    await asyncio.sleep(10)
    
    # Автоматически отправляем сообщение про акцию
    promo_intro = await get_replic("promo_intro_message")
    promo_text = (await get_replic("promo_text")).strip()
    promo_link = (await get_replic("promo_link")).strip()
    promo_photo = (await get_replic("promo_photo_file_id")).strip()
    
    # Текст "Не забудь воспользоваться приятной акцией..."
    await callback.message.answer(promo_intro)
    
    # Картинка, описание, кнопка "Акция" (в такой последовательности)
    if promo_photo:
        try:
            # Картинка с описанием (если есть) и кнопкой "Акция" (если есть ссылка)
            caption = promo_text if promo_text else None
            kb = promo_keyboard(promo_link) if promo_link else None
            await callback.message.answer_photo(photo=promo_photo, caption=caption, reply_markup=kb)
        except Exception:
            # Если file_id битый — отправляем текстом
            if promo_text:
                kb = promo_keyboard(promo_link) if promo_link else None
                await callback.message.answer(promo_text, reply_markup=kb)
            elif promo_link:
                await callback.message.answer("Акция:", reply_markup=promo_keyboard(promo_link))
    else:
        # Нет картинки — отправляем описание и кнопку
        if promo_text:
            kb = promo_keyboard(promo_link) if promo_link else None
            await callback.message.answer(promo_text, reply_markup=kb)
        elif promo_link:
            await callback.message.answer("Акция:", reply_markup=promo_keyboard(promo_link))
    
    await state.clear()
    await callback.answer()


# Обработчик next_final больше не используется, но оставляем на случай если где-то осталась ссылка
@router.callback_query(StateFilter(NumerologyFlow.showing), F.data == "next_final")
async def show_final(callback: CallbackQuery, state: FSMContext):
    # Перенаправляем на combo (новый финал)
    await show_combo(callback, state)
