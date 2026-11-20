"""Regulatory inputs the lab does not derive from the books."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class RegulatoryConfig:
    """Bank-level regulatory settings and amounts supplied by the user.

    Attributes:
        aoci_filter: True removes accumulated OCI from CET1 (the US opt-out for banks not on
            advanced approaches); False is the Basel III treatment, where it counts.
        operational_rwa: Operational-risk RWA (an input; operational losses are not modelled).
        additional_tier1: Additional Tier 1 instruments outstanding.
        tier2: Tier 2 capital.

    """

    aoci_filter: bool = False
    operational_rwa: Decimal = Decimal(0)
    additional_tier1: Decimal = Decimal(0)
    tier2: Decimal = Decimal(0)

    def to_json(self) -> dict[str, Any]:
        """Return the JSON form written to ``config.json``."""
        return {
            "aoci_filter": self.aoci_filter,
            "operational_rwa": str(self.operational_rwa),
            "additional_tier1": str(self.additional_tier1),
            "tier2": str(self.tier2),
        }

    @classmethod
    def from_json(cls, data: dict[str, Any] | None) -> RegulatoryConfig:
        """Build from the JSON form; missing keys take their defaults."""
        data = data or {}
        return cls(
            aoci_filter=bool(data.get("aoci_filter", False)),
            operational_rwa=Decimal(str(data.get("operational_rwa", 0))),
            additional_tier1=Decimal(str(data.get("additional_tier1", 0))),
            tier2=Decimal(str(data.get("tier2", 0))),
        )
