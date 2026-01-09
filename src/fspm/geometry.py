"""Geometry rules for growth direction, taper, and tropism."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

Vector3 = Tuple[float, float, float]


@dataclass(frozen=True)
class TropismInputs:
    sun_vector: Vector3
    up_vector: Vector3
    parent_vector: Vector3


@dataclass(frozen=True)
class GrowthDirectionWeights:
    light: float
    gravity: float
    inertia: float


def _scale(vector: Vector3, weight: float) -> Vector3:
    return (vector[0] * weight, vector[1] * weight, vector[2] * weight)


def _add(a: Vector3, b: Vector3) -> Vector3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def compute_growth_direction(inputs: TropismInputs, weights: GrowthDirectionWeights) -> Vector3:
    """Combine tropism vectors to compute growth direction."""

    combined = _add(
        _add(_scale(inputs.sun_vector, weights.light), _scale(inputs.up_vector, weights.gravity)),
        _scale(inputs.parent_vector, weights.inertia),
    )
    return combined
