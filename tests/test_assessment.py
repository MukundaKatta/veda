"""Tests for veda.assessment — challenges, runner, leaderboard, streaks."""

from datetime import date, timedelta

from veda.assessment import (
    ChallengeRunner,
    CodeChallenge,
    Leaderboard,
    StreakTracker,
    TestCase,
)


def _make_challenge(cid="ch1"):
    return CodeChallenge(
        id=cid,
        prompt="Double the input number.",
        test_cases=[
            TestCase(input_data="2", expected_output="4"),
            TestCase(input_data="5", expected_output="10"),
            TestCase(input_data="0", expected_output="0", is_hidden=True),
        ],
        hints=["Multiply by 2", "Use int() to convert"],
        difficulty=2,
        points=100,
    )


# --- CodeChallenge ------------------------------------------------------

def test_challenge_visible_and_hidden_cases():
    ch = _make_challenge()
    assert len(ch.visible_test_cases) == 2
    assert len(ch.hidden_test_cases) == 1


def test_challenge_hints():
    ch = _make_challenge()
    assert ch.get_hint(0) == "Multiply by 2"
    assert ch.get_hint(5) is None


# --- ChallengeRunner ----------------------------------------------------

def test_runner_all_pass():
    runner = ChallengeRunner()
    runner.register_challenge(_make_challenge())

    def solution(inp):
        return str(int(inp) * 2)

    result = runner.run("ch1", "u1", solution)
    assert result.passed is True
    assert result.tests_passed == 3
    assert result.score == 100


def test_runner_partial_pass():
    runner = ChallengeRunner()
    runner.register_challenge(_make_challenge())

    def bad_solution(inp):
        return "4"  # only correct for input "2"

    result = runner.run("ch1", "u1", bad_solution)
    assert result.passed is False
    assert result.tests_passed == 1
    assert result.score < 100


def test_runner_exception_handling():
    runner = ChallengeRunner()
    runner.register_challenge(_make_challenge())

    def crashing(inp):
        raise ValueError("boom")

    result = runner.run("ch1", "u1", crashing)
    assert result.passed is False
    assert result.tests_passed == 0
    assert any("boom" in e for e in result.errors)


def test_runner_missing_challenge():
    runner = ChallengeRunner()
    result = runner.run("nope", "u1", lambda x: x)
    assert result.passed is False
    assert "not found" in result.errors[0]


def test_runner_best_score():
    runner = ChallengeRunner()
    runner.register_challenge(_make_challenge())
    runner.run("ch1", "u1", lambda x: "wrong")
    runner.run("ch1", "u1", lambda x: str(int(x) * 2))
    assert runner.best_score("u1", "ch1") == 100


def test_runner_list_and_filter():
    runner = ChallengeRunner()
    ch1 = _make_challenge("ch1")
    ch1.difficulty = 1
    ch2 = _make_challenge("ch2")
    ch2.difficulty = 5
    runner.register_challenge(ch1)
    runner.register_challenge(ch2)
    assert len(runner.list_challenges()) == 2
    assert len(runner.list_challenges(max_difficulty=3)) == 1


# --- Leaderboard --------------------------------------------------------

def test_leaderboard_ranking():
    lb = Leaderboard()
    lb.update("u1", "Alice", 300, 3)
    lb.update("u2", "Bob", 500, 5)
    lb.update("u3", "Carol", 100, 1)

    top = lb.top(2)
    assert len(top) == 2
    assert top[0].user_id == "u2"
    assert top[0].rank == 1
    assert top[1].rank == 2


def test_leaderboard_add_score():
    lb = Leaderboard()
    lb.add_score("u1", "Alice", 100)
    lb.add_score("u1", "Alice", 50)
    lb.increment_solved("u1")
    top = lb.top()
    assert top[0].score == 150
    assert top[0].challenges_solved == 1


def test_leaderboard_get_rank():
    lb = Leaderboard()
    lb.update("u1", "Alice", 200, 2)
    lb.update("u2", "Bob", 300, 3)
    assert lb.get_rank("u1") == 2
    assert lb.get_rank("u2") == 1
    assert lb.get_rank("u3") is None
    assert lb.size == 2


# --- StreakTracker ------------------------------------------------------

def test_streak_single_day():
    st = StreakTracker()
    today = date(2026, 1, 15)
    streak = st.record_activity("u1", today)
    assert streak == 1


def test_streak_consecutive_days():
    st = StreakTracker()
    base = date(2026, 3, 1)
    for i in range(5):
        st.record_activity("u1", base + timedelta(days=i))
    assert st.get_streak("u1") == 5


def test_streak_gap_resets():
    st = StreakTracker()
    base = date(2026, 3, 1)
    st.record_activity("u1", base)
    st.record_activity("u1", base + timedelta(days=1))
    # Skip a day
    streak = st.record_activity("u1", base + timedelta(days=3))
    assert streak == 1


def test_longest_streak():
    st = StreakTracker()
    base = date(2026, 3, 1)
    for i in range(5):
        st.record_activity("u1", base + timedelta(days=i))
    # Gap then shorter streak
    for i in range(3):
        st.record_activity("u1", base + timedelta(days=10 + i))
    assert st.get_longest_streak("u1") == 5


def test_active_users():
    st = StreakTracker()
    today = date(2026, 3, 25)
    st.record_activity("u1", today)
    st.record_activity("u2", today - timedelta(days=30))
    active = st.active_users(since=today - timedelta(days=7))
    assert "u1" in active
    assert "u2" not in active
