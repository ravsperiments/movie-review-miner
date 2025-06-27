import pytest
import importlib.util
import sys
from pathlib import Path
import types
import asyncio

ROOT = Path(__file__).resolve().parents[1]

fake_utils = types.ModuleType("utils")
fake_logger = types.ModuleType("logger")

def dummy_get_logger(name: str):
    import logging
    return logging.getLogger(name)

fake_logger.get_logger = dummy_get_logger
fake_utils.logger = fake_logger
sys.modules["utils"] = fake_utils
sys.modules["utils.logger"] = fake_logger

spec = importlib.util.spec_from_file_location(
    "retries", ROOT / "utils" / "retries.py"
)
retries = importlib.util.module_from_spec(spec)
spec.loader.exec_module(retries)
run_with_retries = retries.run_with_retries


def test_run_with_retries_success():
    calls = {"count": 0}

    async def sometimes_fail(attempt: int = 1):
        calls["count"] += 1
        if calls["count"] < 2:
            raise ValueError("boom")
        return "ok"

    result = asyncio.run(run_with_retries(sometimes_fail, max_retries=3, base_delay=0))
    assert result == "ok"
    assert calls["count"] == 2


def test_run_with_retries_failure():
    async def always_fail(attempt: int = 1):
        raise RuntimeError("nope")

    with pytest.raises(RuntimeError):
        asyncio.run(run_with_retries(always_fail, max_retries=2, base_delay=0))
