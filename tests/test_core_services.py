import csv
import json
import time

from config.config_manager import ConfigManager
from core.ticket_parser import TicketParser
from core.train_classifier import TrainClassifier
from logger.query_history import QueryHistory
from notification.base import TicketInfo
from services.cache_service import CacheService
from services.export_service import ExportService


def test_train_classifier_basic_types_and_flags():
    assert TrainClassifier.classify_train("G1") == "GC"
    assert TrainClassifier.classify_train("C123") == "GC"
    assert TrainClassifier.classify_train("D901") == "D"
    assert TrainClassifier.classify_train("Z1") == "Z"
    assert TrainClassifier.classify_train("T1") == "T"
    assert TrainClassifier.classify_train("K1") == "K"
    assert TrainClassifier.classify_train("S101") == "其他"
    assert TrainClassifier.classify_train("1234") == "其他"

    assert TrainClassifier.is_fuxing("G1") is True
    assert TrainClassifier.is_fuxing("K1") is False
    assert TrainClassifier.is_smart("G4001") is True
    assert TrainClassifier.is_smart("G1234") is False


def test_config_manager_deep_merges_defaults(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({
            "notification": {
                "enabled": False,
                "channels": {
                    "wechat_work": {"enabled": True, "webhook_url": "https://example.test"}
                }
            }
        }),
        encoding="utf-8",
    )

    config = ConfigManager(str(config_path)).get_config()

    assert config["notification"]["enabled"] is False
    assert config["notification"]["cooldown_seconds"] == 300
    assert config["notification"]["channels"]["windows_desktop"]["enabled"] is True
    assert config["notification"]["channels"]["wechat_work"]["webhook_url"] == "https://example.test"
    assert config["notification"]["channels"]["dingtalk"]["secret"] == ""
    assert config["logging"]["debug_api"] is False


def test_cache_service_hit_expire_invalidate():
    cache = CacheService(ttl_seconds=1)
    cache.set("北京", "上海", "2026-06-01", ["raw"])

    assert cache.get(" 北京 ", "上海", "2026-06-01") == ["raw"]
    cache.invalidate("北京", "上海", "2026-06-01")
    assert cache.get("北京", "上海", "2026-06-01") is None

    cache.set("北京", "上海", "2026-06-01", ["raw"])
    cache._cache[("北京", "上海", "2026-06-01")] = (["raw"], time.time() - 1)
    assert cache.get("北京", "上海", "2026-06-01") is None


def test_export_service_json_and_csv(tmp_path):
    ticket = TicketInfo(
        train_no="G1",
        from_station="北京南",
        to_station="上海虹桥",
        date="2026-06-01",
        departure_time="08:00",
        arrival_time="12:30",
        duration="04:30",
        available_seats={"二等座": "5"},
    )
    json_path = tmp_path / "tickets.json"
    csv_path = tmp_path / "tickets.csv"

    ExportService.export_to_json([ticket], str(json_path))
    ExportService.export_to_csv([{"车次": "G1", "二等座": "5"}], str(csv_path))

    exported_json = json.loads(json_path.read_text(encoding="utf-8"))
    assert exported_json["total_count"] == 1
    assert exported_json["tickets"][0]["train_no"] == "G1"

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows == [{"车次": "G1", "二等座": "5"}]


def test_ticket_parser_parses_available_ticket():
    fields = [""] * TicketParser.MIN_FIELDS
    fields[TicketParser.FIELD["internal_train_no"]] = "240000G1030A"
    fields[TicketParser.FIELD["train_no"]] = "G103"
    fields[TicketParser.FIELD["from_station_code"]] = "VNP"
    fields[TicketParser.FIELD["to_station_code"]] = "AOH"
    fields[TicketParser.FIELD["departure_time"]] = "08:00"
    fields[TicketParser.FIELD["arrival_time"]] = "12:30"
    fields[TicketParser.FIELD["duration"]] = "04:30"
    fields[TicketParser.FIELD["from_station_no"]] = "01"
    fields[TicketParser.FIELD["to_station_no"]] = "02"
    fields[TicketParser.FIELD["second_class"]] = "5"
    fields[TicketParser.FIELD["seat_types_code"]] = "OM"

    tickets = TicketParser.parse_and_print(
        raw_data=["|".join(fields)],
        ticket_info_list=[],
        date="2026-06-01",
        code_to_name={"VNP": "北京南", "AOH": "上海虹桥"},
        classify_func=TrainClassifier.classify_train,
        return_all=True,
    )

    assert len(tickets) == 1
    assert tickets[0].train_no == "G103"
    assert tickets[0].from_station == "北京南"
    assert tickets[0].available_seats["二等座"] == "5"


def test_query_history_record_delete_and_statistics(tmp_path):
    history = QueryHistory(str(tmp_path))
    history.record("北京", "上海", "2026-06-01", 2, ["G1"])
    history.record("北京", "广州", "2026-06-02", 3, [])

    assert len(history.get_recent()) == 2
    stats = history.get_statistics()
    assert stats["total_queries"] == 2
    assert stats["total_with_tickets"] == 1

    assert history.delete_by_index([0]) is True
    remaining = history.get_recent()
    assert len(remaining) == 1
    assert remaining[0]["to"] == "上海"
