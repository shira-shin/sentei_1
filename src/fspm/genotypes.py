"""Genotype profile parameters from the design spec."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GenotypeProfile:
    apical_dominance: float
    branch_angle_deg: float
    internode_length_cm: float
    flowering_rate: float
    biennial_bearing_sensitivity: float


GENOTYPE_PROFILES = {
    "fuji": GenotypeProfile(
        apical_dominance=0.85,
        branch_angle_deg=45.0,
        internode_length_cm=5.0,
        flowering_rate=0.5,
        biennial_bearing_sensitivity=0.8,
    ),
    "orin": GenotypeProfile(
        apical_dominance=0.65,
        branch_angle_deg=70.0,
        internode_length_cm=4.0,
        flowering_rate=0.7,
        biennial_bearing_sensitivity=0.5,
    ),
    "m9": GenotypeProfile(
        apical_dominance=0.4,
        branch_angle_deg=50.0,
        internode_length_cm=2.5,
        flowering_rate=0.9,
        biennial_bearing_sensitivity=0.3,
    ),
}
