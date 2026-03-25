"""Core domain models for the Veda learning platform.

Provides Course, Module, Lesson, Exercise, UserProgress, and the central
LearningPlatform orchestrator.  All progress is tracked per-user with
completion percentages, time spent, and earned scores.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class Difficulty(Enum):
    """Difficulty levels for courses and exercises."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

    def numeric(self) -> int:
        """Return a numeric value for comparison."""
        return {
            Difficulty.BEGINNER: 1,
            Difficulty.INTERMEDIATE: 2,
            Difficulty.ADVANCED: 3,
            Difficulty.EXPERT: 4,
        }[self]

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Difficulty):
            return NotImplemented
        return self.numeric() < other.numeric()

    def __le__(self, other: object) -> bool:
        if not isinstance(other, Difficulty):
            return NotImplemented
        return self.numeric() <= other.numeric()


@dataclass
class Exercise:
    """A practice exercise within a lesson."""

    id: str
    prompt: str
    expected_output: str
    hints: List[str] = field(default_factory=list)
    points: int = 10

    def check_answer(self, answer: str) -> bool:
        """Check whether the given answer matches the expected output."""
        return answer.strip() == self.expected_output.strip()


@dataclass
class Lesson:
    """A single lesson containing content and optional exercises."""

    id: str
    title: str
    content: str
    exercises: List[Exercise] = field(default_factory=list)
    duration_minutes: int = 15

    @property
    def exercise_count(self) -> int:
        return len(self.exercises)

    @property
    def total_points(self) -> int:
        return sum(ex.points for ex in self.exercises)


@dataclass
class Module:
    """A module groups related lessons within a course."""

    id: str
    title: str
    lessons: List[Lesson] = field(default_factory=list)

    @property
    def lesson_count(self) -> int:
        return len(self.lessons)

    @property
    def total_duration(self) -> int:
        """Total duration across all lessons in minutes."""
        return sum(lesson.duration_minutes for lesson in self.lessons)

    @property
    def total_points(self) -> int:
        return sum(lesson.total_points for lesson in self.lessons)

    def get_lesson(self, lesson_id: str) -> Optional[Lesson]:
        for lesson in self.lessons:
            if lesson.id == lesson_id:
                return lesson
        return None


@dataclass
class Course:
    """A course contains modules and has metadata about difficulty and prerequisites."""

    id: str
    title: str
    description: str
    modules: List[Module] = field(default_factory=list)
    difficulty: Difficulty = Difficulty.BEGINNER
    prerequisites: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    @property
    def module_count(self) -> int:
        return len(self.modules)

    @property
    def lesson_count(self) -> int:
        return sum(m.lesson_count for m in self.modules)

    @property
    def total_duration(self) -> int:
        """Total estimated duration in minutes."""
        return sum(m.total_duration for m in self.modules)

    @property
    def total_points(self) -> int:
        return sum(m.total_points for m in self.modules)

    def get_module(self, module_id: str) -> Optional[Module]:
        for module in self.modules:
            if module.id == module_id:
                return module
        return None

    def get_lesson(self, lesson_id: str) -> Optional[Lesson]:
        for module in self.modules:
            lesson = module.get_lesson(lesson_id)
            if lesson is not None:
                return lesson
        return None


@dataclass
class LessonProgress:
    """Tracks a user's progress through a single lesson."""

    lesson_id: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    exercises_completed: Set[str] = field(default_factory=set)
    score: int = 0

    @property
    def is_complete(self) -> bool:
        return self.completed_at is not None

    @property
    def time_spent(self) -> timedelta:
        if self.started_at is None:
            return timedelta()
        end = self.completed_at or datetime.utcnow()
        return end - self.started_at


@dataclass
class UserProgress:
    """Tracks a user's progress across the entire platform."""

    user_id: str
    display_name: str
    enrolled_courses: Set[str] = field(default_factory=set)
    lesson_progress: Dict[str, LessonProgress] = field(default_factory=dict)
    completed_courses: Set[str] = field(default_factory=set)
    total_score: int = 0
    badges: List[str] = field(default_factory=list)

    def enroll(self, course_id: str) -> None:
        """Enroll in a course."""
        self.enrolled_courses.add(course_id)

    def start_lesson(self, lesson_id: str) -> LessonProgress:
        """Start tracking a lesson."""
        if lesson_id not in self.lesson_progress:
            self.lesson_progress[lesson_id] = LessonProgress(
                lesson_id=lesson_id, started_at=datetime.utcnow()
            )
        return self.lesson_progress[lesson_id]

    def complete_exercise(self, lesson_id: str, exercise_id: str, points: int) -> None:
        """Mark an exercise as completed and award points."""
        progress = self.start_lesson(lesson_id)
        if exercise_id not in progress.exercises_completed:
            progress.exercises_completed.add(exercise_id)
            progress.score += points
            self.total_score += points

    def complete_lesson(self, lesson_id: str) -> None:
        """Mark a lesson as completed."""
        progress = self.start_lesson(lesson_id)
        progress.completed_at = datetime.utcnow()

    def get_course_completion(self, course: Course) -> float:
        """Return the completion percentage (0.0-1.0) for a course."""
        if course.lesson_count == 0:
            return 0.0
        completed = sum(
            1
            for module in course.modules
            for lesson in module.lessons
            if lesson.id in self.lesson_progress
            and self.lesson_progress[lesson.id].is_complete
        )
        return completed / course.lesson_count

    def mark_course_complete(self, course_id: str) -> None:
        """Mark a course as fully completed."""
        self.completed_courses.add(course_id)

    def award_badge(self, badge: str) -> None:
        """Award a badge if not already earned."""
        if badge not in self.badges:
            self.badges.append(badge)


class LearningPlatform:
    """Central orchestrator for the Veda learning platform.

    Manages courses, user registrations, enrolments, and progress tracking.
    """

    def __init__(self, name: str = "Veda") -> None:
        self.name = name
        self._courses: Dict[str, Course] = {}
        self._users: Dict[str, UserProgress] = {}

    # -- Course management ---------------------------------------------------

    def add_course(self, course: Course) -> None:
        """Register a course on the platform."""
        self._courses[course.id] = course

    def remove_course(self, course_id: str) -> bool:
        """Remove a course. Returns True if it existed."""
        return self._courses.pop(course_id, None) is not None

    def get_course(self, course_id: str) -> Optional[Course]:
        return self._courses.get(course_id)

    def list_courses(
        self,
        difficulty: Optional[Difficulty] = None,
        tag: Optional[str] = None,
    ) -> List[Course]:
        """Return courses optionally filtered by difficulty or tag."""
        result = list(self._courses.values())
        if difficulty is not None:
            result = [c for c in result if c.difficulty == difficulty]
        if tag is not None:
            result = [c for c in result if tag in c.tags]
        return result

    def search_courses(self, query: str) -> List[Course]:
        """Simple keyword search across title and description."""
        query_lower = query.lower()
        return [
            c
            for c in self._courses.values()
            if query_lower in c.title.lower() or query_lower in c.description.lower()
        ]

    # -- User management -----------------------------------------------------

    def register_user(self, user_id: str, display_name: str) -> UserProgress:
        """Register a new user and return their progress tracker."""
        if user_id in self._users:
            return self._users[user_id]
        progress = UserProgress(user_id=user_id, display_name=display_name)
        self._users[user_id] = progress
        return progress

    def get_user(self, user_id: str) -> Optional[UserProgress]:
        return self._users.get(user_id)

    def list_users(self) -> List[UserProgress]:
        return list(self._users.values())

    # -- Enrolment and progress ----------------------------------------------

    def enroll_user(self, user_id: str, course_id: str) -> bool:
        """Enrol a user in a course. Returns False if user/course missing."""
        user = self._users.get(user_id)
        course = self._courses.get(course_id)
        if user is None or course is None:
            return False
        # Check prerequisites
        for prereq_id in course.prerequisites:
            if prereq_id not in user.completed_courses:
                return False
        user.enroll(course_id)
        return True

    def submit_exercise(
        self, user_id: str, lesson_id: str, exercise_id: str, answer: str
    ) -> Tuple[bool, int]:
        """Submit an exercise answer. Returns (correct, points_awarded)."""
        user = self._users.get(user_id)
        if user is None:
            return False, 0
        # Find the exercise across all courses
        for course in self._courses.values():
            lesson = course.get_lesson(lesson_id)
            if lesson is not None:
                for ex in lesson.exercises:
                    if ex.id == exercise_id:
                        if ex.check_answer(answer):
                            user.complete_exercise(lesson_id, exercise_id, ex.points)
                            return True, ex.points
                        return False, 0
        return False, 0

    def complete_lesson(self, user_id: str, lesson_id: str) -> bool:
        """Mark a lesson complete for a user."""
        user = self._users.get(user_id)
        if user is None:
            return False
        user.complete_lesson(lesson_id)
        # Check if any course is now fully complete
        for course_id in user.enrolled_courses:
            course = self._courses.get(course_id)
            if course and user.get_course_completion(course) >= 1.0:
                user.mark_course_complete(course_id)
                user.award_badge("course_complete_{}".format(course_id))
        return True

    def get_leaderboard(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """Return top N users by total score."""
        sorted_users = sorted(
            self._users.values(), key=lambda u: u.total_score, reverse=True
        )
        return [
            {
                "user_id": u.user_id,
                "display_name": u.display_name,
                "score": u.total_score,
                "courses_completed": len(u.completed_courses),
                "badges": list(u.badges),
            }
            for u in sorted_users[:top_n]
        ]

    @property
    def course_count(self) -> int:
        return len(self._courses)

    @property
    def user_count(self) -> int:
        return len(self._users)

    def platform_stats(self) -> Dict[str, Any]:
        """Return aggregate platform statistics."""
        total_lessons = sum(c.lesson_count for c in self._courses.values())
        total_duration = sum(c.total_duration for c in self._courses.values())
        return {
            "platform": self.name,
            "courses": self.course_count,
            "users": self.user_count,
            "total_lessons": total_lessons,
            "total_duration_hours": round(total_duration / 60, 1),
        }
