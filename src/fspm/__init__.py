"""Functional-Structural Plant Model (FSPM) toolkit."""

from .genotypes import GENOTYPE_PARAMS, GenotypeParams
from .geometry import GrowthDirectionWeights, TropismInputs, compute_growth_direction
from .models import AppleTree, BudStatus, Metamer, RootSystem
from .physiology import (
    ApplePhysiology,
    HormoneInputs,
    PhotosynthesisInputs,
    compute_activation_potential,
    compute_photosynthesis,
)
from .simulation import Environment, SimulationStepResult, prune_metamer, simulate_step

__all__ = [
    "AppleTree",
    "ApplePhysiology",
    "BudStatus",
    "Environment",
    "GENOTYPE_PARAMS",
    "GenotypeParams",
    "GrowthDirectionWeights",
    "HormoneInputs",
    "Metamer",
    "PhotosynthesisInputs",
    "RootSystem",
    "SimulationStepResult",
    "TropismInputs",
    "compute_activation_potential",
    "compute_growth_direction",
    "compute_photosynthesis",
    "prune_metamer",
    "simulate_step",
]
