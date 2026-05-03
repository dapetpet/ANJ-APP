import pytest


from timing import PeriodicSchedule, format_countdown


def test_format_countdown_none():
    assert format_countdown(None) == "--"


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0, "00:00"),
        (1, "00:01"),
        (9.9, "00:09"),
        (10, "00:10"),
        (59.1, "00:59"),
        (60, "01:00"),
        (61, "01:01"),
        (125, "02:05"),
    ],
)
def test_format_countdown_mmss(seconds, expected):
    assert format_countdown(seconds) == expected


def test_periodic_schedule_start_and_remaining():
    s = PeriodicSchedule(interval_s=10.0)
    assert s.next_run is None
    assert s.remaining(100.0) is None

    s.start(now=100.0)
    assert s.next_run == pytest.approx(110.0)
    assert s.remaining(100.0) == pytest.approx(10.0)
    assert s.remaining(109.4) == pytest.approx(0.6)
    assert s.remaining(110.0) == pytest.approx(0.0)
    assert s.remaining(120.0) == pytest.approx(0.0)


def test_periodic_schedule_advance():
    s = PeriodicSchedule(interval_s=30.0)
    s.start(now=50.0)
    assert s.next_run == pytest.approx(80.0)

    s.advance(now=80.0)
    assert s.next_run == pytest.approx(110.0)


def test_periodic_schedule_reset():
    s = PeriodicSchedule(interval_s=10.0)
    s.start(now=0.0)
    s.reset()
    assert s.next_run is None
