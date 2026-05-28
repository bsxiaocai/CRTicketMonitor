"""utils 模块测试"""

from utils.time_utils import time_to_minutes, duration_to_minutes, is_cross_day
from utils.constants import SEAT_SENTINEL


class TestTimeToMinutes:
    def test_normal_time(self):
        assert time_to_minutes("08:30") == 510

    def test_midnight(self):
        assert time_to_minutes("00:00") == 0

    def test_end_of_day(self):
        assert time_to_minutes("23:59") == 1439

    def test_invalid_format(self):
        assert time_to_minutes("bad") == 99999

    def test_empty_string(self):
        assert time_to_minutes("") == 99999


class TestDurationToMinutes:
    def test_hh_mm_format(self):
        assert duration_to_minutes("04:30") == 270

    def test_chinese_hour_minute(self):
        assert duration_to_minutes("4小时30分") == 270

    def test_chinese_minute_only(self):
        assert duration_to_minutes("30分") == 30

    def test_chinese_hour_only(self):
        assert duration_to_minutes("2小时") == 120

    def test_invalid_format(self):
        assert duration_to_minutes("bad") == 99999

    def test_empty_string(self):
        assert duration_to_minutes("") == 99999


class TestIsCrossDay:
    def test_cross_day(self):
        assert is_cross_day("22:00", "06:00", "08:00") is True

    def test_same_day(self):
        assert is_cross_day("08:00", "12:00", "04:00") is False

    def test_invalid_input(self):
        assert is_cross_day("bad", "bad", "bad") is False


class TestConstants:
    def test_seat_sentinel_contains_expected(self):
        assert '无' in SEAT_SENTINEL
        assert '--' in SEAT_SENTINEL
        assert '' in SEAT_SENTINEL
        assert '0' in SEAT_SENTINEL

    def test_seat_sentinel_is_frozen(self):
        assert isinstance(SEAT_SENTINEL, frozenset)
