"""Core structural primitives for the FSPM design spec."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence


class BudState(str, Enum):
    ACTIVE = "active"
    DORMANT = "dormant"
    FLOWER = "flower"
    DEAD = "dead"


@dataclass(frozen=True)
class Stem:
    """Stem/Internode with pipe-model related properties."""

    length_cm: float
    diameter_cm: float
    mass_g: float


@dataclass(frozen=True)
class Leaf:
    """Leaf that provides photosynthesis."""

    area_cm2: float
    nitrogen_g_m2: float
    incident_light_umol: float


@dataclass(frozen=True)
class Bud:
    """Bud state and distances for hormone calculation."""

    state: BudState
    distance_from_apex_cm: float


@dataclass(frozen=True)
class Fruit:
    """Fruit as a strong carbon sink and hormone source."""

    dry_mass_g: float
    gibberellin_level: float


@dataclass
class Metamer:
    """Minimal functional unit: stem, leaf, bud, optional fruit."""

    stem: Stem
    leaf: Leaf
    bud: Bud
    fruit: Fruit | None = None
    children: Sequence["Metamer"] = field(default_factory=tuple)

    @property
    def has_fruit(self) -> bool:
        return self.fruit is not None
