from __future__ import annotations

import datetime as _dt


def sum_digits(s: str) -> int:
    return sum(int(ch) for ch in s if ch.isdigit())


def validate_date(day: int, month: int, year: int) -> bool:
    try:
        _dt.date(year, month, day)
        return True
    except ValueError:
        return False


def calc_consciousness(day: int, month: int, year: int) -> int:
    """
    Число сознания (новая формула):
    - берём сумму цифр дня рождения
    - прибавляем 7
    - берём остаток от деления на 10

    Примечание: так как описания в таблице заданы для 1..9, остаток 0 переводим в 9.
    """
    base = sum_digits(f"{day:02d}")
    r = (base + 7) % 9
    return r


def calc_mission(day: int, month: int, year: int) -> int:
    """
    Число миссии (новая формула):
    - берём сумму цифр всей даты рождения (ддммгггг)
    - прибавляем 5
    - берём остаток от деления на 9

    Примечание: так как описания в таблице заданы для 1..9, остаток 0 переводим в 9.
    """
    base = sum_digits(f"{day:02d}{month:02d}{year:04d}")
    r = (base + 5) % 9
    return r


