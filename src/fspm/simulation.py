"""Simulation step utilities for a simplified FSPM."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .models import Metamer
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


@dataclass(frozen=True)
class Environment:
    temperature_c: float
    auxin_apex: float
    cytokinin_root: float


@dataclass(frozen=True)
class SimulationStepResult:
    total_assimilation: float
    allocation: AllocationResult
    activation_potentials: list[float]
    flowering_probabilities: list[float]


def simulate_step(metamers: Iterable[Metamer], env: Environment) -> SimulationStepResult:
    """Run a single time-step of photosynthesis and allocation."""

    assimilation = 0.0
    activation_potentials: list[float] = []
    flowering_probabilities: list[float] = []
    hormones = HormoneLevels(auxin_apex=env.auxin_apex, cytokinin_root=env.cytokinin_root)

    for metamer in metamers:
        inputs = PhotosynthesisInputs(
            incident_light_umol=metamer.leaf.incident_light_umol,
            nitrogen_g_m2=metamer.leaf.nitrogen_g_m2,
            temperature_c=env.temperature_c,
        )
        assimilation += compute_photosynthesis(inputs)
        activation_potentials.append(
            compute_activation_potential(hormones, metamer.bud.distance_from_apex_cm)
        )
        gibberellin = metamer.fruit.gibberellin_level if metamer.fruit else 0.0
        flowering_probabilities.append(
            compute_flowering_probability(assimilation, gibberellin)
        )

    strengths = SourceSinkStrengths(
        fruit=2.0,
        shoot=1.5,
        root=1.0,
        storage=0.5,
    )
    allocation = allocate_resources(assimilation, strengths)

    return SimulationStepResult(
        total_assimilation=assimilation,
        allocation=allocation,
        activation_potentials=activation_potentials,
        flowering_probabilities=flowering_probabilities,
    )
