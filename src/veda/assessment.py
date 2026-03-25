"""Code challenges, challenge runner, leaderboard, and streak tracking.

Provides the assessment layer for the Veda learning platform including
runnable code challenges with test cases, a leaderboard sorted by score,
and a streak tracker that rewards daily engagement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class TestCase:
    """A single input/output test case for a code challenge."""

    input_data: str
    expected_output: str
    is_hidden: bool = False


@dataclass
class CodeChallenge:
    """A coding challenge with a prompt, test cases, hints, and difficulty."""

    id: str
    prompt: str
    test_cases: List[TestCase] = field(default_factory=list)
    hints: List[str] = field(default_factory=list)
    difficulty: int = 1  # 1-5 scale
    points: int = 100
    time_limit_seconds: int = 30

    @property
    def visible_test_cases(self) -> List[TestCase]:
        return [tc for tc in self.test_cases if not tc.is_hidden]

    @property
    def hidden_test_cases(self) -> List[TestCase]:
        return [tc for tc in self.test_cases if tc.is_hidden]

    def get_hint(self, index: int) -> Optional[str]:
        if 0 <= index < len(self.hints):
            return self.hints[index]
        return None


@dataclass
class SubmissionResult:
    """Result of running a user's submission against a challenge."""

    challenge_id: str
    user_id: str
    passed: bool
    tests_passed: int
    tests_total: int
    score: int
    errors: List[str] = field(default_factory=list)
    submitted_at: datetime = field(default_factory=datetime.utcnow)


class ChallengeRunner:
    """Evaluates user solutions against code challenges.

    Solutions are provided as callables that accept a string input and
    return a string output. This avoids exec/eval for safety.
    """

    def __init__(self) -> None:
        self._challenges: Dict[str, CodeChallenge] = {}
        self._submissions: List[SubmissionResult] = []

    def register_challenge(self, challenge: CodeChallenge) -> None:
        self._challenges[challenge.id] = challenge

    def get_challenge(self, challenge_id: str) -> Optional[CodeChallenge]:
        return self._challenges.get(challenge_id)

    def list_challenges(self, max_difficulty: Optional[int] = None) -> List[CodeChallenge]:
        challenges = list(self._challenges.values())
        if max_difficulty is not None:
            challenges = [c for c in challenges if c.difficulty <= max_difficulty]
        return sorted(challenges, key=lambda c: c.difficulty)

    def run(
        self,
        challenge_id: str,
        user_id: str,
        solution: Callable[[str], str],
    ) -> SubmissionResult:
        """Run a user's solution against all test cases for a challenge."""
        challenge = self._challenges.get(challenge_id)
        if challenge is None:
            return SubmissionResult(
                challenge_id=challenge_id,
                user_id=user_id,
                passed=False,
                tests_passed=0,
                tests_total=0,
                score=0,
                errors=["Challenge not found: {}".format(challenge_id)],
            )

        passed_count = 0
        errors: List[str] = []
        total = len(challenge.test_cases)

        for i, tc in enumerate(challenge.test_cases):
            try:
                output = solution(tc.input_data)
                if str(output).strip() == tc.expected_output.strip():
                    passed_count += 1
                else:
                    errors.append(
                        "Test {}: expected '{}', got '{}'".format(
                            i + 1, tc.expected_output.strip(), str(output).strip()
                        )
                    )
            except Exception as exc:
                errors.append("Test {}: raised {}".format(i + 1, exc))

        all_passed = passed_count == total and total > 0
        score = challenge.points if all_passed else int(challenge.points * passed_count / max(total, 1) * 0.5)

        result = SubmissionResult(
            challenge_id=challenge_id,
            user_id=user_id,
            passed=all_passed,
            tests_passed=passed_count,
            tests_total=total,
            score=score,
            errors=errors,
        )
        self._submissions.append(result)
        return result

    def user_submissions(self, user_id: str) -> List[SubmissionResult]:
        return [s for s in self._submissions if s.user_id == user_id]

    def best_score(self, user_id: str, challenge_id: str) -> int:
        relevant = [
            s for s in self._submissions
            if s.user_id == user_id and s.challenge_id == challenge_id
        ]
        return max((s.score for s in relevant), default=0)


@dataclass
class LeaderboardEntry:
    """A single entry on the leaderboard."""

    user_id: str
    display_name: str
    score: int
    challenges_solved: int
    rank: int = 0


class Leaderboard:
    """Maintains a ranked leaderboard of users by score."""

    def __init__(self) -> None:
        self._entries: Dict[str, LeaderboardEntry] = {}

    def update(self, user_id: str, display_name: str, score: int, solved: int) -> None:
        self._entries[user_id] = LeaderboardEntry(
            user_id=user_id,
            display_name=display_name,
            score=score,
            challenges_solved=solved,
        )

    def add_score(self, user_id: str, display_name: str, points: int) -> None:
        """Increment score for a user, creating an entry if needed."""
        entry = self._entries.get(user_id)
        if entry is None:
            entry = LeaderboardEntry(user_id=user_id, display_name=display_name, score=0, challenges_solved=0)
            self._entries[user_id] = entry
        entry.score += points

    def increment_solved(self, user_id: str) -> None:
        entry = self._entries.get(user_id)
        if entry:
            entry.challenges_solved += 1

    def top(self, n: int = 10) -> List[LeaderboardEntry]:
        ranked = sorted(self._entries.values(), key=lambda e: e.score, reverse=True)
        for i, entry in enumerate(ranked):
            entry.rank = i + 1
        return ranked[:n]

    def get_rank(self, user_id: str) -> Optional[int]:
        ranked = self.top(len(self._entries))
        for entry in ranked:
            if entry.user_id == user_id:
                return entry.rank
        return None

    @property
    def size(self) -> int:
        return len(self._entries)


class StreakTracker:
    """Tracks daily engagement streaks for users.

    A streak is maintained when a user completes at least one activity
    every calendar day. Missing a day resets the streak to zero.
    """

    def __init__(self) -> None:
        self._activity: Dict[str, List[date]] = {}
        self._streaks: Dict[str, int] = {}

    def record_activity(self, user_id: str, activity_date: Optional[date] = None) -> int:
        """Record activity for a date and return the current streak."""
        today = activity_date or date.today()
        if user_id not in self._activity:
            self._activity[user_id] = []
            self._streaks[user_id] = 0

        dates = self._activity[user_id]
        if today not in dates:
            dates.append(today)
            dates.sort()

        self._streaks[user_id] = self._calculate_streak(dates, today)
        return self._streaks[user_id]

    def get_streak(self, user_id: str) -> int:
        return self._streaks.get(user_id, 0)

    def get_longest_streak(self, user_id: str) -> int:
        """Calculate the longest streak ever for a user."""
        dates = self._activity.get(user_id, [])
        if not dates:
            return 0
        sorted_dates = sorted(set(dates))
        longest = 1
        current = 1
        for i in range(1, len(sorted_dates)):
            if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
                current += 1
                longest = max(longest, current)
            else:
                current = 1
        return longest

    def _calculate_streak(self, dates: List[date], reference: date) -> int:
        """Count consecutive days ending on *reference*."""
        unique = sorted(set(dates), reverse=True)
        if not unique or unique[0] != reference:
            return 0
        streak = 1
        for i in range(1, len(unique)):
            if (unique[i - 1] - unique[i]).days == 1:
                streak += 1
            else:
                break
        return streak

    def active_users(self, since: Optional[date] = None) -> List[str]:
        """Return user IDs active on or after *since*."""
        cutoff = since or date.today()
        return [
            uid
            for uid, dates in self._activity.items()
            if any(d >= cutoff for d in dates)
        ]
