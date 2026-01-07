"""Serialization helpers for API and UI clients."""

from __future__ import annotations

from .models import AppleTree, Metamer


def metamer_to_dict(metamer: Metamer) -> dict[str, object]:
    return {
        "id": metamer.id,
        "parent_id": metamer.parent_id,
        "order": metamer.order,
        "length": metamer.length,
        "thickness": metamer.thickness,
        "angle_world": metamer.angle_world,
        "biomass_carbon": metamer.biomass_carbon,
        "nsc_store": metamer.nsc_store,
        "bud_status": metamer.bud_status.value,
        "is_pruned": metamer.is_pruned,
        "leaf_area": metamer.leaf_area,
        "incident_light": metamer.incident_light,
        "children": [child.id for child in metamer.children],
        "auxin_level": metamer.auxin_level,
        "cytokinin_level": metamer.cytokinin_level,
        "activation_potential": metamer.activation_potential,
        "fruit_weight": metamer.fruit_weight,
        "leaf_weight": metamer.leaf_weight,
        "sag_angle": metamer.sag_angle,
        "biomass_dry_weight": metamer.biomass_dry_weight,
    }


def tree_to_dict(tree: AppleTree) -> dict[str, object]:
    return {
        "genotype_params": tree.genotype_params,
        "root_system": {
            "nitrogen_uptake": tree.root_system.nitrogen_uptake,
            "cytokinin_level": tree.root_system.cytokinin_level,
        },
        "roots": [metamer.id for metamer in tree.roots],
        "metamers": [metamer_to_dict(metamer) for metamer in tree.iter_metamers()],
    }
