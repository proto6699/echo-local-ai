from neco.system_vitals import _parse_meminfo


def test_parse_meminfo() -> None:
    parsed = _parse_meminfo("MemTotal: 1048576 kB\nMemAvailable: 524288 kB\n")
    assert parsed == {"used_gib": 0.5, "total_gib": 1.0, "used_percent": 50.0}


def test_parse_meminfo_requires_total_and_available() -> None:
    assert _parse_meminfo("MemTotal: 1024 kB\n") is None
