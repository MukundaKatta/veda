"""Tests for veda.curriculum — builder, prerequisites, skill map, default curriculum."""

from veda.core import Course, Difficulty, Module, Lesson
from veda.curriculum import (
    CurriculumBuilder,
    PrerequisiteChecker,
    SkillMap,
    build_default_curriculum,
)


def test_curriculum_builder_basic():
    course = (
        CurriculumBuilder()
        .course("c1", "Test", "A test course")
        .difficulty(Difficulty.INTERMEDIATE)
        .tags("python")
        .module("m1", "Module 1")
        .lesson("l1", "Lesson 1", "Content", 20)
        .lesson("l2", "Lesson 2", "Content", 15)
        .build()
    )
    assert course.id == "c1"
    assert course.difficulty == Difficulty.INTERMEDIATE
    assert course.module_count == 1
    assert course.lesson_count == 2
    assert "python" in course.tags


def test_curriculum_builder_multiple_modules():
    course = (
        CurriculumBuilder()
        .course("c1", "Test", "desc")
        .module("m1", "Mod1")
        .lesson("l1", "L1")
        .module("m2", "Mod2")
        .lesson("l2", "L2")
        .lesson("l3", "L3")
        .build()
    )
    assert course.module_count == 2
    assert course.lesson_count == 3


def test_prerequisite_checker_satisfied():
    checker = PrerequisiteChecker()
    c1 = Course(id="c1", title="C1", description="", prerequisites=[])
    c2 = Course(id="c2", title="C2", description="", prerequisites=["c1"])
    checker.register_course(c1)
    checker.register_course(c2)

    ok, missing = checker.check("c2", {"c1"})
    assert ok is True
    assert missing == []


def test_prerequisite_checker_missing():
    checker = PrerequisiteChecker()
    c2 = Course(id="c2", title="C2", description="", prerequisites=["c1"])
    checker.register_course(c2)
    ok, missing = checker.check("c2", set())
    assert ok is False
    assert missing == ["c1"]


def test_prerequisite_unlock_order():
    checker = PrerequisiteChecker()
    c1 = Course(id="c1", title="C1", description="", prerequisites=[])
    c2 = Course(id="c2", title="C2", description="", prerequisites=["c1"])
    c3 = Course(id="c3", title="C3", description="", prerequisites=["c2"])
    checker.register_course(c1)
    checker.register_course(c2)
    checker.register_course(c3)
    order = checker.get_unlock_order("c3")
    assert order == ["c1", "c2", "c3"]


def test_prerequisite_cycle_detection():
    checker = PrerequisiteChecker()
    c1 = Course(id="c1", title="C1", description="", prerequisites=["c2"])
    c2 = Course(id="c2", title="C2", description="", prerequisites=["c1"])
    checker.register_course(c1)
    checker.register_course(c2)
    cycles = checker.detect_cycles()
    assert len(cycles) >= 1


def test_skill_map():
    sm = SkillMap()
    sm.add_skill("python", "c1", Difficulty.BEGINNER)
    sm.add_skill("python", "c2", Difficulty.ADVANCED)
    sm.add_skill("javascript", "c3")

    assert sm.courses_for_skill("python") == ["c1", "c2"]
    assert sm.skills_for_course("c1") == ["python"]
    assert sm.skill_level("python") == Difficulty.ADVANCED
    assert "javascript" in sm.all_skills()
    assert sm.courses_for_skill("rust") == []
    assert sm.skill_level("rust") is None


def test_default_curriculum_has_five_tracks():
    courses = build_default_curriculum()
    assert len(courses) == 5
    ids = {c.id for c in courses}
    assert "python-101" in ids
    assert "web-101" in ids
    assert "ds-201" in ids
    assert "algo-301" in ids
    assert "sd-401" in ids
    # Check prerequisite chain
    ds = next(c for c in courses if c.id == "ds-201")
    assert "python-101" in ds.prerequisites
