"""Physiology calculations for source-sink and hormone models."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp


@dataclass(frozen=True)
class PhotosynthesisInputs:
    incident_light: float
    p_max: float
    k: float
    r_day: float


@dataclass(frozen=True)
class HormoneInputs:
    auxin_apex: float
    cytokinin: float
    distance: float
    lambda_factor: float


def compute_photosynthesis(inputs: PhotosynthesisInputs) -> float:
    """Compute net carbon fixation using simplified light response."""

    return inputs.p_max * (1.0 - exp(-inputs.k * inputs.incident_light)) - inputs.r_day


def compute_activation_potential(inputs: HormoneInputs) -> float:
    """Compute bud activation potential from cytokinin/auxin ratio."""

    denominator = (inputs.auxin_apex * inputs.distance) + inputs.lambda_factor
    if denominator <= 0:
        return 0.0
    return inputs.cytokinin / denominator
