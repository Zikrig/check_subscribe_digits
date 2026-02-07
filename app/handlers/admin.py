# app/handlers/admin.py

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
import re

from app.config import settings
from app.services.sheets import update_table
from app.services.replics import get_replic
from app.services.db import SessionLocal, Replic
from app.services.counters import get_counter, reset_counter
from app.services.channels import get_all_channels, toggle_channel, update_channel, delete_channel, get_channel

router = Router()

# Текст для команды /info
INFO_TEXT = (
    "/start — версия для пользователей\n"
    "/info — список команд\n"
    "/table — обновить данные нумерологии из таблицы (кэш)\n"
    "/channels — управление каналами\n"
    "/edit_replics — редактировать реплики/акцию\n"
)

# Состояния для редактирования реплик
class EditReplic(StatesGroup):
    choosing_replic = State()
    editing_text = State()
    waiting_promo_photo = State()

# Состояния для управления каналами
class ChannelManage(StatesGroup):
    choosing_action = State()
    adding_channel = State()
    editing_name = State()
    editing_link = State()
    confirming_delete = State()

@router.message(F.text == "/table")
async def cmd_table(message: Message):
    if not message.from_user.id in settings.ADMINS:
        return
    await update_table()
    await message.answer("Данные нумерологии обновлены в кэше!")

@router.message(F.text == "/info")
async def cmd_info(message: Message):
    if not message.from_user.id in settings.ADMINS:
        return
    await message.answer(INFO_TEXT)

@router.message(F.text == "/edit_replics")
async def cmd_edit_replics(message: Message, state: FSMContext):
    if message.from_user.id not in settings.ADMINS:
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Стартовое сообщение", callback_data="edit_start")],
        [InlineKeyboardButton(text="Сообщение о неподписке", callback_data="edit_not_subbed")],
        [InlineKeyboardButton(text="Приветствие (нумерология)", callback_data="edit_welcome")],
        [InlineKeyboardButton(text="Текст после проверки подписки", callback_data="edit_subs_ok")],
        [InlineKeyboardButton(text="Текст акции", callback_data="edit_promo_text")],
        [InlineKeyboardButton(text="Ссылка акции", callback_data="edit_promo_link")],
        [InlineKeyboardButton(text="Картинка акции", callback_data="edit_promo_photo")],
        [InlineKeyboardButton(text="Назад", callback_data="cancel_edit")]
    ])
    
    await message.answer("Выберите реплику для редактирования:", reply_markup=keyboard)
    await state.set_state(EditReplic.choosing_replic)

@router.callback_query(StateFilter(EditReplic.choosing_replic))
async def choose_replic(callback: CallbackQuery, state: FSMContext):
    if callback.data == "cancel_edit":
        await state.clear()
        await callback.message.edit_text("Редактирование отменено.")
        await callback.message.answer(INFO_TEXT)
        await callback.answer()
        return
    
    replic_map = {
        "edit_start": "start_message",
        "edit_not_subbed": "not_subbed_message",
        "edit_welcome": "welcome_message",
        "edit_subs_ok": "subs_ok_message",
        "edit_promo_text": "promo_text",
        "edit_promo_link": "promo_link",
    }
    
    if callback.data == "edit_promo_photo":
        cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_edit")]
        ])
        await callback.message.edit_text(
            "Отправьте картинку для акции (фото). Я сохраню её и бот будет показывать её в конце.",
            reply_markup=cancel_keyboard
        )
        await state.set_state(EditReplic.waiting_promo_photo)
        await callback.answer()
        return

    replic_name = replic_map.get(callback.data)
    if replic_name:
        current_text = await get_replic(replic_name)
        await state.update_data(replic_name=replic_name)
        
        # Создаем клавиатуру с кнопкой отмены
        cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_edit")]
        ])
        
        await callback.message.edit_text(
            f"Текущий текст: {current_text}\n\nОтправьте новый текст:",
            reply_markup=cancel_keyboard
        )
        await state.set_state(EditReplic.editing_text)
    await callback.answer()


@router.message(StateFilter(EditReplic.waiting_promo_photo))
async def save_promo_photo(message: Message, state: FSMContext):
    if not message.photo:
        await message.answer("Нужно отправить именно фото.")
        return

    file_id = message.photo[-1].file_id

    async with SessionLocal() as session:
        result = await session.execute(select(Replic).where(Replic.name == "promo_photo_file_id"))
        replic = result.scalar_one_or_none()
        if replic:
            replic.text = file_id
        else:
            session.add(Replic(name="promo_photo_file_id", text=file_id))
        await session.commit()

    await message.answer("Картинка акции сохранена!")
    await state.clear()
    await message.answer(INFO_TEXT)

@router.callback_query(StateFilter(EditReplic.editing_text), F.data == "cancel_edit")
async def cancel_edit(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Редактирование отменено.")
    await callback.message.answer(INFO_TEXT)
    await callback.answer()

@router.message(StateFilter(EditReplic.editing_text))
async def save_new_replic(message: Message, state: FSMContext):
    data = await state.get_data()
    replic_name = data["replic_name"]
    new_text = message.text

    async with SessionLocal() as session:
        # Проверяем, существует ли уже запись
        result = await session.execute(
            select(Replic).where(Replic.name == replic_name)
        )
        replic = result.scalar_one_or_none()
        
        if replic:
            # Обновляем существующую запись
            replic.text = new_text
        else:
            # Создаем новую запись
            session.add(Replic(name=replic_name, text=new_text))
        
        await session.commit()

    await message.answer("Реплика успешно обновлена!")
    await state.clear()
    await message.answer(INFO_TEXT)
    
# Управление каналами
@router.message(F.text == "/channels")
async def manage_channels(message: Message):
    if message.from_user.id not in settings.ADMINS:
        return
    
    channels = await get_all_channels()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    
    for channel in channels:
        status = "✅" if channel.is_active else "❌"
        display_name = channel.name or channel.username
        
        button = InlineKeyboardButton(
            text=f"{status} {display_name}",
            callback_data=f"channel_{channel.id}"
        )
        keyboard.inline_keyboard.append([button])
    add_button = InlineKeyboardButton(text="➕ Добавить канал", callback_data="add_channel")
    keyboard.inline_keyboard.append([add_button])
    back_button = InlineKeyboardButton(text="⬅️ Назад", callback_data="cancel_channels")
    keyboard.inline_keyboard.append([back_button])
    
    await message.answer("Управление каналами:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("toggle_"))
async def channel_toggle_handler(callback: CallbackQuery):
    channel_id = int(callback.data.split("_")[1])
    success = await toggle_channel(channel_id)
    
    if success:
        # Обновляем сообщение с новой информацией
        channel = await get_channel(channel_id)
        status_btn_text = "❌ Деактивировать" if channel.is_active else "✅ Активировать"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=status_btn_text, callback_data=f"toggle_{channel_id}")],
            [InlineKeyboardButton(text="✏️ Изменить название", callback_data=f"edit_name_{channel_id}")],
            [InlineKeyboardButton(text="🔗 Изменить ссылку", callback_data=f"edit_link_{channel_id}")],
            [InlineKeyboardButton(text="🗑️ Удалить канал", callback_data=f"delete_{channel_id}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="cancel_channels")]
        ])
        
        await callback.message.edit_text(
            f"Управление каналом:\n\n"
            f"ID: {channel.id}\n"
            f"Username: {channel.username}\n"
            f"Название: {channel.name or 'Не задано'}\n"
            f"Ссылка: {channel.link or 'Не задана'}\n"
            f"Статус: {'Активен' if channel.is_active else 'Неактивен'}",
            reply_markup=keyboard
        )
    
    await callback.answer()

@router.callback_query(F.data.startswith("edit_name_"))
async def channel_edit_name_handler(callback: CallbackQuery, state: FSMContext):
    channel_id = int(callback.data.split("_")[2])
    await state.update_data(channel_id=channel_id)
    await state.set_state(ChannelManage.editing_name)
    
    await callback.message.edit_text(
        "Введите новое название канала:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data=f"channel_{channel_id}")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_link_"))
async def channel_edit_link_handler(callback: CallbackQuery, state: FSMContext):
    channel_id = int(callback.data.split("_")[2])
    await state.update_data(channel_id=channel_id)
    await state.set_state(ChannelManage.editing_link)
    
    await callback.message.edit_text(
        "Введите новую ссылку канала (должна начинаться с https:// или http://):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data=f"channel_{channel_id}")]
        ])
    )
    await callback.answer()

@router.callback_query(F.data.startswith("delete_"))
async def channel_delete_handler(callback: CallbackQuery, state: FSMContext):
    channel_id = int(callback.data.split("_")[1])
    await state.update_data(channel_id=channel_id)
    await state.set_state(ChannelManage.confirming_delete)
    
    channel = await get_channel(channel_id)
    await callback.message.edit_text(
        f"Вы уверены, что хотите удалить канал {channel.name or channel.username}?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_delete_{channel_id}")],
            [InlineKeyboardButton(text="❌ Нет", callback_data=f"channel_{channel_id}")]
        ])
    )
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_delete_"))
async def channel_confirm_delete_handler(callback: CallbackQuery, state: FSMContext):
    channel_id = int(callback.data.split("_")[2])
    
    success = await delete_channel(channel_id)
    if success:
        await callback.message.edit_text("Канал успешно удален!")
        await manage_channels(callback.message)
    else:
        await callback.answer("Ошибка при удалении канала")
    
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "channel_back")
async def channel_back_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки Назад в управлении каналами"""
    await state.clear()
    await manage_channels(callback.message)
    await callback.answer()

@router.callback_query(F.data == "cancel_channels")
async def cancel_channels_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик отмены управления каналами"""
    await state.clear()
    await callback.message.edit_text("Управление каналами завершено.")
    await callback.message.answer(INFO_TEXT)
    await callback.answer()


@router.callback_query(StateFilter(ChannelManage.editing_name), F.data.startswith("channel_"))
async def cancel_edit_name(callback: CallbackQuery, state: FSMContext):
    """Отмена редактирования названия канала"""
    await state.clear()
    channel_id = int(callback.data.split("_")[1])
    await channel_action_handler(callback, state)
    await callback.answer()

@router.callback_query(StateFilter(ChannelManage.editing_link), F.data.startswith("channel_"))
async def cancel_edit_link(callback: CallbackQuery, state: FSMContext):
    
    """Отмена редактирования ссылки канала"""
    await state.clear()
    channel_id = int(callback.data.split("_")[1])
    await channel_action_handler(callback, state)
    await callback.answer()
    
    
@router.callback_query(F.data.startswith("channel_"))
async def channel_action_handler(callback: CallbackQuery, state: FSMContext):
    if callback.data == "channel_back":
        # Обрабатываем кнопку "Назад"
        await manage_channels(callback.message)
        await callback.answer()
        return
        
    parts = callback.data.split("_")
    channel_id = int(parts[1])
    
    # Получаем информацию о канале
    channel = await get_channel(channel_id)
    if not channel:
        await callback.answer("Канал не найден")
        return
    
    await state.update_data(channel_id=channel_id)
    
    # Создаем клавиатуру для управления каналом
    status_btn_text = "❌ Деактивировать" if channel.is_active else "✅ Активировать"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=status_btn_text, callback_data=f"toggle_{channel_id}")],
        [InlineKeyboardButton(text="✏️ Изменить название", callback_data=f"edit_name_{channel_id}")],
        [InlineKeyboardButton(text="🔗 Изменить ссылку", callback_data=f"edit_link_{channel_id}")],
        [InlineKeyboardButton(text="🗑️ Удалить канал", callback_data=f"delete_{channel_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="cancel_channels")]
    ])
    
    await callback.message.edit_text(
        f"Управление каналом:\n\n"
        f"ID: {channel.id}\n"
        f"Username: {channel.username}\n"
        f"Название: {channel.name or 'Не задано'}\n"
        f"Ссылка: {channel.link or 'Не задана'}\n"
        f"Статус: {'Активен' if channel.is_active else 'Неактивен'}",
        reply_markup=keyboard
    )
    await callback.answer()


@router.message(StateFilter(ChannelManage.editing_name))
async def process_edit_name(message: Message, state: FSMContext):
    data = await state.get_data()
    channel_id = data.get("channel_id")
    new_name = message.text

    success = await update_channel(channel_id, name=new_name)
    if success:
        await message.answer("Название канала успешно обновлено!")
    else:
        await message.answer("Ошибка при обновлении названия канала.")

    await state.clear()
    await manage_channels(message)

@router.message(StateFilter(ChannelManage.editing_link))
async def process_edit_link(message: Message, state: FSMContext):
    data = await state.get_data()
    channel_id = data.get("channel_id")
    new_link = message.text

    try:
        success = await update_channel(channel_id, link=new_link)
        if success:
            await message.answer("Ссылка канала успешно обновлена!")
        else:
            await message.answer("Ошибка при обновлении ссылки канала.")
    except ValueError as e:
        await message.answer(str(e))

    await state.clear()
    await manage_channels(message)


# Update the cancel handlers to properly clear state
@router.callback_query(StateFilter(ChannelManage.editing_name), F.data.startswith("channel_"))
async def cancel_edit_name(callback: CallbackQuery, state: FSMContext):
    """Отмена редактирования названия канала"""
    await state.clear()
    channel_id = int(callback.data.split("_")[1])
    await channel_action_handler(callback, state)

@router.callback_query(StateFilter(ChannelManage.editing_link), F.data.startswith("channel_"))
async def cancel_edit_link(callback: CallbackQuery, state: FSMContext):
    """Отмена редактирования ссылки канала"""
    await state.clear()
    channel_id = int(callback.data.split("_")[1])
    await channel_action_handler(callback, state)
    

@router.callback_query(F.data == "reset_counter")
async def reset_counter_handler(callback: CallbackQuery):
    if callback.from_user.id not in settings.ADMINS:
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="confirm_reset")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="cancel_reset")]
    ])
    
    await callback.message.edit_text(
        "Вы уверены, что хотите обнулить счетчик?",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "confirm_reset")
async def confirm_reset_handler(callback: CallbackQuery):
    if callback.from_user.id not in settings.ADMINS:
        return
    
    await reset_counter()
    await callback.message.edit_text("Счетчик обнулен!")
    await callback.answer()

@router.callback_query(F.data == "cancel_reset")
async def cancel_reset_handler(callback: CallbackQuery):
    await callback.message.edit_text("Отмена обнуления счетчика")
    await callback.answer()
    
    
@router.callback_query(F.data == "add_channel")
async def add_channel_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ChannelManage.adding_channel)
    await callback.message.edit_text(
        "Введите данные канала в формате:\n"
        "<code>id username [name] [link]</code>\n\n"
        "Пример:\n"
        "<code>-10012345678 channel_username Название канала https://t.me/channel_username</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_channels")]
        ])
    )
    await callback.answer()

# Обработчик сообщения с данными нового канала
@router.message(StateFilter(ChannelManage.adding_channel))
async def process_add_channel(message: Message, state: FSMContext):
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("Ошибка: недостаточно данных. Нужно как минимум id и username.")
            return

        channel_id = int(parts[0])
        username = parts[1]
        name = ' '.join(parts[2:]) if len(parts) > 2 else None
        link = None

        # Проверяем, есть ли ссылка в сообщении
        for part in parts[2:]:
            if part.startswith(('http://', 'https://', 't.me/')):
                link = part
                # Убираем ссылку из названия
                if name:
                    name = name.replace(part, '').strip()
                break

        from app.services.channels import add_channel
        success = await add_channel(channel_id, username, name, link)
        
        if success:
            await message.answer("Канал успешно добавлен!")
        else:
            await message.answer("Ошибка: канал с таким ID уже существует.")
            
    except ValueError:
        await message.answer("Ошибка: ID канала должен быть числом.")
    except Exception as e:
        await message.answer(f"Ошибка при добавлении канала: {str(e)}")
    
    await state.clear()
    await manage_channels(message)