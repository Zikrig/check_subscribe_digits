# /app/replics.py

from sqlalchemy import select
from app.services.db import SessionLocal, Replic

async def get_replic(name: str) -> str:
    async with SessionLocal() as session:
        result = await session.execute(
            select(Replic).where(Replic.name == name)
        )
        replic = result.scalar_one_or_none()
        if replic:
            return replic.text
        
        # Fallback to default values if not found in DB
        default_replics = {
            "start_message": (
                "Привет, дорогая!\n"
                "Чтобы узнать твои тип личности и твою жизненную миссию по нумерологии сообщи свою дату рождения. "
                "Перед этим тебе нужно подписаться на мой канал.\n"
            ),
            "subs_ok_message": "Спасибо! Подписка подтверждена ✅",
            "welcome_message": (
                "Привет, дорогая!\n"
                "Чтобы узнать твои тип личности и твою жизненную миссию по нумерологии сообщи свою дату рождения. "
                "Перед этим тебе нужно подписаться на мой канал.\n"
            ),
            "ask_name": "Сперва давай познакомимся. Напиши свое имя.",
            "ask_day": "{name}, какого числа твой день рождения? Выбери на кнопках ниже.",
            "ask_month": "{name}, в каком месяце ты родилась? Выбери на кнопках ниже.",
            "ask_year": "Теперь введи свой год рождения в формате ГГГГ.",
            "confirm_date": "Твоя полная дата рождения {date}?",
            "not_subbed_message": "Похоже, ты ещё не подписан на все каналы. Проверь и нажми кнопку снова.",
            "consciousness_message": (
                "{name}, твое число сознания {num}\n\n"
                "{desc}\n\n"
                "Нажми кнопку Далее, чтобы узнать свою Миссию, которая проявляется после достижения 30-летнего возраста."
            ),
            "mission_message": (
                "{name}, твоя миссия {num}\n\n"
                "{desc}\n\n"
                "Нажми кнопку Далее, чтобы узнать о том, как сочетаются число Сознания и число Миссии."
            ),
            "combo_message": "{desc}\n\n{final}",
            "final_message": (
                "{name}, надеюсь тебе понравилось твое описание по нумерологии.\n"
                "Поделись этой ссылкой с друзьями и близкими, чтобы они узнали, что о них говорят цифры.\n\n"
                "Не забудь воспользоваться приятной акцией для моих подписчиков."
            ),
            "promo_text": "",
            "promo_link": "",
            "promo_photo_file_id": "",
        }
        return default_replics.get(name, "")