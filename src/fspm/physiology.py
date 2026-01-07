"""Physiology calculations for source-sink and hormone models."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, pi, sqrt

from .models import AppleTree, Metamer


@dataclass(frozen=True)
class PhotosynthesisInputs:
    incident_light: float
    t_leaf: float
    c_a: float
    vcmax25: float
    jmax25: float
    rd25: float
    kc25: float = 404.9
    ko25: float = 278400.0
    gamma_star25: float = 42.75
    ci_ratio: float = 0.7
    o2: float = 210000.0


@dataclass(frozen=True)
class HormoneInputs:
    auxin_apex: float
    cytokinin: float
    distance: float
    lambda_factor: float


def _arrhenius(rate_25: float, activation_energy: float, temperature_c: float) -> float:
    temperature_k = temperature_c + 273.15
    ref_k = 25.0 + 273.15
    gas_constant = 8.314
    return rate_25 * exp((activation_energy / gas_constant) * ((temperature_k - ref_k) / (temperature_k * ref_k)))


def compute_photosynthesis(inputs: PhotosynthesisInputs) -> float:
    """Compute net carbon fixation using the FvCB model."""

    vcmax = _arrhenius(inputs.vcmax25, 65000.0, inputs.t_leaf)
    jmax = _arrhenius(inputs.jmax25, 50000.0, inputs.t_leaf)
    rd = inputs.rd25 * (2.0 ** ((inputs.t_leaf - 25.0) / 10.0))

    ci = inputs.c_a * inputs.ci_ratio
    km = inputs.kc25 * (1.0 + inputs.o2 / inputs.ko25)
    gamma_star = inputs.gamma_star25

    alpha = 0.24
    theta = 0.7
    j_light = alpha * inputs.incident_light
    j = (j_light + jmax - sqrt((j_light + jmax) ** 2 - 4.0 * theta * j_light * jmax)) / (2.0 * theta)

    a_c = vcmax * (ci - gamma_star) / (ci + km)
    a_j = j * (ci - gamma_star) / (4.5 * ci + 10.5 * gamma_star)

    return min(a_c, a_j) - rd


def compute_activation_potential(inputs: HormoneInputs) -> float:
    """Compute bud activation potential from cytokinin/auxin ratio."""

    denominator = (inputs.auxin_apex * inputs.distance) + inputs.lambda_factor
    if denominator <= 0:
        return 0.0
    return inputs.cytokinin / denominator


class ApplePhysiology:
    """Physiological engine for carbon, hormones, mechanics, and allocation."""

    def __init__(self, genotype_params: dict[str, float]):
        self.genotype_params = genotype_params
        self.kappa = genotype_params.get("kappa", 0.02)
        self.auxin_transport_efficiency = genotype_params.get("auxin_transport_efficiency", 0.8)
        self.auxin_production = genotype_params.get("auxin_production", 1.0)
        self.cytokinin_decay = genotype_params.get("cytokinin_decay", 0.2)
        self.lambda_factor = genotype_params.get("lambda_factor", 0.5)
        self.wood_density = genotype_params.get("wood_density", 0.6)
        self.carbon_fraction = genotype_params.get("carbon_fraction", 0.45)
        self.branch_elasticity = genotype_params.get("branch_elasticity", 1.0)
        self.mechanical_auxin_slowdown = genotype_params.get("mechanical_auxin_slowdown", 0.9)
        self.activation_bias_strength = genotype_params.get("activation_bias_strength", 0.6)
        self.ga_per_fruit_g = genotype_params.get("ga_per_fruit_g", 0.02)
        self.ga_bias_strength = genotype_params.get("ga_bias_strength", 0.08)
        self.last_gibberellin = 0.0

    def calculate_photosynthesis(
        self,
        incident_light: float,
        t_leaf: float,
        c_a: float,
        vcmax25: float,
        jmax25: float,
        rd25: float,
        kc25: float = 404.9,
        ko25: float = 278400.0,
        gamma_star25: float = 42.75,
        ci_ratio: float = 0.7,
        o2: float = 210000.0,
    ) -> float:
        inputs = PhotosynthesisInputs(
            incident_light=incident_light,
            t_leaf=t_leaf,
            c_a=c_a,
            vcmax25=vcmax25,
            jmax25=jmax25,
            rd25=rd25,
            kc25=kc25,
            ko25=ko25,
            gamma_star25=gamma_star25,
            ci_ratio=ci_ratio,
            o2=o2,
        )
        return compute_photosynthesis(inputs)

    def update_pipe_model(self, metamer: Metamer, descendant_leaf_area: float) -> None:
        area_node = self.kappa * descendant_leaf_area
        if area_node <= 0:
            return
        diameter = sqrt(4.0 * area_node / pi)
        metamer.thickness = diameter
        radius = diameter / 2.0
        volume = pi * radius**2 * metamer.length
        dry_weight = volume * self.wood_density
        metamer.biomass_dry_weight = dry_weight
        metamer.biomass_carbon = dry_weight * self.carbon_fraction

    def calculate_mechanical_stress(self, metamer: Metamer) -> float:
        radius = max(metamer.thickness / 2.0, 1e-6)
        inertia = pi * radius**4 / 4.0
        load = metamer.fruit_weight + metamer.leaf_weight
        if inertia <= 0 or self.branch_elasticity <= 0:
            metamer.sag_angle = 0.0
            return 0.0
        angle_rad = (load * metamer.length**2) / (2.0 * self.branch_elasticity * inertia)
        angle_deg = min(90.0, angle_rad * 180.0 / pi)
        metamer.sag_angle = angle_deg
        return angle_deg

    def transport_hormones(self, tree: AppleTree) -> None:
        parent_map = {metamer.id: metamer.parent_id for metamer in tree.metamers}
        for metamer in tree.metamers:
            self.calculate_mechanical_stress(metamer)
            metamer.auxin_level = 0.0
            metamer.cytokinin_level = 0.0

        for metamer in sorted(tree.metamers, key=lambda item: item.order, reverse=True):
            if metamer.is_pruned:
                metamer.auxin_level = 0.0
                continue
            metamer.auxin_level += self.auxin_production
            flow_factor = max(0.0, 1.0 - (metamer.sag_angle / 90.0) * self.mechanical_auxin_slowdown)
            parent_id = parent_map.get(metamer.id)
            if parent_id is not None:
                parent = tree.find_metamer(parent_id)
                if parent and not parent.is_pruned:
                    parent.auxin_level += metamer.auxin_level * self.auxin_transport_efficiency * flow_factor

        for metamer in tree.metamers:
            distance = metamer.distance_from_root
            metamer.cytokinin_level = tree.root_system.cytokinin_level * exp(-self.cytokinin_decay * distance)
            denominator = (metamer.auxin_level * metamer.distance_from_apex) + self.lambda_factor
            base_potential = 0.0 if denominator <= 0 else metamer.cytokinin_level / denominator
            mechanical_bias = (metamer.sag_angle / 90.0) * self.activation_bias_strength
            metamer.activation_potential = base_potential + mechanical_bias

    def allocate_resources(self, nsc_reserve: float, sink_strengths: dict[str, float]) -> dict[str, float]:
        priorities = {"fruit": 4.0, "shoot": 3.0, "root": 2.0, "storage": 1.0}
        weighted = {
            key: sink_strengths.get(key, 0.0) * priorities[key] for key in priorities
        }
        total = sum(weighted.values())
        if total <= 0:
            self.last_gibberellin = 0.0
            return {key: 0.0 for key in priorities}
        allocations = {key: nsc_reserve * (value / total) for key, value in weighted.items()}
        self.last_gibberellin = allocations["fruit"] * self.ga_per_fruit_g
        return allocations

    def bud_fate_decision(self, base_flower_probability: float, gibberellin: float | None = None) -> float:
        ga_level = self.last_gibberellin if gibberellin is None else gibberellin
        adjusted = base_flower_probability - (self.ga_bias_strength * ga_level)
        return max(0.0, min(1.0, adjusted))
