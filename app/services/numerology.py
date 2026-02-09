from __future__ import annotations

import datetime as _dt


def sum_digits(s: str) -> int:
    return sum(int(ch) for ch in s if ch.isdigit())


def reduce_to_1_9(n: int) -> int:
    """
    Сводим число к одной цифре 1..9 (цифровой корень).
    Пример: 33 -> 3+3=6.
    """
    n = abs(int(n))
    if n == 0:
        return 0
    return 9 if (n % 9 == 0) else (n % 9)


def validate_date(day: int, month: int, year: int) -> bool:
    try:
        _dt.date(year, month, day)
        return True
    except ValueError:
        return False


def calc_consciousness(day: int, month: int, year: int) -> int:
    """
    Число сознания (день рождения):
    - если день 1..9 => число сознания = день
    - если день 10..31 => суммируем цифры дня и сводим к 1..9
      пример: 15 -> 1+5 = 6
    """
    return reduce_to_1_9(sum_digits(f"{day:02d}"))


def calc_mission(day: int, month: int, year: int) -> int:
    """
    Число миссии (по всей дате рождения):
    Складываем все цифры даты ДД.ММ.ГГГГ и сводим к одной цифре 1..9.
    Пример: 02.07.1977 -> 0+2+0+7+1+9+7+7 = 33 -> 3+3 = 6
    """
    base = sum_digits(f"{day:02d}{month:02d}{year:04d}")
    return reduce_to_1_9(base)


