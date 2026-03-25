"""Tests for veda.core — platform, courses, modules, lessons, progress."""

from veda.core import (
    Course,
    Difficulty,
    Exercise,
    LearningPlatform,
    Lesson,
    Module,
    UserProgress,
)


def _make_exercise(eid="ex1", expected="42"):
    return Exercise(id=eid, prompt="What is the answer?", expected_output=expected)


def _make_lesson(lid="l1", title="Intro", exercises=None):
    return Lesson(
        id=lid,
        title=title,
        content="Some content",
        exercises=exercises or [],
        duration_minutes=20,
    )


def _make_module(mid="m1", title="Mod1", lessons=None):
    return Module(id=mid, title=title, lessons=lessons or [])


def _make_course(cid="c1", modules=None, prereqs=None):
    return Course(
        id=cid,
        title="Test Course",
        description="A test course",
        modules=modules or [],
        difficulty=Difficulty.BEGINNER,
        prerequisites=prereqs or [],
        tags=["test"],
    )


# --- Difficulty ---------------------------------------------------------

def test_difficulty_ordering():
    assert Difficulty.BEGINNER < Difficulty.INTERMEDIATE
    assert Difficulty.ADVANCED <= Difficulty.EXPERT
    assert not (Difficulty.EXPERT < Difficulty.BEGINNER)


def test_difficulty_numeric():
    assert Difficulty.BEGINNER.numeric() == 1
    assert Difficulty.EXPERT.numeric() == 4


# --- Exercise -----------------------------------------------------------

def test_exercise_check_correct():
    ex = _make_exercise(expected="hello")
    assert ex.check_answer("hello") is True


def test_exercise_check_incorrect():
    ex = _make_exercise(expected="hello")
    assert ex.check_answer("world") is False


def test_exercise_check_strips_whitespace():
    ex = _make_exercise(expected="hello")
    assert ex.check_answer("  hello  ") is True


# --- Lesson -------------------------------------------------------------

def test_lesson_properties():
    ex = _make_exercise()
    lesson = _make_lesson(exercises=[ex])
    assert lesson.exercise_count == 1
    assert lesson.total_points == 10


# --- Module -------------------------------------------------------------

def test_module_duration_and_points():
    ex = _make_exercise()
    ex.points = 20
    lesson = _make_lesson(exercises=[ex])
    mod = _make_module(lessons=[lesson])
    assert mod.total_duration == 20
    assert mod.total_points == 20
    assert mod.get_lesson("l1") is lesson
    assert mod.get_lesson("nope") is None


# --- Course -------------------------------------------------------------

def test_course_counts():
    lesson = _make_lesson()
    mod = _make_module(lessons=[lesson])
    course = _make_course(modules=[mod])
    assert course.module_count == 1
    assert course.lesson_count == 1
    assert course.total_duration == 20
    assert course.get_module("m1") is mod
    assert course.get_lesson("l1") is lesson


# --- UserProgress -------------------------------------------------------

def test_user_enroll_and_complete():
    user = UserProgress(user_id="u1", display_name="Arjuna")
    user.enroll("c1")
    assert "c1" in user.enrolled_courses
    user.mark_course_complete("c1")
    assert "c1" in user.completed_courses


def test_user_exercise_scoring():
    user = UserProgress(user_id="u1", display_name="Arjuna")
    user.complete_exercise("l1", "ex1", 10)
    assert user.total_score == 10
    # Completing same exercise again should not double-count
    user.complete_exercise("l1", "ex1", 10)
    assert user.total_score == 10


def test_user_course_completion_percentage():
    lesson1 = _make_lesson(lid="l1")
    lesson2 = _make_lesson(lid="l2")
    mod = _make_module(lessons=[lesson1, lesson2])
    course = _make_course(modules=[mod])

    user = UserProgress(user_id="u1", display_name="Arjuna")
    assert user.get_course_completion(course) == 0.0
    user.complete_lesson("l1")
    assert user.get_course_completion(course) == 0.5
    user.complete_lesson("l2")
    assert user.get_course_completion(course) == 1.0


def test_user_badges():
    user = UserProgress(user_id="u1", display_name="Arjuna")
    user.award_badge("first_login")
    user.award_badge("first_login")  # duplicate
    assert user.badges == ["first_login"]


# --- LearningPlatform --------------------------------------------------

def test_platform_add_and_list_courses():
    platform = LearningPlatform()
    course = _make_course()
    platform.add_course(course)
    assert platform.course_count == 1
    assert platform.list_courses() == [course]
    assert platform.list_courses(difficulty=Difficulty.BEGINNER) == [course]
    assert platform.list_courses(difficulty=Difficulty.EXPERT) == []
    assert platform.list_courses(tag="test") == [course]
    assert platform.list_courses(tag="nope") == []


def test_platform_remove_course():
    platform = LearningPlatform()
    platform.add_course(_make_course())
    assert platform.remove_course("c1") is True
    assert platform.remove_course("c1") is False
    assert platform.course_count == 0


def test_platform_search():
    platform = LearningPlatform()
    platform.add_course(_make_course())
    assert len(platform.search_courses("Test")) == 1
    assert len(platform.search_courses("zzz")) == 0


def test_platform_register_user():
    platform = LearningPlatform()
    user = platform.register_user("u1", "Arjuna")
    assert user.user_id == "u1"
    # Re-register returns same object
    same = platform.register_user("u1", "Arjuna")
    assert same is user
    assert platform.user_count == 1


def test_platform_enroll_with_prerequisites():
    platform = LearningPlatform()
    c1 = _make_course(cid="c1")
    c2 = _make_course(cid="c2", prereqs=["c1"])
    platform.add_course(c1)
    platform.add_course(c2)
    user = platform.register_user("u1", "Arjuna")
    # Cannot enroll in c2 without completing c1
    assert platform.enroll_user("u1", "c2") is False
    # Enroll and complete c1
    platform.enroll_user("u1", "c1")
    user.mark_course_complete("c1")
    assert platform.enroll_user("u1", "c2") is True


def test_platform_submit_exercise():
    ex = _make_exercise(expected="42")
    lesson = _make_lesson(exercises=[ex])
    mod = _make_module(lessons=[lesson])
    course = _make_course(modules=[mod])

    platform = LearningPlatform()
    platform.add_course(course)
    platform.register_user("u1", "Arjuna")

    correct, points = platform.submit_exercise("u1", "l1", "ex1", "42")
    assert correct is True
    assert points == 10

    wrong, pts = platform.submit_exercise("u1", "l1", "ex1", "0")
    assert wrong is False
    assert pts == 0


def test_platform_complete_lesson_awards_badge():
    lesson = _make_lesson(lid="l1")
    mod = _make_module(lessons=[lesson])
    course = _make_course(modules=[mod])

    platform = LearningPlatform()
    platform.add_course(course)
    user = platform.register_user("u1", "Arjuna")
    platform.enroll_user("u1", "c1")
    platform.complete_lesson("u1", "l1")
    assert "c1" in user.completed_courses
    assert "course_complete_c1" in user.badges


def test_platform_leaderboard():
    platform = LearningPlatform()
    for i in range(5):
        u = platform.register_user("u{}".format(i), "User{}".format(i))
        u.total_score = (i + 1) * 100
    board = platform.get_leaderboard(top_n=3)
    assert len(board) == 3
    assert board[0]["score"] == 500


def test_platform_stats():
    platform = LearningPlatform()
    lesson = _make_lesson()
    mod = _make_module(lessons=[lesson])
    course = _make_course(modules=[mod])
    platform.add_course(course)
    stats = platform.platform_stats()
    assert stats["courses"] == 1
    assert stats["total_lessons"] == 1
