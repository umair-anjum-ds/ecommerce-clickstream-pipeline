"""Shared test setup: one Spark session and one small fake dataset for all tests."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.generate_sample_data import generate  # noqa: E402
from src.spark_session import get_spark  # noqa: E402


@pytest.fixture(scope="session")
def spark():
    session = get_spark(app_name="tests", shuffle_partitions=4, driver_memory="2g")
    yield session
    session.stop()


@pytest.fixture(scope="session")
def sample_csv(tmp_path_factory):
    path = tmp_path_factory.mktemp("data") / "events.csv"
    generate(str(path), sessions=1200, seed=7)
    return str(path)
