import pytest

pytest.importorskip("PySide6")

from ui.gui.main_window import TransferWorker


class FakeQueryService:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error

    def execute_transfer_query(self, date, from_station, to_station):
        if self.error:
            raise self.error
        return self.result


def run_worker(worker):
    finished = []
    errors = []
    worker.signals.finished.connect(finished.append)
    worker.signals.error.connect(errors.append)
    worker.run()
    return finished, errors


def test_transfer_worker_success():
    worker = TransferWorker(
        FakeQueryService({"transfers": ["方案"], "total_count": 1}),
        "2026-06-01",
        "北京",
        "上海",
    )

    finished, errors = run_worker(worker)

    assert finished == [{"transfers": ["方案"], "total_count": 1}]
    assert errors == []


def test_transfer_worker_station_not_found_result():
    worker = TransferWorker(
        FakeQueryService({"error": "STATION_NOT_FOUND", "transfers": [], "total_count": 0}),
        "2026-06-01",
        "不存在",
        "上海",
    )

    finished, errors = run_worker(worker)

    assert finished == [{"error": "STATION_NOT_FOUND", "transfers": [], "total_count": 0}]
    assert errors == []


def test_transfer_worker_emits_error_on_exception():
    worker = TransferWorker(
        FakeQueryService(error=RuntimeError("network down")),
        "2026-06-01",
        "北京",
        "上海",
    )

    finished, errors = run_worker(worker)

    assert finished == []
    assert errors == ["network down"]
