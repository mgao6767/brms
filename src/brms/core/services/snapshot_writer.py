"""save_snapshot: write a SimulationSnapshot as the zip archive ZipLoader reads."""

from __future__ import annotations

import datetime
import json
import zipfile
from typing import TYPE_CHECKING

from brms.core.services.loaders import SNAPSHOT_FORMAT, ZipLoaderConfig

if TYPE_CHECKING:
    from pathlib import Path

    from brms.core.models.position import Position
    from brms.core.services.simulation_builder import SimulationSnapshot


def _position_record(position: Position) -> dict[str, object]:
    return {
        "id": position.id,
        "instrument_id": position.instrument_id,
        "book_type": position.book_type.name,
        "measurement_basis": position.measurement_basis.name,
        "side": position.side.name,
        "acquisition_date": position.acquisition_date.isoformat(),
        "acquisition_cost": str(position.acquisition_cost),
        "status": position.status.name,
    }


def save_snapshot(
    snapshot: SimulationSnapshot,
    instrument_specs: list[dict[str, object]],
    path: Path,
    *,
    end_date: datetime.date | None = None,
) -> None:
    """Write *snapshot* to *path*.

    *instrument_specs* are the JSON-ready instrument definitions the snapshot's instruments
    were built from (``type`` plus constructor arguments), written as ``instruments.json``.
    """
    files = ZipLoaderConfig()
    config: dict[str, object] = {
        "format": SNAPSHOT_FORMAT,
        "name": snapshot.name,
        "start_date": snapshot.start_date.isoformat(),
        "regulatory": snapshot.regulatory.to_json(),
    }
    if end_date is not None:
        config["end_date"] = end_date.isoformat()
    balances = {
        "snapshot_date": (snapshot.start_date - datetime.timedelta(days=1)).isoformat(),
        "balances": snapshot.balances,
        "valuations": snapshot.valuations,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(files.config_file, json.dumps(config, indent=2))
        zf.writestr(files.instruments_file, json.dumps(instrument_specs, indent=2))
        zf.writestr(files.positions_file, json.dumps([_position_record(p) for p in snapshot.positions], indent=2))
        zf.writestr("balances.json", json.dumps(balances, indent=2))
        for frame_name, filename in files.market_data_mapping.items():
            frame = snapshot.market_frames.get(frame_name)
            if frame is not None:
                zf.writestr(filename, frame.to_csv(index_label="date", date_format="%Y-%m-%d"))
