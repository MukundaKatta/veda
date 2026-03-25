"""Curriculum building, prerequisite validation, and skill mapping.

Provides tools for constructing learning paths, verifying that prerequisites
are satisfied, and mapping skills across the platform's course catalogue.
Includes a built-in 5-track starter curriculum.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from veda.core import Course, Difficulty, Exercise, Lesson, Module


class PrerequisiteChecker:
    """Validates that a user has completed all prerequisites for a course."""

    def __init__(self) -> None:
        self._courses: Dict[str, Course] = {}

    def register_course(self, course: Course) -> None:
        self._courses[course.id] = course

    def check(self, course_id: str, completed_course_ids: Set[str]) -> Tuple[bool, List[str]]:
        """Return (satisfied, missing_ids) for the given course."""
        course = self._courses.get(course_id)
        if course is None:
            return False, []
        missing = [pid for pid in course.prerequisites if pid not in completed_course_ids]
        return len(missing) == 0, missing

    def get_unlock_order(self, course_id: str) -> List[str]:
        """Return a topological ordering of prerequisites leading to *course_id*."""
        visited: Set[str] = set()
        order: List[str] = []

        def _visit(cid: str) -> None:
            if cid in visited:
                return
            visited.add(cid)
            course = self._courses.get(cid)
            if course:
                for prereq in course.prerequisites:
                    _visit(prereq)
            order.append(cid)

        _visit(course_id)
        return order

    def detect_cycles(self) -> List[List[str]]:
        """Detect circular prerequisite chains. Returns list of cycles."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {cid: WHITE for cid in self._courses}
        cycles: List[List[str]] = []
        path: List[str] = []

        def _dfs(cid: str) -> None:
            color[cid] = GRAY
            path.append(cid)
            course = self._courses.get(cid)
            if course:
                for prereq in course.prerequisites:
                    if prereq in color:
                        if color[prereq] == GRAY:
                            idx = path.index(prereq)
                            cycles.append(list(path[idx:]))
                        elif color[prereq] == WHITE:
                            _dfs(prereq)
            path.pop()
            color[cid] = BLACK

        for cid in self._courses:
            if color[cid] == WHITE:
                _dfs(cid)
        return cycles


@dataclass
class SkillNode:
    """A node in the skill map linking a skill to courses that teach it."""

    skill: str
    course_ids: List[str] = field(default_factory=list)
    level: Difficulty = Difficulty.BEGINNER


class SkillMap:
    """Maps skills to courses, enabling discovery by competency."""

    def __init__(self) -> None:
        self._skills: Dict[str, SkillNode] = {}

    def add_skill(self, skill: str, course_id: str, level: Difficulty = Difficulty.BEGINNER) -> None:
        if skill not in self._skills:
            self._skills[skill] = SkillNode(skill=skill, level=level)
        node = self._skills[skill]
        if course_id not in node.course_ids:
            node.course_ids.append(course_id)
        # Keep the highest level seen
        if level.numeric() > node.level.numeric():
            node.level = level

    def courses_for_skill(self, skill: str) -> List[str]:
        node = self._skills.get(skill)
        return list(node.course_ids) if node else []

    def skills_for_course(self, course_id: str) -> List[str]:
        return [
            skill
            for skill, node in self._skills.items()
            if course_id in node.course_ids
        ]

    def all_skills(self) -> List[str]:
        return sorted(self._skills.keys())

    def skill_level(self, skill: str) -> Optional[Difficulty]:
        node = self._skills.get(skill)
        return node.level if node else None


class CurriculumBuilder:
    """Fluent builder for constructing courses with modules and lessons."""

    def __init__(self) -> None:
        self._id: str = ""
        self._title: str = ""
        self._description: str = ""
        self._difficulty: Difficulty = Difficulty.BEGINNER
        self._prerequisites: List[str] = []
        self._tags: List[str] = []
        self._modules: List[Module] = []
        self._current_module_lessons: List[Lesson] = []
        self._current_module_title: str = ""
        self._current_module_id: str = ""

    def course(self, course_id: str, title: str, description: str) -> "CurriculumBuilder":
        self._id = course_id
        self._title = title
        self._description = description
        return self

    def difficulty(self, diff: Difficulty) -> "CurriculumBuilder":
        self._difficulty = diff
        return self

    def prerequisites(self, *prereq_ids: str) -> "CurriculumBuilder":
        self._prerequisites = list(prereq_ids)
        return self

    def tags(self, *tag_list: str) -> "CurriculumBuilder":
        self._tags = list(tag_list)
        return self

    def module(self, module_id: str, title: str) -> "CurriculumBuilder":
        self._flush_module()
        self._current_module_id = module_id
        self._current_module_title = title
        self._current_module_lessons = []
        return self

    def lesson(
        self,
        lesson_id: str,
        title: str,
        content: str = "",
        duration: int = 15,
        exercises: Optional[List[Exercise]] = None,
    ) -> "CurriculumBuilder":
        self._current_module_lessons.append(
            Lesson(
                id=lesson_id,
                title=title,
                content=content,
                exercises=exercises or [],
                duration_minutes=duration,
            )
        )
        return self

    def build(self) -> Course:
        self._flush_module()
        return Course(
            id=self._id,
            title=self._title,
            description=self._description,
            modules=list(self._modules),
            difficulty=self._difficulty,
            prerequisites=list(self._prerequisites),
            tags=list(self._tags),
        )

    def _flush_module(self) -> None:
        if self._current_module_id:
            self._modules.append(
                Module(
                    id=self._current_module_id,
                    title=self._current_module_title,
                    lessons=list(self._current_module_lessons),
                )
            )
            self._current_module_id = ""
            self._current_module_lessons = []


def build_default_curriculum() -> List[Course]:
    """Return the built-in 5-track starter curriculum.

    Tracks:
      1. Python Fundamentals (beginner)
      2. Web Development Basics (beginner)
      3. Data Structures (intermediate, requires Python Fundamentals)
      4. Algorithms (advanced, requires Data Structures)
      5. System Design (expert, requires Algorithms)
    """
    python_fund = (
        CurriculumBuilder()
        .course("python-101", "Python Fundamentals", "Learn Python from scratch.")
        .difficulty(Difficulty.BEGINNER)
        .tags("python", "programming", "beginner")
        .module("py-basics", "Python Basics")
        .lesson("py-vars", "Variables and Types", "Learn about Python variables.", 20)
        .lesson("py-control", "Control Flow", "If statements and loops.", 25)
        .module("py-functions", "Functions")
        .lesson("py-func-intro", "Defining Functions", "Create reusable code.", 20)
        .lesson("py-func-adv", "Advanced Functions", "Closures and decorators.", 30)
        .build()
    )

    web_dev = (
        CurriculumBuilder()
        .course("web-101", "Web Development Basics", "HTML, CSS, and JavaScript.")
        .difficulty(Difficulty.BEGINNER)
        .tags("web", "html", "css", "javascript")
        .module("web-html", "HTML Essentials")
        .lesson("html-intro", "Introduction to HTML", "Structure of a web page.", 20)
        .lesson("html-forms", "HTML Forms", "Collecting user input.", 25)
        .module("web-css", "CSS Fundamentals")
        .lesson("css-intro", "CSS Basics", "Styling your pages.", 20)
        .build()
    )

    data_structures = (
        CurriculumBuilder()
        .course("ds-201", "Data Structures", "Essential data structures.")
        .difficulty(Difficulty.INTERMEDIATE)
        .prerequisites("python-101")
        .tags("python", "data-structures", "computer-science")
        .module("ds-linear", "Linear Structures")
        .lesson("ds-arrays", "Arrays and Lists", "Sequential data storage.", 25)
        .lesson("ds-stacks", "Stacks and Queues", "LIFO and FIFO structures.", 25)
        .module("ds-trees", "Tree Structures")
        .lesson("ds-bst", "Binary Search Trees", "Ordered tree structures.", 30)
        .build()
    )

    algorithms = (
        CurriculumBuilder()
        .course("algo-301", "Algorithms", "Algorithm design and analysis.")
        .difficulty(Difficulty.ADVANCED)
        .prerequisites("ds-201")
        .tags("algorithms", "computer-science")
        .module("algo-sort", "Sorting Algorithms")
        .lesson("algo-merge", "Merge Sort", "Divide and conquer sorting.", 30)
        .lesson("algo-quick", "Quick Sort", "Partition-based sorting.", 30)
        .module("algo-graph", "Graph Algorithms")
        .lesson("algo-bfs", "Breadth-First Search", "Level-by-level traversal.", 35)
        .build()
    )

    system_design = (
        CurriculumBuilder()
        .course("sd-401", "System Design", "Designing large-scale systems.")
        .difficulty(Difficulty.EXPERT)
        .prerequisites("algo-301")
        .tags("system-design", "architecture")
        .module("sd-basics", "Fundamentals")
        .lesson("sd-scale", "Scalability", "Horizontal vs vertical scaling.", 40)
        .lesson("sd-cache", "Caching Strategies", "Speed up your systems.", 35)
        .build()
    )

    return [python_fund, web_dev, data_structures, algorithms, system_design]
