"""Genotype profile parameters from the design spec."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GenotypeParams:
    apical_dominance: float
    internode_length: float
    branching_angle: float
    flower_rate: float


GENOTYPE_PARAMS: dict[str, GenotypeParams] = {
    "fuji": GenotypeParams(
        apical_dominance=0.85,
        internode_length=0.05,
        branching_angle=0.78,
        flower_rate=0.4,
    ),
    "orin": GenotypeParams(
        apical_dominance=0.65,
        internode_length=0.04,
        branching_angle=1.22,
        flower_rate=0.7,
    ),
}
