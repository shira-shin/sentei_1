"""Simulation step utilities for a simplified FSPM."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import count
from math import pi

from .models import AppleTree, BudStatus, Metamer
from .physiology import HormoneInputs, PhotosynthesisInputs, compute_activation_potential, compute_photosynthesis


@dataclass(frozen=True)
class Environment:
    temperature_c: float
    p_max: float = 12.0
    light_extinction_k: float = 0.003
    r_day: float = 1.2
    activation_threshold: float = 1.0
    lambda_factor: float = 0.5
    kappa: float = 0.02


@dataclass(frozen=True)
class SimulationStepResult:
    total_assimilation: float
    activation_potentials: list[float]
    new_metamers: list[Metamer]


def _update_thickness_from_leaf_area(metamer: Metamer, kappa: float) -> None:
    total_leaf_area = metamer.descendant_leaf_area()
    area_node = kappa * total_leaf_area
    if area_node > 0:
        metamer.thickness = (4.0 * area_node / pi) ** 0.5


def _spawn_metamer(parent: Metamer, new_id: int) -> Metamer:
    return Metamer(
        id=new_id,
        parent_id=parent.id,
        order=parent.order + 1,
        length=parent.length,
        thickness=parent.thickness,
        angle_world=parent.angle_world,
        biomass_carbon=0.0,
        nsc_store=0.0,
        bud_status=BudStatus.DORMANT,
    )


def prune_metamer(target: Metamer) -> None:
    target.is_pruned = True
    for descendant in target.iter_descendants():
        descendant.is_pruned = True


def simulate_step(tree: AppleTree, env: Environment) -> SimulationStepResult:
    """Run a single time-step of photosynthesis, hormone activation, and pipe update."""

    assimilation = 0.0
    activation_potentials: list[float] = []
    new_metamers: list[Metamer] = []
    next_id = count(start=max((metamer.id for metamer in tree.metamers), default=0) + 1)

    for metamer in tree.iter_active_metamers():
        if metamer.is_pruned:
            continue
        inputs = PhotosynthesisInputs(
            incident_light=metamer.incident_light,
            p_max=env.p_max,
            k=env.light_extinction_k,
            r_day=env.r_day,
        )
        assimilation += compute_photosynthesis(inputs)

        hormone_inputs = HormoneInputs(
            auxin_apex=tree.genotype_params["apical_dominance"],
            cytokinin=tree.root_system.cytokinin_level,
            distance=metamer.distance_from_apex,
            lambda_factor=env.lambda_factor,
        )
        potential = compute_activation_potential(hormone_inputs)
        activation_potentials.append(potential)

        if potential >= env.activation_threshold and metamer.bud_status == BudStatus.DORMANT:
            metamer.bud_status = BudStatus.ACTIVE
            child = _spawn_metamer(metamer, next(next_id))
            metamer.add_child(child)
            new_metamers.append(child)

        _update_thickness_from_leaf_area(metamer, env.kappa)

    for metamer in new_metamers:
        tree.add_metamer(metamer)

    return SimulationStepResult(
        total_assimilation=assimilation,
        activation_potentials=activation_potentials,
        new_metamers=new_metamers,
    )
