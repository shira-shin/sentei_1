"""Functional-Structural Plant Model (FSPM) toolkit."""

from .genotypes import GENOTYPE_PROFILES, GenotypeProfile
from .geometry import GrowthDirectionWeights, TropismInputs, compute_growth_direction
from .models import Bud, BudState, Fruit, Leaf, Metamer, Stem
from .physiology import (
    AllocationResult,
    HormoneLevels,
    PhotosynthesisInputs,
    SourceSinkStrengths,
    allocate_resources,
    compute_activation_potential,
    compute_flowering_probability,
    compute_photosynthesis,
)
from .simulation import Environment, SimulationStepResult, simulate_step

__all__ = [
    "AllocationResult",
    "Bud",
    "BudState",
    "Environment",
    "Fruit",
    "GENOTYPE_PROFILES",
    "GenotypeProfile",
    "GrowthDirectionWeights",
    "HormoneLevels",
    "Leaf",
    "Metamer",
    "PhotosynthesisInputs",
    "SimulationStepResult",
    "SourceSinkStrengths",
    "Stem",
    "TropismInputs",
    "allocate_resources",
    "compute_activation_potential",
    "compute_flowering_probability",
    "compute_growth_direction",
    "compute_photosynthesis",
    "simulate_step",
]
