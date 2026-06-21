"""
models.py — Core data schema for Sentinel Sync.

Defines the Application data model, pipeline stage enumeration, badge color
mapping, and serialization helpers used across the dashboard, scheduler,
and LLM engine.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from enum import Enum
from typing import Optional

from currency import to_usd


class PipelineStage(str, Enum):
    APPLIED = "Applied"
    APTITUDE_TEST = "Aptitude Test"
    TECHNICAL_INTERVIEW = "Technical Interview"
    HR_INTERVIEW = "HR Interview"
    OFFER = "Offer"
    GHOSTED = "Ghosted"
    REJECTED = "Rejected"


ALL_STAGES = [s.value for s in PipelineStage]

ACTIVE_STAGES = {
    PipelineStage.APPLIED,
    PipelineStage.APTITUDE_TEST,
    PipelineStage.TECHNICAL_INTERVIEW,
    PipelineStage.HR_INTERVIEW,
    PipelineStage.OFFER,
}

INTERVIEW_STAGES = {
    PipelineStage.APTITUDE_TEST,
    PipelineStage.TECHNICAL_INTERVIEW,
    PipelineStage.HR_INTERVIEW,
}

# Green for Offer, Amber for Ghosted, Red for Rejected, Blue for active interviews.
STAGE_BADGE_COLORS = {
    PipelineStage.APPLIED: "#3B82F6",
    PipelineStage.APTITUDE_TEST: "#3B82F6",
    PipelineStage.TECHNICAL_INTERVIEW: "#3B82F6",
    PipelineStage.HR_INTERVIEW: "#3B82F6",
    PipelineStage.OFFER: "#22C55E",
    PipelineStage.GHOSTED: "#F59E0B",
    PipelineStage.REJECTED: "#EF4444",
}


@dataclass
class Application:
    company: str
    title: str
    salary: float
    currency: str = "USD"
    stage: PipelineStage = PipelineStage.APPLIED
    interview_datetime: Optional[datetime] = None
    last_interaction_date: date = field(default_factory=date.today)
    match_score: float = 50.0  # Approval Probability, 0-100
    notes: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    @property
    def salary_usd_equivalent(self) -> float:
        """Normalized USD value used for cross-currency ranking math."""
        return to_usd(self.salary, self.currency)

    @property
    def priority_score(self) -> float:
        """Dynamic Priority Score = USD-equivalent Salary * Approval Probability."""
        return round(self.salary_usd_equivalent * (self.match_score / 100.0), 2)

    @property
    def days_since_contact(self) -> int:
        return (date.today() - self.last_interaction_date).days

    @property
    def is_ghosted_candidate(self) -> bool:
        """True if an active/mid-pipeline application has gone cold (>5 days)."""
        return (
            self.stage in (INTERVIEW_STAGES | {PipelineStage.APPLIED})
            and self.days_since_contact > 5
        )

    @property
    def badge_color(self) -> str:
        return STAGE_BADGE_COLORS.get(self.stage, "#6B7280")

    def to_dict(self) -> dict:
        d = asdict(self)
        d["stage"] = self.stage.value
        d["interview_datetime"] = (
            self.interview_datetime.isoformat() if self.interview_datetime else None
        )
        d["last_interaction_date"] = self.last_interaction_date.isoformat()
        d["priority_score"] = self.priority_score
        d["days_since_contact"] = self.days_since_contact
        return d

    @staticmethod
    def from_dict(d: dict) -> "Application":
        return Application(
            company=d["company"],
            title=d["title"],
            salary=float(d["salary"]),
            currency=d.get("currency", "USD"),
            stage=PipelineStage(d.get("stage", "Applied")),
            interview_datetime=(
                datetime.fromisoformat(d["interview_datetime"])
                if d.get("interview_datetime")
                else None
            ),
            last_interaction_date=(
                date.fromisoformat(d["last_interaction_date"])
                if d.get("last_interaction_date")
                else date.today()
            ),
            match_score=float(d.get("match_score", 50.0)),
            notes=d.get("notes", ""),
            id=d.get("id", uuid.uuid4().hex[:8]),
        )
