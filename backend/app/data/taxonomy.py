"""The SAT topic taxonomy.

Structure mirrors the **digital SAT** (2024+): two sections, four domains each,
broken into the specific skills a tutor would actually diagnose and assign
practice on. Skill names follow College Board's published domain/skill outline;
where College Board lists a single broad skill (e.g. "Boundaries"), it is split
into the finer categories tutors teach to (sentence boundaries vs. internal
punctuation), which is what makes a per-skill study plan useful.

``frequency_weight`` is the skill's approximate share *of its section*; the
weights in each section sum to 1.0. They come from College Board's published
test-spec domain weightings plus my own experience with the question mix across
released practice tests -- approximate and tutor-informed, NOT scraped or copied
from any proprietary source. Approximate domain shares used:

    Math      Algebra 35% | Advanced Math 35% | Problem-Solving & Data 15% | Geometry & Trig 15%
    R & W     Information & Ideas 26% | Craft & Structure 28% | Expression 20% | Conventions 26%

NOTE: no real question text, answer choices, or passages appear anywhere in this
project. Only skill tags and their relative frequencies are stored.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.enums import Section


@dataclass(frozen=True)
class TopicSpec:
    section: Section
    domain: str
    skill_name: str
    frequency_weight: float


# (section, domain) -> [(skill_name, frequency_weight), ...]
_DOMAINS: list[tuple[Section, str, list[tuple[str, float]]]] = [
    (
        Section.MATH,
        "Algebra",
        [
            ("Linear equations in one variable", 0.07),
            ("Linear equations in two variables", 0.07),
            ("Linear functions", 0.08),
            ("Systems of two linear equations in two variables", 0.07),
            ("Linear inequalities in one or two variables", 0.06),
        ],
    ),
    (
        Section.MATH,
        "Advanced Math",
        [
            ("Equivalent expressions", 0.07),
            ("Nonlinear equations in one variable", 0.07),
            ("Systems of nonlinear equations", 0.06),
            ("Nonlinear functions", 0.08),
            ("Quadratic and exponential models", 0.07),
        ],
    ),
    (
        Section.MATH,
        "Problem-Solving and Data Analysis",
        [
            ("Ratios, rates, and proportional relationships", 0.03),
            ("Percentages", 0.025),
            ("One-variable data: center and spread", 0.025),
            ("Two-variable data: models and scatterplots", 0.025),
            ("Probability and conditional probability", 0.02),
            ("Inference from sample statistics and margin of error", 0.025),
        ],
    ),
    (
        Section.MATH,
        "Geometry and Trigonometry",
        [
            ("Area and volume", 0.04),
            ("Lines, angles, and triangles", 0.04),
            ("Right triangles and trigonometry", 0.04),
            ("Circles", 0.03),
        ],
    ),
    (
        Section.READING_WRITING,
        "Information and Ideas",
        [
            ("Central ideas and details", 0.07),
            ("Command of evidence: textual", 0.07),
            ("Command of evidence: quantitative", 0.06),
            ("Inferences", 0.06),
        ],
    ),
    (
        Section.READING_WRITING,
        "Craft and Structure",
        [
            ("Words in context", 0.12),
            ("Text structure and purpose", 0.09),
            ("Cross-text connections", 0.07),
        ],
    ),
    (
        Section.READING_WRITING,
        "Expression of Ideas",
        [
            ("Rhetorical synthesis", 0.09),
            ("Transitions", 0.07),
            ("Precision and concision", 0.04),
        ],
    ),
    (
        Section.READING_WRITING,
        "Standard English Conventions",
        [
            ("Sentence boundaries and punctuation", 0.08),
            ("Subject-verb and pronoun agreement", 0.06),
            ("Verb tense and form", 0.05),
            ("Modifiers and parallel structure", 0.04),
            ("Possessives and apostrophes", 0.03),
        ],
    ),
]


TAXONOMY: list[TopicSpec] = [
    TopicSpec(section, domain, skill_name, weight)
    for section, domain, skills in _DOMAINS
    for skill_name, weight in skills
]


def section_weight_totals() -> dict[Section, float]:
    """Sum of ``frequency_weight`` per section (each should be ~1.0)."""
    totals: dict[Section, float] = {}
    for spec in TAXONOMY:
        totals[spec.section] = totals.get(spec.section, 0.0) + spec.frequency_weight
    return totals
