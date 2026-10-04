import unittest
from datetime import date
import generate_calendar as cal


class PersianCalendarTests(unittest.TestCase):
    def test_known_dates(self):
        self.assertEqual(cal.gregorian_to_jalali(2026, 3, 21), (1405, 1, 1))
        self.assertEqual(cal.gregorian_to_jalali(2026, 10, 4), (1405, 7, 12))
        self.assertEqual(cal.gregorian_to_jalali(2027, 3, 20), (1405, 12, 29))

    def test_weekday_mapping(self):
        self.assertEqual(cal.PERSIAN_WEEKDAYS[date(2026, 10, 4).weekday()], "یکشنبه")

    def test_persian_digits(self):
        self.assertEqual(cal.fa_num(1405), "۱۴۰۵")
        self.assertEqual(cal.fa_num(12), "۱۲")

    def test_year_start(self):
        self.assertEqual(cal.jalali_year_start_gregorian(1405), date(2026, 3, 21))

    def test_ics_escaping(self):
        self.assertEqual(cal.escape_ics("الف،ب"), "الف\\،ب")


if __name__ == "__main__":
    unittest.main()
