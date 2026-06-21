"""
priority.py — Ranking and portfolio-level metrics for Sentinel Sync.

Implements the Dynamic Priority Score sort and the headline metrics shown
on the dashboard (active count, average package, Ghost-Meter).
"""

from __future__ import annotations

from typing import List

from models import Application, PipelineStage, ACTIVE_STAGES, INTERVIEW_STAGES


def sorted_by_priority(applications: List[Application]) -> List[Application]:
    """Force-sort applications by Dynamic Priority Score, descending."""
    return sorted(applications, key=lambda a: a.priority_score, reverse=True)


def total_active(applications: List[Application]) -> int:
    return sum(1 for a in applications if a.stage in ACTIVE_STAGES)


def average_package(applications: List[Application]) -> float:
    """Returns the USD-equivalent average package across active applications.
    Callers should format this via currency.format_amount(value, "USD", ...)."""
    active_usd = [a.salary_usd_equivalent for a in applications if a.stage in ACTIVE_STAGES]
    return round(sum(active_usd) / len(active_usd), 2) if active_usd else 0.0


def ghost_meter(applications: List[Application]) -> dict:
    """Counts feeding the Ghost-Meter widget: explicitly ghosted vs. going cold."""
    ghosted_explicit = sum(1 for a in applications if a.stage == PipelineStage.GHOSTED)
    going_cold = sum(
        1 for a in applications
        if a.is_ghosted_candidate and a.stage != PipelineStage.GHOSTED
    )
    return {
        "ghosted": ghosted_explicit,
        "going_cold": going_cold,
        "total_at_risk": ghosted_explicit + going_cold,
    }


def find_offer_companies(applications: List[Application]) -> List[Application]:
    return [a for a in applications if a.stage == PipelineStage.OFFER]


def find_midstage_companies(applications: List[Application]) -> List[Application]:
    return [a for a in applications if a.stage in INTERVIEW_STAGES]
