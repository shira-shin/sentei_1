"""Core structural primitives for the FSPM design spec."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Optional, Tuple

Vector3 = Tuple[float, float, float]


class BudStatus(str, Enum):
    ACTIVE = "Active"
    DORMANT = "Dormant"
    FLOWER = "Flower"
    DEAD = "Dead"


@dataclass
class Metamer:
    """Minimal functional unit of the apple tree."""

    id: int
    parent_id: Optional[int]
    order: int
    length: float
    thickness: float
    angle_world: Vector3
    biomass_carbon: float
    nsc_store: float
    bud_status: BudStatus
    is_pruned: bool = False
    leaf_area: float = 0.0
    incident_light: float = 0.0
    children: list["Metamer"] = field(default_factory=list)

    def add_child(self, child: "Metamer") -> None:
        self.children.append(child)

    def descendant_leaf_area(self) -> float:
        return sum(child.descendant_leaf_area() for child in self.children) + self.leaf_area

    def iter_descendants(self) -> Iterable["Metamer"]:
        for child in self.children:
            yield child
            yield from child.iter_descendants()

    @property
    def distance_from_apex(self) -> float:
        return self.order * self.length


@dataclass(frozen=True)
class RootSystem:
    """Root system parameters for nitrogen uptake and cytokinin production."""

    nitrogen_uptake: float
    cytokinin_level: float


@dataclass
class AppleTree:
    """Container for metamers and genotype-specific parameters."""

    genotype_params: dict[str, float]
    root_system: RootSystem
    metamers: list[Metamer] = field(default_factory=list)

    def add_metamer(self, metamer: Metamer) -> None:
        self.metamers.append(metamer)

    def find_metamer(self, metamer_id: int) -> Optional[Metamer]:
        return next((metamer for metamer in self.metamers if metamer.id == metamer_id), None)

    def iter_active_metamers(self) -> Iterable[Metamer]:
        return (metamer for metamer in self.metamers if not metamer.is_pruned)
