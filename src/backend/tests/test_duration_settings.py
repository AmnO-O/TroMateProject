"""SCRUM-138: configurable time durations (Use-Case Specification v3.0, Test Plan v1.2 §3)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.core.config import DurationSettings, Settings
from app.main import log_duration_settings
from app.services.durations import format_duration_vi, validate_review_window
from app.services.errors import ValidationError
from tests.helpers import TEST_BOT_TOKEN, TEST_WEBHOOK_SECRET

PRODUCTION = {
    "review_window_min_minutes": 1440,
    "review_window_max_minutes": 43200,
    "rep_vote_period_minutes": None,
    "change_request_vote_period_minutes": 1440,
    "vote_reminder_before_end_minutes": 120,
    "change_request_open_period_minutes": 4320,
    "proposal_cooldown_minutes": 10080,
    "dispute_reminder_interval_minutes": 4320,
    "deadline_reminder_before_minutes": 1440,
    "deadline_reminder_min_window_minutes": 1440,
}

# Test Plan v1.2, section 3 "Test configuration".
TEST_ENV = {
    "REVIEW_WINDOW_MIN_MINUTES": "5",
    "REVIEW_WINDOW_MAX_MINUTES": "43200",
    "REP_VOTE_PERIOD_MINUTES": "10",
    "CHANGE_REQUEST_VOTE_PERIOD_MINUTES": "10",
    "VOTE_REMINDER_BEFORE_END_MINUTES": "2",
    "CHANGE_REQUEST_OPEN_PERIOD_MINUTES": "10",
    "PROPOSAL_COOLDOWN_MINUTES": "15",
    "DISPUTE_REMINDER_INTERVAL_MINUTES": "10",
    "DEADLINE_REMINDER_BEFORE_MINUTES": "5",
    "DEADLINE_REMINDER_MIN_WINDOW_MINUTES": "5",
}


@pytest.fixture(autouse=True)
def _clear_duration_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate every test from duration variables set in the shell."""

    for name in TEST_ENV:
        monkeypatch.delenv(name, raising=False)


def _durations(**kwargs) -> DurationSettings:
    return DurationSettings(_env_file=None, **kwargs)


def test_defaults_are_production_values() -> None:
    durations = _durations()

    assert durations.duration_values() == PRODUCTION
    assert durations.non_production_durations() == {}
    assert durations.rep_vote_period(12) == timedelta(hours=12)
    assert durations.rep_vote_period(72) == timedelta(hours=72)
    assert durations.change_request_vote_period == timedelta(hours=24)
    assert durations.vote_reminder_before_end == timedelta(hours=2)
    assert durations.change_request_open_period == timedelta(days=3)
    assert durations.proposal_cooldown == timedelta(days=7)
    assert durations.dispute_reminder_interval == timedelta(days=3)
    assert durations.deadline_reminder_before == timedelta(hours=24)


def test_values_from_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in TEST_ENV.items():
        monkeypatch.setenv(name, value)

    durations = _durations(app_env="test")

    assert durations.review_window_min_minutes == 5
    assert durations.review_window_max_minutes == 43200
    # BR10: every choice uses the test period; the 12/24/48/72-hour labels are unchanged.
    for hours in (12, 24, 48, 72):
        assert durations.rep_vote_period(hours) == timedelta(minutes=10)
    assert durations.change_request_vote_period == timedelta(minutes=10)
    assert durations.vote_reminder_before_end == timedelta(minutes=2)
    assert durations.change_request_open_period == timedelta(minutes=10)
    assert durations.proposal_cooldown == timedelta(minutes=15)
    assert durations.dispute_reminder_interval == timedelta(minutes=10)
    assert durations.deadline_reminder_before == timedelta(minutes=5)
    assert durations.deadline_reminder_min_window_minutes == 5
    assert set(durations.non_production_durations()) == {
        name.lower() for name in TEST_ENV if name != "REVIEW_WINDOW_MAX_MINUTES"
    }


def test_full_settings_read_durations_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISPUTE_REMINDER_INTERVAL_MINUTES", "10")
    settings = Settings(
        _env_file=None,
        app_env="test",
        auto_set_webhook=False,
        telegram_bot_token=TEST_BOT_TOKEN,
        telegram_webhook_secret=TEST_WEBHOOK_SECRET,
    )
    assert settings.dispute_reminder_interval == timedelta(minutes=10)


def test_rep_vote_period_rejects_unknown_choice() -> None:
    with pytest.raises(ValueError, match="12, 24, 48, 72"):
        _durations().rep_vote_period(6)


@pytest.mark.parametrize("name", [n for n in PRODUCTION if n != "rep_vote_period_minutes"])
def test_durations_must_be_positive(name: str) -> None:
    with pytest.raises(PydanticValidationError):
        _durations(**{name: 0})


def test_min_window_must_not_exceed_max() -> None:
    with pytest.raises(PydanticValidationError, match="must not exceed"):
        _durations(review_window_min_minutes=100, review_window_max_minutes=50)


def test_production_accepts_production_values() -> None:
    assert _durations(app_env="production", **PRODUCTION).app_env == "production"


@pytest.mark.parametrize(
    ("name", "value"),
    [(name.lower(), int(value)) for name, value in TEST_ENV.items()]
    + [("review_window_max_minutes", 50000)],
)
def test_production_refuses_non_production_duration(name: str, value: int) -> None:
    if PRODUCTION[name] == value:
        pytest.skip("test value equals the production value")
    with pytest.raises(PydanticValidationError, match=f"APP_ENV=production.*{name.upper()}"):
        _durations(app_env="production", **{name: value})


def test_production_app_settings_refuse_to_load(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REVIEW_WINDOW_MIN_MINUTES", "5")
    with pytest.raises(PydanticValidationError, match="REVIEW_WINDOW_MIN_MINUTES=5"):
        Settings(
            _env_file=None,
            app_env="production",
            auto_set_webhook=False,
            telegram_bot_token=TEST_BOT_TOKEN,
            telegram_webhook_secret=TEST_WEBHOOK_SECRET,
        )


def test_non_production_envs_accept_overrides() -> None:
    for env in ("local", "test"):
        assert _durations(app_env=env, review_window_min_minutes=5).review_window_min_minutes == 5


def test_validate_review_window_production_limits() -> None:
    durations = _durations()
    assert validate_review_window(1440, durations) == 1440
    assert validate_review_window(43200, durations) == 43200
    for invalid in (5, 1439, 43201):
        with pytest.raises(ValidationError) as exc:
            validate_review_window(invalid, durations)
        assert "từ 1 ngày đến 30 ngày" in exc.value.message


def test_validate_review_window_test_limits() -> None:
    durations = _durations(review_window_min_minutes=5)
    assert validate_review_window(5, durations) == 5
    with pytest.raises(ValidationError) as exc:
        validate_review_window(4, durations)
    assert "từ 5 phút đến 30 ngày" in exc.value.message


def test_deadline_reminder_only_above_min_window() -> None:
    production = _durations()
    assert not production.needs_deadline_reminder(None)
    assert not production.needs_deadline_reminder(1440)
    assert production.needs_deadline_reminder(1441)
    test_env = _durations(deadline_reminder_min_window_minutes=5)
    assert not test_env.needs_deadline_reminder(5)
    assert test_env.needs_deadline_reminder(6)


def test_format_duration_vi() -> None:
    assert format_duration_vi(5) == "5 phút"
    assert format_duration_vi(1440) == "1 ngày"
    assert format_duration_vi(43200) == "30 ngày"
    assert format_duration_vi(1500) == "1 ngày 1 giờ"


def test_startup_log_lists_active_durations(caplog: pytest.LogCaptureFixture) -> None:
    settings = Settings(
        _env_file=None,
        app_env="test",
        auto_set_webhook=False,
        telegram_bot_token=TEST_BOT_TOKEN,
        telegram_webhook_secret=TEST_WEBHOOK_SECRET,
        review_window_min_minutes=5,
    )
    with caplog.at_level(logging.INFO, logger="app.main"):
        log_duration_settings(settings)
    assert "review_window_min_minutes=5" in caplog.text
    assert "dispute_reminder_interval_minutes=4320" in caplog.text
    assert "Non-production durations in effect: REVIEW_WINDOW_MIN_MINUTES" in caplog.text


async def test_five_minute_window_is_latched_and_survives_room_change() -> None:
    """BR03: a 5-minute test window works and is stored on the expense at share time."""

    from tests.test_uc01_new_command import _build_fake_service

    service, expense_repo, room = _build_fake_service(api_key="", review_timeout_minutes=5)
    draft = await service.prepare_expense_draft(
        telegram_chat_id=-100123456,
        chat_title="R203",
        telegram_user_id=9001,
        sender_display_name="Trần Minh",
        sender_username="tranminh",
        text="Mua trái cây 120k chia đều",
    )
    assert draft is not None
    shared_at = datetime(2026, 11, 27, 9, 0, tzinfo=UTC)
    created = await service.share_expense_draft(draft, now=shared_at)
    room.review_timeout_minutes = 1440

    assert created.review_window_minutes == 5
    assert created.review_deadline == shared_at + timedelta(minutes=5)
    assert expense_repo.saved[0].review_deadline == shared_at + timedelta(minutes=5)
