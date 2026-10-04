#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Persian (Jalali) calendar feeds for Apple Calendar.

Feeds:
  calendar.ics        One clean Persian-date event per day.
  calendar-pro.ics    Professional Persian-date feed.
  calendar-full.ics   Full/legacy date + weekday feed.
  iran-holidays.ics   Official Iran holidays as a separate feed.
  iran-events.ics     Iranian national/religious occasions as a separate feed.

No third-party package is required.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
IRAN_DATA_PATH = ROOT / "data" / "iran-calendar.json"

PERSIAN_MONTHS = [
    "", "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]

GREGORIAN_MONTHS_FA = [
    "", "ژانویه", "فوریه", "مارس", "آوریل", "مه", "ژوئن",
    "ژوئیه", "اوت", "سپتامبر", "اکتبر", "نوامبر", "دسامبر",
]

# Python weekday(): Monday=0 ... Sunday=6
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
    """Convert a Gregorian date to Jalali (Solar Hijri)."""
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
    """Return Gregorian date of 1 Farvardin for a Jalali year."""
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
    """Fold UTF-8 iCalendar lines without splitting multi-byte characters."""
    if len(line.encode("utf-8")) <= max_octets:
        return [line]

    parts: list[str] = []
    current = ""
    current_len = 0

    for char in line:
        char_len = len(char.encode("utf-8"))
        limit = max_octets if not parts else max_octets - 1

        if current and current_len + char_len > limit:
            parts.append(current)
            current = char
            current_len = char_len
        else:
            current += char
            current_len += char_len

    if current:
        parts.append(current)

    return [parts[0]] + [" " + part for part in parts[1:]]


def make_event(
    *,
    gdate: date,
    jy: int,
    jm: int,
    jd: int,
    owner_tag: str,
    dtstamp: str,
    summary: str,
    uid_prefix: str,
    description: str,
) -> list[str]:
    next_day = gdate + timedelta(days=1)

    raw = [
        "BEGIN:VEVENT",
        f"UID:{uid_prefix}-{jy:04d}-{jm:02d}-{jd:02d}@{owner_tag}",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART;VALUE=DATE:{gdate:%Y%m%d}",
        f"DTEND;VALUE=DATE:{next_day:%Y%m%d}",
        f"SUMMARY:{escape_ics(summary)}",
        f"DESCRIPTION:{escape_ics(description)}",
        "CATEGORIES:Persian Calendar",
        "CLASS:PUBLIC",
        "TRANSP:TRANSPARENT",
        "STATUS:CONFIRMED",
        "SEQUENCE:0",
        "END:VEVENT",
    ]

    folded: list[str] = []
    for line in raw:
        folded.extend(fold_ics_line(line))
    return folded


def calendar_header(
    *,
    name: str,
    description: str,
    owner_tag: str,
    calendar_color: str,
    source_url: str,
) -> list[str]:
    return [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//{owner_tag}//Persian Apple Calendar//FA",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_ics(name)}",
        f"X-WR-CALDESC:{escape_ics(description)}",
        "X-WR-TIMEZONE:Asia/Tehran",
        f"X-APPLE-CALENDAR-COLOR:{calendar_color}",
        f"COLOR:{calendar_color}",
        "REFRESH-INTERVAL;VALUE=DURATION:PT12H",
        "X-PUBLISHED-TTL:PT12H",
        f"SOURCE;VALUE=URI:{source_url}",
    ]


def build_feed(
    *,
    mode: str,
    name: str,
    description: str,
    owner_tag: str,
    calendar_color: str,
    source_url: str,
    start_jy: int,
    end_jy: int,
) -> list[str]:
    start = jalali_year_start_gregorian(start_jy)
    end = jalali_year_start_gregorian(end_jy + 1)  # exclusive
    dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lines = calendar_header(
        name=name,
        description=description,
        owner_tag=owner_tag,
        calendar_color=calendar_color,
        source_url=source_url,
    )

    current = start
    while current < end:
        jy, jm, jd = gregorian_to_jalali(current.year, current.month, current.day)
        weekday = PERSIAN_WEEKDAYS[current.weekday()]
        month = PERSIAN_MONTHS[jm]
        short_date = f"{fa_num(jd)} {month}"
        full_date = f"{weekday}، {fa_num(jd)} {month} {fa_num(jy)}"
        gregorian_fa = (
            f"{fa_num(current.day)} {GREGORIAN_MONTHS_FA[current.month]} "
            f"{fa_num(current.year)}"
        )

        if mode == "clean":
            lines.extend(
                make_event(
                    gdate=current,
                    jy=jy,
                    jm=jm,
                    jd=jd,
                    owner_tag=owner_tag,
                    dtstamp=dtstamp,
                    summary=short_date,
                    uid_prefix="date",
                    description=full_date,
                )
            )

        elif mode == "pro":
            lines.extend(
                make_event(
                    gdate=current,
                    jy=jy,
                    jm=jm,
                    jd=jd,
                    owner_tag=owner_tag,
                    dtstamp=dtstamp,
                    summary=short_date,
                    uid_prefix="pro",
                    description=(
                        f"{full_date}\n"
                        f"میلادی: {gregorian_fa}"
                    ),
                )
            )

        elif mode == "full":
            lines.extend(
                make_event(
                    gdate=current,
                    jy=jy,
                    jm=jm,
                    jd=jd,
                    owner_tag=owner_tag,
                    dtstamp=dtstamp,
                    summary=short_date,
                    uid_prefix="date",
                    description=full_date,
                )
            )
            lines.extend(
                make_event(
                    gdate=current,
                    jy=jy,
                    jm=jm,
                    jd=jd,
                    owner_tag=owner_tag,
                    dtstamp=dtstamp,
                    summary=weekday,
                    uid_prefix="weekday",
                    description=full_date,
                )
            )
        else:
            raise ValueError(f"Unknown feed mode: {mode}")

        current += timedelta(days=1)

    lines.append("END:VCALENDAR")
    return lines


def jalali_to_gregorian_date(jy: int, jm: int, jd: int) -> date:
    start = jalali_year_start_gregorian(jy)
    if jm <= 6:
        offset = (jm - 1) * 31 + (jd - 1)
    else:
        offset = 186 + (jm - 7) * 30 + (jd - 1)
    return start + timedelta(days=offset)


def build_iran_feed(
    *,
    items: list[dict],
    holidays_only: bool,
    name: str,
    description: str,
    owner_tag: str,
    calendar_color: str,
    source_url: str,
) -> list[str]:
    lines = calendar_header(
        name=name,
        description=description,
        owner_tag=owner_tag,
        calendar_color=calendar_color,
        source_url=source_url,
    )
    dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    selected = []
    for item in items:
        if item.get("calendar") not in {"شمسی", "قمری"}:
            continue
        if holidays_only and item.get("status") != "تعطیل":
            continue
        selected.append(item)

    for index, item in enumerate(selected):
        jy = int(item["year"])
        jm = int(item["month"])
        jd = int(item["day"])
        gdate = jalali_to_gregorian_date(jy, jm, jd)
        weekday = PERSIAN_WEEKDAYS[gdate.weekday()]
        month = PERSIAN_MONTHS[jm]
        holiday_label = "تعطیل رسمی" if item.get("status") == "تعطیل" else "مناسبت"
        description_text = (
            f"{weekday}، {fa_num(jd)} {month} {fa_num(jy)}\n"
            f"{holiday_label} • {item.get('calendar', '')}"
        )
        uid_prefix = "iran-holiday" if holidays_only else "iran-event"
        # Include a deterministic suffix so multiple occasions on one day stay unique.
        digest_source = f"{item.get('calendar', '')}|{item.get('title', '')}".encode("utf-8")
        safe_suffix = hashlib.sha1(digest_source).hexdigest()[:10]

        lines.extend(
            make_event(
                gdate=gdate,
                jy=jy,
                jm=jm,
                jd=jd,
                owner_tag=owner_tag,
                dtstamp=dtstamp,
                summary=str(item["title"]),
                uid_prefix=f"{uid_prefix}-{safe_suffix}",
                description=description_text,
            )
        )

    lines.append("END:VCALENDAR")
    return lines


def write_ics(path: Path, lines: list[str]) -> None:
    """Write RFC 5545 compatible CRLF line endings."""
    path.write_bytes(("\r\n".join(lines) + "\r\n").encode("utf-8"))


def validate_known_dates() -> None:
    checks = {
        (2026, 3, 21): (1405, 1, 1),
        (2026, 10, 4): (1405, 7, 12),
        (2027, 3, 20): (1405, 12, 29),
    }
    for gdate, expected in checks.items():
        actual = gregorian_to_jalali(*gdate)
        if actual != expected:
            raise AssertionError(
                f"Date conversion failed: {gdate} -> {actual}, expected {expected}"
            )


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    start_jy = int(config["start_jalali_year"])
    end_jy = int(config["end_jalali_year"])
    owner_tag = str(config["owner_tag"]).strip()
    calendar_name = str(config["calendar_name"]).strip()
    calendar_color = str(config["calendar_color"]).strip()
    raw_base_url = str(config["raw_base_url"]).rstrip("/")
    holidays_color = str(config.get("holidays_color", "#FF3B30")).strip()
    events_color = str(config.get("events_color", "#007AFF")).strip()

    validate_known_dates()

    feeds = [
        (
            "calendar.ics",
            "clean",
            calendar_name,
            f"تاریخ شمسی {fa_num(start_jy)} تا {fa_num(end_jy)} برای Apple Calendar",
        ),
        (
            "calendar-pro.ics",
            "pro",
            f"{calendar_name} — حرفه‌ای",
            f"تقویم شمسی حرفه‌ای {fa_num(start_jy)} تا {fa_num(end_jy)}",
        ),
        (
            "calendar-full.ics",
            "full",
            f"{calendar_name} — کامل",
            f"تاریخ شمسی و روز هفته، {fa_num(start_jy)} تا {fa_num(end_jy)}",
        ),
    ]

    for filename, mode, name, description in feeds:
        lines = build_feed(
            mode=mode,
            name=name,
            description=description,
            owner_tag=owner_tag,
            calendar_color=calendar_color,
            source_url=f"{raw_base_url}/{filename}",
            start_jy=start_jy,
            end_jy=end_jy,
        )
        write_ics(ROOT / filename, lines)

    generated = [item[0] for item in feeds]

    if IRAN_DATA_PATH.exists():
        iran_data = json.loads(IRAN_DATA_PATH.read_text(encoding="utf-8"))
        iran_items = iran_data.get("events", [])

        holiday_lines = build_iran_feed(
            items=iran_items,
            holidays_only=True,
            name="تعطیلات رسمی ایران",
            description="تعطیلات رسمی ایران — تقویم مستقل برای Apple Calendar",
            owner_tag=owner_tag,
            calendar_color=holidays_color,
            source_url=f"{raw_base_url}/iran-holidays.ics",
        )
        write_ics(ROOT / "iran-holidays.ics", holiday_lines)
        generated.append("iran-holidays.ics")

        event_lines = build_iran_feed(
            items=iran_items,
            holidays_only=False,
            name="مناسبت‌های ایران",
            description="مناسبت‌های ملی، فرهنگی و مذهبی ایران",
            owner_tag=owner_tag,
            calendar_color=events_color,
            source_url=f"{raw_base_url}/iran-events.ics",
        )
        write_ics(ROOT / "iran-events.ics", event_lines)
        generated.append("iran-events.ics")

    print(
        f"Generated feeds for Jalali years {start_jy}–{end_jy}: "
        + ", ".join(generated)
    )


if __name__ == "__main__":
    main()
