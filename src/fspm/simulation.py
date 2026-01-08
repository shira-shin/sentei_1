"""Simulation step utilities for a simplified FSPM."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import count
from math import exp

from .models import AppleTree, BudStatus, Metamer
from .physiology import (
    ApplePhysiology,
    HormoneInputs,
    compute_activation_potential,
)


@dataclass(frozen=True)
class Environment:
    temperature_c: float
    co2_ppm: float = 410.0
    vcmax25: float = 80.0
    jmax25: float = 150.0
    rd25: float = 1.2
    activation_threshold: float = 1.0
    lambda_factor: float = 0.5
    kappa: float = 0.02


@dataclass(frozen=True)
class SimulationStepResult:
    total_assimilation: float
    activation_potentials: list[float]
    new_metamers: list[Metamer]


def _spawn_metamer(parent: Metamer, new_id: int) -> Metamer:
    return Metamer(
        id=new_id,
        parent_id=parent.id,
        order=parent.order + 1,
        length=parent.length,
        thickness=parent.thickness,
        angle_world=parent.angle_world,
        biomass_carbon=0.0,
        nsc_store=max(0.1, parent.nsc_store * 0.2),
        bud_status=BudStatus.DORMANT,
    )


def prune_metamer(tree: AppleTree, target: Metamer) -> None:
    target.is_pruned = True
    for descendant in target.iter_descendants():
        descendant.is_pruned = True

    if target.parent_id is None:
        return
    parent = tree.find_metamer(target.parent_id)
    if not parent:
        return
    if parent.bud_status == BudStatus.DORMANT:
        parent.bud_status = BudStatus.ACTIVE
    for sibling in parent.children:
        if not sibling.is_pruned and sibling.bud_status == BudStatus.DORMANT:
            sibling.bud_status = BudStatus.ACTIVE

    highest_order = max((metamer.order for metamer in tree.iter_active_metamers()), default=parent.order)
    if target.order >= highest_order:
        for metamer in tree.iter_active_metamers():
            if metamer.bud_status == BudStatus.DORMANT:
                metamer.bud_status = BudStatus.ACTIVE


def simulate_step(tree: AppleTree, env: Environment) -> SimulationStepResult:
    """Run a single time-step of photosynthesis, hormone activation, and pipe update."""

    assimilation = 0.0
    maintenance_total = 0.0
    activation_potentials: list[float] = []
    new_metamers: list[Metamer] = []
    next_id = count(start=max((metamer.id for metamer in tree.iter_metamers()), default=0) + 1)
    physiology = ApplePhysiology(tree.genotype_params)

    physiology.transport_hormones(tree)

    active_metamers = list(tree.iter_active_metamers())
    total_leaf_area = sum(metamer.leaf_area for metamer in active_metamers)
    overlap_map: dict[int, float] = {}
    cumulative_leaf_area = 0.0
    for metamer in sorted(active_metamers, key=lambda item: item.order, reverse=True):
        overlap_map[metamer.id] = 0.0 if total_leaf_area <= 0 else min(1.0, cumulative_leaf_area / total_leaf_area)
        cumulative_leaf_area += metamer.leaf_area

    apex = max(active_metamers, key=lambda item: item.order, default=None)
    apical_auxin = apex.auxin_level if apex else 0.0
    apical_strength = tree.genotype_params.get("apical_dominance", 0.85)
    apical_decay = tree.genotype_params.get("apical_decay", 2.5)
    apex_distance = apex.distance_from_root if apex else 0.0

    per_metamer_potential: dict[int, float] = {}

    for metamer in active_metamers:
        if metamer.is_pruned:
            continue
        assimilation += physiology.calculate_photosynthesis(
            incident_light=metamer.incident_light,
            canopy_overlap=overlap_map.get(metamer.id, 0.0),
            t_leaf=env.temperature_c,
            c_a=env.co2_ppm,
            vcmax25=env.vcmax25,
            jmax25=env.jmax25,
            rd25=env.rd25,
        )
        maintenance_total += metamer.biomass_carbon * tree.genotype_params.get("maintenance_cost", 0.001)

        hormone_inputs = HormoneInputs(
            auxin_apex=apical_auxin,
            cytokinin=tree.root_system.cytokinin_level,
            distance=metamer.distance_from_apex,
            lambda_factor=env.lambda_factor,
        )
        potential = max(metamer.activation_potential, compute_activation_potential(hormone_inputs))
        activation_potentials.append(potential)
        per_metamer_potential[metamer.id] = potential

        physiology.update_pipe_model(metamer, metamer.descendant_leaf_area())

    if maintenance_total > 0 and assimilation < maintenance_total:
        maintenance_total = assimilation * 0.85
    net_assimilation = assimilation - maintenance_total
    if net_assimilation > 0:
        per_metamer_gain = net_assimilation / max(len(active_metamers), 1)
        for metamer in active_metamers:
            metamer.nsc_store += per_metamer_gain

    construction_cost = tree.genotype_params.get("construction_cost", 0.5)
    energy_threshold = tree.genotype_params.get("energy_threshold", 0.3)
    for metamer in active_metamers:
        if metamer.is_pruned:
            continue
        potential = per_metamer_potential.get(metamer.id, 0.0)
        distance_down = max(0.0, apex_distance - metamer.distance_from_root)
        apical_inhibition = apical_auxin * apical_strength * exp(-apical_decay * distance_down)
        suppressed_potential = potential - apical_inhibition
        branching_penalty = 1.0 + (0.25 * len(metamer.children))
        threshold_modifier = 0.75 if metamer.bud_status == BudStatus.ACTIVE else 1.0
        can_branch = (
            suppressed_potential >= env.activation_threshold * branching_penalty * threshold_modifier
            and metamer.nsc_store >= (energy_threshold + construction_cost)
            and metamer.bud_status in {BudStatus.DORMANT, BudStatus.ACTIVE}
            and net_assimilation > 0
        )
        if can_branch:
            metamer.bud_status = BudStatus.ACTIVE
            metamer.nsc_store = max(0.0, metamer.nsc_store - construction_cost)
            child = _spawn_metamer(metamer, next(next_id))
            tree.register_child(metamer, child)
            new_metamers.append(child)

    return SimulationStepResult(
        total_assimilation=assimilation,
        activation_potentials=activation_potentials,
        new_metamers=new_metamers,
    )
