#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Sync Iran national/religious occasions from timestamp.ir into a normalized JSON dataset.

Policy:
- Keep Solar Hijri (شمسی) and Hijri lunar (قمری) occasions.
- Exclude Gregorian/world observances (میلادی).
- Exclude ad-hoc/special items (رویداد خاص) from the official-holidays feed.
- A holiday is included only when the source marks that specific شمسی/قمری occasion as تعطیل.

The generated JSON is committed to the repository, so calendar generation remains reproducible.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DATA_FILE = DATA_DIR / "iran-calendar.json"

MONTHS = {
    "فروردین": 1, "اردیبهشت": 2, "خرداد": 3, "تیر": 4,
    "مرداد": 5, "شهریور": 6, "مهر": 7, "آبان": 8,
    "آذر": 9, "دی": 10, "بهمن": 11, "اسفند": 12,
}
FA_TO_EN = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
DATE_RE = re.compile(
    r"^([۰-۹0-9]{1,2})\s+(" + "|".join(MONTHS) + r")(?:\s+.*)?$"
)
INLINE_EVENT_RE = re.compile(
    r"^(تعطیل|غیرتعطیل)\s+(شمسی|قمری|میلادی)\s+(.+)$"
)


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\u200c", "‌").strip())


def to_int(value: str) -> int:
    return int(value.translate(FA_TO_EN))


def extract_year(year: int, html: str, debug: bool = False) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    lines = [clean(x) for x in soup.stripped_strings if clean(x)]

    if debug:
        print("\n".join(f"{i:04d}: {line}" for i, line in enumerate(lines[:250])))

    records: list[dict] = []
    current_date: tuple[int, int] | None = None
    pending_status: str | None = None
    pending_calendar: str | None = None

    ignored_exact = {
        "جزئیات روز", "تعطیل", "غیرتعطیل", "شمسی", "قمری", "میلادی",
        "رویداد خاص",
    }

    for line in lines:
        m = DATE_RE.match(line)
        if m:
            day = to_int(m.group(1))
            month = MONTHS[m.group(2)]
            if 1 <= day <= 31:
                current_date = (month, day)
                pending_status = None
                pending_calendar = None
            continue

        if current_date is None:
            continue

        m = INLINE_EVENT_RE.match(line)
        if m:
            status, calendar_type, title = m.groups()
            title = clean(title)
            if title:
                records.append({
                    "year": year,
                    "month": current_date[0],
                    "day": current_date[1],
                    "status": status,
                    "calendar": calendar_type,
                    "title": title,
                })
            pending_status = None
            pending_calendar = None
            continue

        if line in {"تعطیل", "غیرتعطیل"}:
            pending_status = line
            pending_calendar = None
            continue

        if pending_status and line in {"شمسی", "قمری", "میلادی"}:
            pending_calendar = line
            continue

        if line == "رویداد خاص":
            pending_status = None
            pending_calendar = None
            continue

        if pending_status and pending_calendar:
            # Ignore navigation/meta fragments. The next meaningful token is normally the title.
            if line not in ignored_exact and not line.startswith(("میلادی ", "قمری ")):
                records.append({
                    "year": year,
                    "month": current_date[0],
                    "day": current_date[1],
                    "status": pending_status,
                    "calendar": pending_calendar,
                    "title": line,
                })
                pending_status = None
                pending_calendar = None

    # Fallback: some markup versions concatenate status/type/title into larger text nodes.
    if len(records) < 20:
        plain = soup.get_text("\n", strip=True)
        current_date = None
        for raw in plain.splitlines():
            line = clean(raw)
            m = DATE_RE.match(line)
            if m:
                current_date = (MONTHS[m.group(2)], to_int(m.group(1)))
                continue
            if current_date:
                m = INLINE_EVENT_RE.match(line)
                if m:
                    status, calendar_type, title = m.groups()
                    records.append({
                        "year": year,
                        "month": current_date[0],
                        "day": current_date[1],
                        "status": status,
                        "calendar": calendar_type,
                        "title": clean(title),
                    })

    # Normalize + deduplicate.
    unique = {}
    for item in records:
        title = item["title"].replace("«", "").replace("»", "").strip()
        if not title:
            continue
        item["title"] = title
        key = (item["year"], item["month"], item["day"], item["status"], item["calendar"], title)
        unique[key] = item

    return sorted(
        unique.values(),
        key=lambda x: (x["year"], x["month"], x["day"], x["calendar"], x["title"]),
    )


def fetch_year(year: int, timeout: int = 30, debug: bool = False) -> list[dict]:
    url = f"https://timestamp.ir/events-list/{year}"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; PersianAppleCalendar/1.0; +https://github.com/nemoresideo/persian-apple-calendar)"
    }
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"
    items = extract_year(year, response.text, debug=debug)
    if len(items) < 40:
        raise RuntimeError(f"Parsed too few events for {year}: {len(items)}")
    return items


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-year", type=int, default=1405)
    parser.add_argument("--end-year", type=int, default=1410)
    parser.add_argument("--debug-year", type=int)
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    previous = {}
    if DATA_FILE.exists():
        try:
            old = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            for item in old.get("events", []):
                previous.setdefault(int(item["year"]), []).append(item)
        except Exception:
            previous = {}

    all_items: list[dict] = []
    synced_years: list[int] = []
    retained_years: list[int] = []

    for year in range(args.start_year, args.end_year + 1):
        try:
            items = fetch_year(year, debug=(args.debug_year == year))
            all_items.extend(items)
            synced_years.append(year)
            print(f"{year}: synced {len(items)} solar/lunar/Gregorian-labeled records")
        except Exception as exc:
            if year in previous:
                all_items.extend(previous[year])
                retained_years.append(year)
                print(f"{year}: sync failed; retained existing data ({exc})", file=sys.stderr)
            else:
                print(f"{year}: unavailable; skipped ({exc})", file=sys.stderr)

    # Keep only Iranian Solar Hijri and religious lunar occasions.
    all_items = [x for x in all_items if x["calendar"] in {"شمسی", "قمری"}]

    holidays = [
        x for x in all_items
        if x["status"] == "تعطیل" and x["calendar"] in {"شمسی", "قمری"}
    ]

    payload = {
        "schema_version": 1,
        "source": {
            "name": "timestamp.ir",
            "url_template": "https://timestamp.ir/events-list/{year}",
            "reference_note": "1405 official calendar is published by the Calendar Center, Institute of Geophysics, University of Tehran.",
        },
        "synced_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "synced_years": synced_years,
        "retained_years": retained_years,
        "events": all_items,
        "holiday_count": len(holidays),
        "event_count": len(all_items),
    }

    DATA_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        f"Saved {len(all_items)} Iranian solar/lunar occasions; "
        f"{len(holidays)} source-marked official holidays."
    )


if __name__ == "__main__":
    main()
