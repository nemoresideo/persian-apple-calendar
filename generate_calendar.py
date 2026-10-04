#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generate Apple Calendar-compatible ICS feeds for Persian (Jalali) dates.

Outputs:
  - calendar.ics       : Persian date only (cleaner)
  - calendar-full.ics  : Persian date + Persian weekday (matches the Instagram example)

No third-party Python package is required.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import json


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"

PERSIAN_MONTHS = [
    "",
    "فروردین",
    "اردیبهشت",
    "خرداد",
    "تیر",
    "مرداد",
    "شهریور",
    "مهر",
    "آبان",
    "آذر",
    "دی",
    "بهمن",
    "اسفند",
]

PERSIAN_WEEKDAYS = {
    0: "دوشنبه",
    1: "سه‌شنبه",
    2: "چهارشنبه",
    3: "پنجشنبه",
    4: "جمعه",
    5: "شنبه",
    6: "یکشنبه",
}

FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def fa_num(value: int | str) -> str:
    return str(value).translate(FA_DIGITS)


def gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    g_day_no = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]

    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621

    gy2 = gy + 1 if gm > 2 else gy

    days = (
        365 * gy
        + (gy2 + 3) // 4
        - (gy2 + 99) // 100
        + (gy2 + 399) // 400
        - 80
        + gd
        + g_day_no[gm - 1]
    )

    jy += 33 * (days // 12053)
    days %= 12053

    jy += 4 * (days // 1461)
    days %= 1461

    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365

    if days < 186:
        jm = 1 + days // 31
        jd = 1 + days % 31
    else:
        jm = 7 + (days - 186) // 30
        jd = 1 + (days - 186) % 30

    return jy, jm, jd


def jalali_year_start_gregorian(jy: int) -> date:
    for gy in (jy + 621, jy + 622):
        for day in range(19, 23):
            candidate = date(gy, 3, day)
            if gregorian_to_jalali(candidate.year, candidate.month, candidate.day) == (jy, 1, 1):
                return candidate
    raise RuntimeError(f"Could not locate start of Jalali year {jy}")


def escape_ics(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", r"\;")
        .replace(",", r"\,")
        .replace("\r\n", r"\n")
        .replace("\n", r"\n")
    )


def fold_ics_line(line: str, max_octets: int = 73) -> list[str]:
    encoded = line.encode("utf-8")
    if len(encoded) <= max_octets:
        return [line]

    parts = []
    current = ""
    current_len = 0
    for ch in line:
        ch_len = len(ch.encode("utf-8"))
        limit = max_octets if not parts else max_octets - 1
        if current and current_len + ch_len > limit:
            parts.append(current)
            current = ch
            current_len = ch_len
        else:
            current += ch
            current_len += ch_len

    if current:
        parts.append(current)

    return [parts[0]] + [" " + p for p in parts[1:]]


def event_lines(
    gdate: date,
    jy: int,
    jm: int,
    jd: int,
    owner_tag: str,
    dtstamp: str,
    kind: str,
) -> list[str]:
    next_day = gdate + timedelta(days=1)
    weekday_fa = PERSIAN_WEEKDAYS[gdate.weekday()]
    month_fa = PERSIAN_MONTHS[jm]

    if kind == "date":
        summary = f"{fa_num(jd)} {month_fa}"
        uid = f"date-{jy:04d}-{jm:02d}-{jd:02d}@{owner_tag}"
    elif kind == "weekday":
        summary = weekday_fa
        uid = f"weekday-{gdate:%Y%m%d}@{owner_tag}"
    else:
        raise ValueError(f"Unknown event kind: {kind}")

    description = f"{weekday_fa}، {fa_num(jd)} {month_fa} {fa_num(jy)}"

    raw = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART;VALUE=DATE:{gdate:%Y%m%d}",
        f"DTEND;VALUE=DATE:{next_day:%Y%m%d}",
        f"SUMMARY:{escape_ics(summary)}",
        f"DESCRIPTION:{escape_ics(description)}",
        "TRANSP:TRANSPARENT",
        "STATUS:CONFIRMED",
        "SEQUENCE:0",
        "END:VEVENT",
    ]

    folded = []
    for line in raw:
        folded.extend(fold_ics_line(line))
    return folded


def calendar_lines(
    *,
    name: str,
    description: str,
    owner_tag: str,
    start_jy: int,
    end_jy: int,
    include_weekday: bool,
) -> list[str]:
    start = jalali_year_start_gregorian(start_jy)
    end = jalali_year_start_gregorian(end_jy + 1)
    dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//{owner_tag}//Persian Apple Calendar//FA",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_ics(name)}",
        f"X-WR-CALDESC:{escape_ics(description)}",
        "X-WR-TIMEZONE:Asia/Tehran",
        "REFRESH-INTERVAL;VALUE=DURATION:PT12H",
        "X-PUBLISHED-TTL:PT12H",
    ]

    current = start
    while current < end:
        jy, jm, jd = gregorian_to_jalali(current.year, current.month, current.day)

        lines.extend(
            event_lines(current, jy, jm, jd, owner_tag, dtstamp, "date")
        )

        if include_weekday:
            lines.extend(
                event_lines(current, jy, jm, jd, owner_tag, dtstamp, "weekday")
            )

        current += timedelta(days=1)

    lines.append("END:VCALENDAR")
    return lines


def write_ics(path: Path, lines: list[str]) -> None:
    path.write_bytes(("\r\n".join(lines) + "\r\n").encode("utf-8"))


def validate_known_dates() -> None:
    checks = {
        (2026, 3, 21): (1405, 1, 1),
        (2026, 10, 3): (1405, 7, 11),
        (2027, 3, 20): (1405, 12, 29),
    }
    for g, expected in checks.items():
        actual = gregorian_to_jalali(*g)
        if actual != expected:
            raise AssertionError(f"Date conversion failed: {g} -> {actual}, expected {expected}")


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    start_jy = int(config["start_jalali_year"])
    end_jy = int(config["end_jalali_year"])
    owner_tag = str(config["owner_tag"]).strip()
    calendar_name = str(config["calendar_name"]).strip()

    validate_known_dates()

    clean_lines = calendar_lines(
        name=calendar_name,
        description=f"تاریخ شمسی {fa_num(start_jy)} تا {fa_num(end_jy)} برای Apple Calendar",
        owner_tag=owner_tag,
        start_jy=start_jy,
        end_jy=end_jy,
        include_weekday=False,
    )
    write_ics(ROOT / "calendar.ics", clean_lines)

    full_lines = calendar_lines(
        name=f"{calendar_name} — کامل",
        description=f"تاریخ شمسی و روز هفته، {fa_num(start_jy)} تا {fa_num(end_jy)}",
        owner_tag=owner_tag,
        start_jy=start_jy,
        end_jy=end_jy,
        include_weekday=True,
    )
    write_ics(ROOT / "calendar-full.ics", full_lines)

    print(f"Generated calendar.ics and calendar-full.ics for {start_jy}–{end_jy}")


if __name__ == "__main__":
    main()
