from __future__ import annotations

"""
Phrase + cadence templates used by the generator.

Templates are intentionally simple dicts. They provide structure (cadence targets,
bar-count constraints, and starting scale-degree options) while still leaving room
for stochastic rhythm/pitch generation.

v1 note: this project intentionally excludes 6/8 meter, so templates only target
4/4, 3/4, and 2/4.
"""

from typing import Any


_TEMPLATES_T1: list[dict[str, Any]] = [
    {
        "id": "T1_1bar_authentic_321",
        "bar_counts": [1],
        "skeleton": "3-2-1",
        "cadence_type": "authentic",
        "cadence_degrees": [2, 1],
        "start_degree_options": [1, 3, 5],
    },
    {
        "id": "T1_2bar_authentic_321",
        "bar_counts": [2],
        "skeleton": "3-2-1",
        "cadence_type": "authentic",
        "cadence_degrees": [2, 1],
        "start_degree_options": [1, 3, 5],
    },
    {
        "id": "T1_2bar_authentic_54321",
        "bar_counts": [2],
        "skeleton": "5-4-3-2-1",
        "cadence_type": "authentic",
        "cadence_degrees": [2, 1],
        "start_degree_options": [1, 3, 5],
    },
    {
        "id": "T1_1bar_authentic_521",
        "bar_counts": [1],
        "skeleton": "5-2-1",
        "cadence_type": "authentic",
        "cadence_degrees": [7, 1],
        "start_degree_options": [1, 3, 5],
    },
    {
        "id": "T1_2bar_authentic_521",
        "bar_counts": [2],
        "skeleton": "5-2-1",
        "cadence_type": "authentic",
        "cadence_degrees": [7, 1],
        "start_degree_options": [1, 3, 5],
    },
]


_TEMPLATES_T2: list[dict[str, Any]] = [
    {
        "id": "T2_2bar_authentic_321",
        "bar_counts": [2],
        "skeleton": "3-2-1",
        "cadence_type": "authentic",
        "cadence_degrees": [2, 1],
        "start_degree_options": [1, 2, 3, 5],
    },
    {
        "id": "T2_3bar_half_12",
        "bar_counts": [3],
        "skeleton": "1-2",
        "cadence_type": "half",
        "cadence_degrees": [4, 5],
        "start_degree_options": [1, 2, 3, 5],
    },
    {
        "id": "T2_4bar_authentic_54321",
        "bar_counts": [4],
        "skeleton": "5-4-3-2-1",
        "cadence_type": "authentic",
        "cadence_degrees": [2, 1],
        "start_degree_options": [1, 2, 3, 5],
    },
    {
        "id": "T2_3bar_deceptive_73",
        "bar_counts": [3],
        "skeleton": "7-3",
        "cadence_type": "deceptive",
        "cadence_degrees": [2, 3],
        "start_degree_options": [1, 2, 3, 5],
    },
    {
        "id": "T2_2bar_half_45",
        "bar_counts": [2],
        "skeleton": "4-5",
        "cadence_type": "half",
        "cadence_degrees": [4, 5],
        "start_degree_options": [1, 2, 3, 5],
    },
]


_TEMPLATES_T3: list[dict[str, Any]] = [
    {
        "id": "T3_1bar_open_any",
        "bar_counts": [1],
        "skeleton": "open",
        "cadence_type": "open",
        "cadence_degrees": None,
        "start_degree_options": [1, 2, 3, 4, 5, 6, 7],
    },
    {
        "id": "T3_2bar_plagal_43",
        "bar_counts": [2],
        "skeleton": "4-3",
        "cadence_type": "plagal",
        "cadence_degrees": [4, 3],
        "start_degree_options": [1, 2, 3, 4, 5, 6, 7],
    },
    {
        "id": "T3_4bar_authentic_721",
        "bar_counts": [4],
        "skeleton": "7-2-1",
        "cadence_type": "authentic",
        "cadence_degrees": [7, 1],
        "start_degree_options": [1, 2, 3, 4, 5, 6, 7],
    },
    {
        "id": "T3_3bar_deceptive_23",
        "bar_counts": [3],
        "skeleton": "2-3",
        "cadence_type": "deceptive",
        "cadence_degrees": [2, 3],
        "start_degree_options": [1, 2, 3, 4, 5, 6, 7],
    },
    {
        "id": "T3_2bar_half_15",
        "bar_counts": [2],
        "skeleton": "1-5",
        "cadence_type": "half",
        "cadence_degrees": [4, 5],
        "start_degree_options": [1, 2, 3, 4, 5, 6, 7],
    },
]


def get_templates_for_tier(tier: int) -> list[dict[str, Any]]:
    if tier == 1:
        return list(_TEMPLATES_T1)
    if tier == 2:
        return list(_TEMPLATES_T2)
    if tier == 3:
        return list(_TEMPLATES_T3)
    raise ValueError(f"tier must be 1, 2, or 3 (got {tier})")

