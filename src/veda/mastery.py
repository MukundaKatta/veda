"""Mastery tracking and next-lesson recommendation.

``curriculum.py`` defines what can be learned. ``assessment.py`` grades
individual attempts. This module sits above both and maintains a
per-learner *mastery* score for every skill, then recommends what to
study next based on prerequisites and the zone-of-proximal-development
heuristic ("hardest skill the learner is still likely to succeed at").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class Skill:
    id: str
    title: str
    difficulty: float  # 0..1, rough a-priori difficulty
    prerequisites: tuple[str, ...] = ()


@dataclass
class LearnerState:
    """Tracks mastery and decay for a single learner."""

    mastery: dict[str, float] = field(default_factory=dict)
    attempts: dict[str, int] = field(default_factory=dict)
    last_touched_day: dict[str, int] = field(default_factory=dict)
    current_day: int = 0

    def record_attempt(self, skill_id: str, grade: float, *, weight: float = 0.3) -> float:
        """Update mastery via EMA over `grade` in [0,1]. Returns new mastery."""
        if not 0.0 <= grade <= 1.0:
            raise ValueError("grade must be in [0,1]")
        cur = self.mastery.get(skill_id, 0.0)
        new = (1 - weight) * cur + weight * grade
        self.mastery[skill_id] = new
        self.attempts[skill_id] = self.attempts.get(skill_id, 0) + 1
        self.last_touched_day[skill_id] = self.current_day
        return new

    def effective_mastery(self, skill_id: str, *, half_life_days: int = 14) -> float:
        """Mastery with exponential decay from last touch."""
        base = self.mastery.get(skill_id, 0.0)
        last = self.last_touched_day.get(skill_id, self.current_day)
        days = max(0, self.current_day - last)
        if half_life_days <= 0:
            return base
        return base * (0.5 ** (days / half_life_days))


def prerequisites_satisfied(skill: Skill, state: LearnerState, *, threshold: float = 0.7) -> bool:
    return all(state.effective_mastery(p) >= threshold for p in skill.prerequisites)


def recommend_next(
    curriculum: Iterable[Skill],
    state: LearnerState,
    *,
    challenge_sweet_spot: float = 0.55,
) -> list[Skill]:
    """Rank unlocked skills by how close they sit to the ZPD sweet spot.

    Skills the learner has already mastered (mastery >= 0.9) drop out.
    Among the rest, we prefer ones whose *effective difficulty given
    current mastery* lands near `challenge_sweet_spot` — ~55% expected
    success rate is the usual ZPD target.
    """
    scored: list[tuple[Skill, float]] = []
    for s in curriculum:
        m = state.effective_mastery(s.id)
        if m >= 0.9:
            continue
        if not prerequisites_satisfied(s, state):
            continue
        expected = max(0.0, 1.0 - s.difficulty * (1.0 - m))
        zpd_fit = 1.0 - abs(expected - challenge_sweet_spot)
        # Break ties toward skills that haven't been attempted recently.
        freshness = 1.0 / (1.0 + state.attempts.get(s.id, 0))
        scored.append((s, zpd_fit * 0.8 + freshness * 0.2))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [s for s, _ in scored]


def overdue_reviews(
    curriculum: Iterable[Skill],
    state: LearnerState,
    *,
    review_threshold: float = 0.6,
    half_life_days: int = 14,
) -> list[Skill]:
    """Skills whose decayed mastery has fallen below the review threshold."""
    out: list[Skill] = []
    for s in curriculum:
        if s.id not in state.mastery:
            continue
        if state.effective_mastery(s.id, half_life_days=half_life_days) < review_threshold:
            out.append(s)
    return out
