"""FastAPI app exposing the FSPM simulation for the game UI."""

from __future__ import annotations

from math import pi, sin
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from fspm import (
    AppleTree,
    BudStatus,
    Environment,
    Metamer,
    RootSystem,
    prune_metamer,
    simulate_step,
)
from fspm.serialization import metamer_to_dict, tree_to_dict

app = FastAPI(title="FSPM Pruning Game API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/web", StaticFiles(directory="web", html=True), name="web")


class RootSystemPayload(BaseModel):
    nitrogen_uptake: float = 1.2
    cytokinin_level: float = 0.6


class MetamerPayload(BaseModel):
    id: int = 1
    parent_id: Optional[int] = None
    order: int = 0
    length: float = 0.05
    thickness: float = 0.4
    angle_world: tuple[float, float, float] = (0.0, 1.0, 0.0)
    biomass_carbon: float = 1.2
    nsc_store: float = 4.0
    bud_status: BudStatus = BudStatus.DORMANT
    leaf_area: float = 30.0
    incident_light: float = 1200.0


class TreeResetRequest(BaseModel):
    genotype_params: dict[str, float] | None = Field(
        default=None,
        description="Overrides for genotype parameters.",
    )
    root_system: RootSystemPayload | None = None
    metamer: MetamerPayload | None = None


class StepRequest(BaseModel):
    temperature_c: float = 25.0
    co2_ppm: float = 410.0
    vcmax25: float = 80.0
    jmax25: float = 150.0
    rd25: float = 1.2
    activation_threshold: float = 0.6
    lambda_factor: float = 0.5
    kappa: float = 0.02


class YearSimulationRequest(BaseModel):
    days: int = Field(default=365, ge=1, le=3650)
    base_temperature_c: float = 15.0
    seasonal_amplitude_c: float = 10.0
    co2_ppm: float = 410.0
    vcmax25: float = 80.0
    jmax25: float = 150.0
    rd25: float = 1.2
    activation_threshold: float = 0.6
    lambda_factor: float = 0.5
    kappa: float = 0.02


class PruneRequest(BaseModel):
    metamer_id: int


DEFAULT_GENOTYPE_PARAMS = {
    "apical_dominance": 0.85,
    "apical_decay": 2.5,
    "internode_length": 0.05,
    "branching_angle": 0.78,
    "flower_rate": 0.4,
    "canopy_extinction": 1.2,
    "kappa": 0.02,
    "maintenance_cost": 0.001,
    "construction_cost": 0.5,
    "energy_threshold": 0.2,
}


def _build_tree(request: TreeResetRequest | None) -> AppleTree:
    genotype_params = DEFAULT_GENOTYPE_PARAMS.copy()
    root_payload = RootSystemPayload()
    metamer_payload = MetamerPayload()
    if request:
        if request.genotype_params:
            genotype_params.update(request.genotype_params)
        if request.root_system:
            root_payload = request.root_system
        if request.metamer:
            metamer_payload = request.metamer

    root_system = RootSystem(
        nitrogen_uptake=root_payload.nitrogen_uptake,
        cytokinin_level=root_payload.cytokinin_level,
    )
    tree = AppleTree(genotype_params=genotype_params, root_system=root_system)
    metamer = Metamer(
        id=metamer_payload.id,
        parent_id=metamer_payload.parent_id,
        order=metamer_payload.order,
        length=metamer_payload.length,
        thickness=metamer_payload.thickness,
        angle_world=metamer_payload.angle_world,
        biomass_carbon=metamer_payload.biomass_carbon,
        nsc_store=metamer_payload.nsc_store,
        bud_status=metamer_payload.bud_status,
        leaf_area=metamer_payload.leaf_area,
        incident_light=metamer_payload.incident_light,
    )
    tree.add_root(metamer)
    return tree


def _activate_buds_after_prune(tree: AppleTree, target: Metamer) -> None:
    if target.parent_id is None:
        return
    parent = tree.find_metamer(target.parent_id)
    if not parent:
        return
    if parent.bud_status == BudStatus.DORMANT:
        parent.bud_status = BudStatus.ACTIVE
    for child in parent.children:
        if not child.is_pruned and child.bud_status == BudStatus.DORMANT:
            child.bud_status = BudStatus.ACTIVE


def _apply_winter_dormancy(tree: AppleTree) -> None:
    for metamer in tree.iter_metamers():
        if metamer.bud_status != BudStatus.DEAD:
            metamer.bud_status = BudStatus.DORMANT


def _apply_pruning_apical_release(tree: AppleTree) -> bool:
    apical_pruned = any(metamer.is_pruned for metamer in tree.roots)
    if not apical_pruned:
        return False
    current = tree.genotype_params.get("apical_dominance", 0.85)
    tree.genotype_params["apical_dominance"] = max(0.0, current * 0.6)
    return True


CURRENT_TREE = _build_tree(None)
CURRENT_ENV = Environment(temperature_c=25.0)


@app.get("/state")
def get_state() -> dict[str, object]:
    return {"tree": tree_to_dict(CURRENT_TREE)}


@app.post("/reset")
def reset_tree(request: TreeResetRequest | None = None) -> dict[str, object]:
    global CURRENT_TREE
    CURRENT_TREE = _build_tree(request)
    return {"tree": tree_to_dict(CURRENT_TREE)}


@app.post("/step")
def step_simulation(request: StepRequest) -> dict[str, object]:
    global CURRENT_ENV
    CURRENT_ENV = Environment(
        temperature_c=request.temperature_c,
        co2_ppm=request.co2_ppm,
        vcmax25=request.vcmax25,
        jmax25=request.jmax25,
        rd25=request.rd25,
        activation_threshold=request.activation_threshold,
        lambda_factor=request.lambda_factor,
        kappa=request.kappa,
    )
    result = simulate_step(CURRENT_TREE, CURRENT_ENV)
    return {
        "result": {
            "total_assimilation": result.total_assimilation,
            "activation_potentials": result.activation_potentials,
            "new_metamers": [metamer_to_dict(metamer) for metamer in result.new_metamers],
        },
        "tree": tree_to_dict(CURRENT_TREE),
    }


@app.post("/prune")
def prune(request: PruneRequest) -> dict[str, object]:
    target = CURRENT_TREE.find_metamer(request.metamer_id)
    if not target:
        raise HTTPException(status_code=404, detail="Metamer not found")
    prune_metamer(CURRENT_TREE, target)
    _activate_buds_after_prune(CURRENT_TREE, target)
    return {"tree": tree_to_dict(CURRENT_TREE)}


@app.post("/simulate_year")
def simulate_year(request: YearSimulationRequest) -> dict[str, object]:
    global CURRENT_ENV
    total_assimilation = 0.0
    total_new_metamers: list[dict[str, object]] = []
    for day in range(request.days):
        seasonal_phase = (2.0 * pi * day) / request.days
        temperature = request.base_temperature_c + request.seasonal_amplitude_c * sin(seasonal_phase)
        CURRENT_ENV = Environment(
            temperature_c=temperature,
            co2_ppm=request.co2_ppm,
            vcmax25=request.vcmax25,
            jmax25=request.jmax25,
            rd25=request.rd25,
            activation_threshold=request.activation_threshold,
            lambda_factor=request.lambda_factor,
            kappa=request.kappa,
        )
        result = simulate_step(CURRENT_TREE, CURRENT_ENV)
        total_assimilation += result.total_assimilation
        total_new_metamers.extend(metamer_to_dict(metamer) for metamer in result.new_metamers)

    _apply_winter_dormancy(CURRENT_TREE)
    apical_released = _apply_pruning_apical_release(CURRENT_TREE)
    return {
        "result": {
            "total_assimilation": total_assimilation,
            "new_metamers": total_new_metamers,
            "apical_dominance_released": apical_released,
        },
        "tree": tree_to_dict(CURRENT_TREE),
    }
