from app.apps.idempotency.service import IdempotencyService


class DummyModel:
    idempotency_key = "test-key"


class StubIdempotencyRepository:
    def __init__(self) -> None:
        self.called = False
        self.model = None
        self.key = None

    def get_entity_by_idempotency_key(self, db, model, key):
        self.called = True
        self.model = model
        self.key = key
        return {"model": model, "key": key}


def test_find_duplicate_delegates_to_repository() -> None:
    repository = StubIdempotencyRepository()
    service = IdempotencyService(repository)

    result = service.find_duplicate(None, DummyModel, "test-key")

    assert repository.called is True
    assert repository.model is DummyModel
    assert repository.key == "test-key"
    assert result == {"model": DummyModel, "key": "test-key"}


def test_log_duplicate_emits_warning(monkeypatch) -> None:
    warnings = {}

    def fake_warning(message, *args, **kwargs):
        warnings["message"] = message
        warnings["args"] = args

    monkeypatch.setattr("app.apps.idempotency.service.logger.warning", fake_warning)
    service = IdempotencyService(StubIdempotencyRepository())

    service.log_duplicate("missing-key", "PAYMENT", 42)

    assert warnings["message"] == "DUPLICATE %s BLOCKED | key=%s owner=%s timestamp=%s"
    assert warnings["args"][0] == "PAYMENT"
    assert warnings["args"][1] == "missing-key"
    assert warnings["args"][2] == 42
