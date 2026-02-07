"""
ВАЖНО: этот модуль работает ТОЛЬКО на чтение Google Sheets.
Никаких sh.clear()/append_row()/update() и т.п. здесь быть не должно.

Таблица используется как справочник нумерологических описаний:
- B2:B10: описания "числа сознания" 1..9
- D2:D10: описания "миссии" 1..9
- F2:F82: описания сочетаний (1,1) .. (1,9), (2,1) .. (9,9) — всего 81 строка
"""

import asyncio
from dataclasses import dataclass

import gspread

from app.config import settings

gc = gspread.service_account(filename="creds.json")


@dataclass(frozen=True)
class NumerologyTable:
    consciousness: dict[int, str]  # 1..9
    mission: dict[int, str]  # 1..9
    combination: dict[tuple[int, int], str]  # (1..9, 1..9)


_CACHE: NumerologyTable | None = None


def _flatten_1col(values: list[list[str]]) -> list[str]:
    # gspread returns list[list[str]] even for 1-column ranges
    out: list[str] = []
    for row in values:
        out.append(str(row[0]) if row else "")
    return out


async def update_table() -> NumerologyTable:
    """
    Обновить кэш данных нумерологии из Google Sheet (ТОЛЬКО ЧТЕНИЕ).
    Оставляем имя update_table, чтобы не ломать импорты в админке (/table).
    """
    global _CACHE

    if not settings.SHEET_ID:
        raise RuntimeError("SHEET_ID не задан в окружении")

    # gspread синхронный — уводим в thread, чтобы не блокировать event loop
    def _read() -> NumerologyTable:
        sh = gc.open_by_key(settings.SHEET_ID).sheet1

        cons = _flatten_1col(sh.get("B2:B10"))
        miss = _flatten_1col(sh.get("D2:D10"))
        comb = _flatten_1col(sh.get("F2:F82"))

        if len(cons) != 9 or len(miss) != 9 or len(comb) != 81:
            raise RuntimeError(
                f"Неверный размер диапазонов: B2:B10={len(cons)}, D2:D10={len(miss)}, F2:F82={len(comb)}"
            )

        consciousness = {i + 1: cons[i] for i in range(9)}
        mission = {i + 1: miss[i] for i in range(9)}
        combination: dict[tuple[int, int], str] = {}
        idx = 0
        for c in range(1, 10):
            for m in range(1, 10):
                combination[(c, m)] = comb[idx]
                idx += 1

        return NumerologyTable(consciousness=consciousness, mission=mission, combination=combination)

    _CACHE = await asyncio.to_thread(_read)
    return _CACHE


def get_cached_table() -> NumerologyTable | None:
    return _CACHE


async def periodic_update(interval_sec: int = 600):
    """
    Периодическое обновление кэша (ТОЛЬКО ЧТЕНИЕ). Можно отключить, если не нужно.
    """
    while True:
        try:
            await update_table()
        except Exception:
            # не падаем из-за таблицы — админ сможет обновить вручную
            pass
        await asyncio.sleep(interval_sec)
