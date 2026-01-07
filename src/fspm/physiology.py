"""Physiology calculations for source-sink and hormone models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PhotosynthesisInputs:
    incident_light_umol: float
    nitrogen_g_m2: float
    temperature_c: float
    dark_respiration: float = 1.0


@dataclass(frozen=True)
class SourceSinkStrengths:
    fruit: float
    shoot: float
    root: float
    storage: float


@dataclass(frozen=True)
class AllocationResult:
    fruit: float
    shoot: float
    root: float
    storage: float


@dataclass(frozen=True)
class HormoneLevels:
    auxin_apex: float
    cytokinin_root: float


def compute_photosynthesis(inputs: PhotosynthesisInputs) -> float:
    """Compute net CO2 assimilation using a simplified FvCB-style minimum."""

    a_c = 0.08 * inputs.incident_light_umol * inputs.nitrogen_g_m2
    a_j = 0.06 * inputs.incident_light_umol * (1.0 + inputs.temperature_c / 25.0)
    assimilation = min(a_c, a_j) - inputs.dark_respiration
    return max(0.0, assimilation)


def allocate_resources(total_carbon: float, strengths: SourceSinkStrengths) -> AllocationResult:
    """Allocate carbon based on sink strength competition."""

    total_strength = strengths.fruit + strengths.shoot + strengths.root + strengths.storage
    if total_strength <= 0:
        return AllocationResult(0.0, 0.0, 0.0, 0.0)

    def portion(strength: float) -> float:
        return (strength / total_strength) * total_carbon

    return AllocationResult(
        fruit=portion(strengths.fruit),
        shoot=portion(strengths.shoot),
        root=portion(strengths.root),
        storage=portion(strengths.storage),
    )


def compute_flowering_probability(carbon_reserve: float, gibberellin_level: float) -> float:
    """Estimate flower induction probability under biennial bearing pressure."""

    if gibberellin_level <= 0:
        return 1.0
    probability = carbon_reserve / (carbon_reserve + gibberellin_level)
    return max(0.0, min(1.0, probability))


def compute_activation_potential(
    hormones: HormoneLevels, distance_cm: float, lambda_factor: float = 0.5
) -> float:
    """Compute bud activation potential from cytokinin/auxin ratio."""

    denominator = hormones.auxin_apex * distance_cm + lambda_factor
    if denominator <= 0:
        return 0.0
    return hormones.cytokinin_root / denominator
