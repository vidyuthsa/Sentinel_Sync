"""
sample_data.py — Pre-loaded mock pipeline so the dashboard is immediately
functional and visually populated on first launch.
"""

from __future__ import annotations

from datetime import datetime, date, timedelta
from typing import List

from models import Application, PipelineStage


def load_sample_applications() -> List[Application]:
    today = date.today()
    now = datetime.now()

    return [
        Application(
            company="Northwind Systems",
            title="Senior Backend Engineer",
            salary=168000,
            stage=PipelineStage.OFFER,
            last_interaction_date=today - timedelta(days=1),
            match_score=88.0,
            notes="Offer received; verbal comp discussion pending.",
        ),
        Application(
            company="Quantara Labs",
            title="ML Platform Engineer",
            salary=182000,
            stage=PipelineStage.TECHNICAL_INTERVIEW,
            interview_datetime=(now + timedelta(days=2)).replace(
                hour=14, minute=0, second=0, microsecond=0
            ),
            last_interaction_date=today - timedelta(days=2),
            match_score=76.0,
            notes="Second-round system design interview scheduled.",
        ),
        Application(
            company="Brightline Health",
            title="Full-Stack Developer",
            salary=131000,
            stage=PipelineStage.HR_INTERVIEW,
            interview_datetime=(now + timedelta(days=2)).replace(
                hour=16, minute=0, second=0, microsecond=0
            ),
            last_interaction_date=today - timedelta(days=1),
            match_score=70.0,
        ),
        Application(
            company="Carbide Robotics",
            title="Embedded Software Engineer",
            salary=1800000,
            currency="INR",
            stage=PipelineStage.APTITUDE_TEST,
            last_interaction_date=today - timedelta(days=8),
            match_score=58.0,
            notes="Online assessment completed; awaiting result. (18 LPA)",
        ),
        Application(
            company="Vertex Analytics",
            title="Data Scientist",
            salary=1450000,
            currency="INR",
            stage=PipelineStage.APPLIED,
            last_interaction_date=today - timedelta(days=9),
            match_score=64.0,
            notes="14.5 LPA",
        ),
        Application(
            company="Solace Cloud",
            title="DevOps Engineer",
            salary=128000,
            stage=PipelineStage.GHOSTED,
            last_interaction_date=today - timedelta(days=14),
            match_score=55.0,
            notes="No response since final-round interview.",
        ),
        Application(
            company="Pinpoint Retail",
            title="Frontend Engineer",
            salary=98000,
            stage=PipelineStage.REJECTED,
            last_interaction_date=today - timedelta(days=20),
            match_score=42.0,
        ),
        Application(
            company="Atlas Defense",
            title="Site Reliability Engineer",
            salary=155000,
            stage=PipelineStage.APPLIED,
            last_interaction_date=today - timedelta(days=3),
            match_score=61.0,
        ),
    ]
