"""Regulatory inputs travel with the bank through build, save and load."""
# ruff: noqa: D103

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from brms.core.models.regulatory import RegulatoryConfig
from brms.core.services import build_core_services
from brms.core.services.simulation_builder import BuildConfig, SimulationBuilder
from brms.core.services.snapshot_writer import save_snapshot
from tests.support.engine import flat_yields, funding

if TYPE_CHECKING:
    from pathlib import Path


def test_default_regulatory_config() -> None:
    config = RegulatoryConfig()
    assert config.aoci_filter is False  # noqa: S101
    assert config.operational_rwa == 0  # noqa: S101
    assert config.additional_tier1 == 0  # noqa: S101
    assert config.tier2 == 0  # noqa: S101


def test_regulatory_config_round_trips(tmp_path: Path) -> None:
    regulatory = RegulatoryConfig(
        aoci_filter=True, operational_rwa=Decimal(1_000_000), additional_tier1=Decimal(50_000), tier2=Decimal(70_000),
    )
    instruments, positions = funding()
    config = BuildConfig(
        name="reg", start_date=datetime.date(2021, 2, 1), instruments=instruments, positions=positions,
        market_frames={"yields": flat_yields(datetime.date(2021, 1, 4), datetime.date(2021, 3, 31))},
        regulatory=regulatory,
    )
    snapshot = SimulationBuilder().build(config)
    assert snapshot.regulatory == regulatory  # noqa: S101
    path = tmp_path / "reg.zip"
    save_snapshot(snapshot, [{"id": "equity", "type": "common_equity", "name": "Test equity"}], path)
    assert build_core_services(simulation_zip=path).bank.regulatory == regulatory  # noqa: S101
