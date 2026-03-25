"""Veda - Open-source learning platform with courses, modules, lessons,
code challenges, progress tracking, and leaderboards.

Named after the Vedas, the sacred texts of Hindu tradition representing
the oldest scriptures and the foundation of all knowledge."""

from veda.core import (
    LearningPlatform,
    Course,
    Module,
    Lesson,
    Exercise,
    UserProgress,
    Difficulty,
)
from veda.curriculum import CurriculumBuilder, PrerequisiteChecker, SkillMap
from veda.assessment import CodeChallenge, ChallengeRunner, Leaderboard, StreakTracker

__version__ = "0.1.0"
__all__ = [
    "LearningPlatform",
    "Course",
    "Module",
    "Lesson",
    "Exercise",
    "UserProgress",
    "Difficulty",
    "CurriculumBuilder",
    "PrerequisiteChecker",
    "SkillMap",
    "CodeChallenge",
    "ChallengeRunner",
    "Leaderboard",
    "StreakTracker",
]
