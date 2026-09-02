"""The SAT topic taxonomy.

Structure mirrors the **digital SAT** (2024+): two sections, four domains each,
broken into the specific skills a tutor would actually diagnose and assign
practice on. Skill names follow College Board's published domain/skill outline;
where College Board lists a single broad skill (e.g. "Boundaries"), it is split
into the finer categories tutors teach to (sentence boundaries vs. internal
punctuation), which is what makes a per-skill study plan useful.

``frequency_weight`` is the skill's approximate share *of its section*. The
per-section weights sum to 1.0. They are derived from College Board's published
test-spec domain weightings and my own experience with question mixes across
released practice tests -- they are approximate and tutor-informed, NOT scraped
or copied from any proprietary source. Approximate domain shares used:

    Math            Algebra 35% · Advanced Math 35% · Problem-Solving & Data 15% · Geometry & Trig 15%
    Reading&Writing Information & Ideas 26% · Craft & Structure 28% · Expression of Ideas 20% · Standard English Conventions 26%

NOTE: no real question text, answer choices, or passages appear anywhere in this
project. Only skill tags and their relative frequencies are stored.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import Section


@dataclass(frozen=True)
class TopicSpec:
    section: Section
    domain: str
    skill_name: str
    frequency_weight: float


TAXONOMY: list[TopicSpec] = [
    # ---- Math : Algebra (~35% of the Math section) ----
    TopicSpec(Section.MATH, "Algebra", "Linear equations in one variable", 0.07),
    TopicSpec(Section.MATH, "Algebra", "Linear equations in two variables", 0.07),
    TopicSpec(Section.MATH, "Algebra", "Linear functions", 0.08),
    TopicSpec(Section.MATH, "Algebra", "Systems of two linear equations in two variables", 0.07),
    TopicSpec(Section.MATH, "Algebra", "Linear inequalities in one or two variables", 0.06),
    # ---- Math : Advanced Math (~35%) ----
    TopicSpec(Section.MATH, "Advanced Math", "Equivalent expressions", 0.07),
    TopicSpec(Section.MATH, "Advanced Math", "Nonlinear equations in one variable", 0.07),
    TopicSpec(Section.MATH, "Advanced Math", "Systems of nonlinear equations", 0.06),
    TopicSpec(Section.MATH, "Advanced Math", "Nonlinear functions", 0.08),
    TopicSpec(Section.MATH, "Advanced Math", "Quadratic and exponential models", 0.07),
    # ---- Math : Problem-Solving and Data Analysis (~15%) ----
    TopicSpec(Section.MATH, "Problem-Solving and Data Analysis", "Ratios, rates, and proportional relationships", 0.03),
    TopicSpec(Section.MATH, "Problem-Solving and Data Analysis", "Percentages", 0.025),
    TopicSpec(Section.MATH, "Problem-Solving and Data Analysis", "One-variable data: center and spread", 0.025),
    TopicSpec(Section.MATH, "Problem-Solving and Data Analysis", "Two-variable data: models and scatterplots", 0.025),
    TopicSpec(Section.MATH, "Problem-Solving and Data Analysis", "Probability and conditional probability", 0.02),
    TopicSpec(Section.MATH, "Problem-Solving and Data Analysis", "Inference from sample statistics and margin of error", 0.025),
    # ---- Math : Geometry and Trigonometry (~15%) ----
    TopicSpec(Section.MATH, "Geometry and Trigonometry", "Area and volume", 0.04),
    TopicSpec(Section.MATH, "Geometry and Trigonometry", "Lines, angles, and triangles", 0.04),
    TopicSpec(Section.MATH, "Geometry and Trigonometry", "Right triangles and trigonometry", 0.04),
    TopicSpec(Section.MATH, "Geometry and Trigonometry", "Circles", 0.03),
    # ---- Reading & Writing : Information and Ideas (~26%) ----
    TopicSpec(Section.READING_WRITING, "Information and Ideas", "Central ideas and details", 0.07),
    TopicSpec(Section.READING_WRITING, "Information and Ideas", "Command of evidence: textual", 0.07),
    TopicSpec(Section.READING_WRITING, "Information and Ideas", "Command of evidence: quantitative", 0.06),
    TopicSpec(Section.READING_WRITING, "Information and Ideas", "Inferences", 0.06),
    # ---- Reading & Writing : Craft and Structure (~28%) ----
    TopicSpec(Section.READING_WRITING, "Craft and Structure", "Words in context", 0.12),
    TopicSpec(Section.READING_WRITING, "Craft and Structure", "Text structure and purpose", 0.09),
    TopicSpec(Section.READING_WRITING, "Craft and Structure", "Cross-text connections", 0.07),
    # ---- Reading & Writing : Expression of Ideas (~20%) ----
    TopicSpec(Section.READING_WRITING, "Expression of Ideas", "Rhetorical synthesis", 0.09),
    TopicSpec(Section.READING_WRITING, "Expression of Ideas", "Transitions", 0.07),
    TopicSpec(Section.READING_WRITING, "Expression of Ideas", "Precision and concision", 0.04),
    # ---- Reading & Writing : Standard English Conventions (~26%) ----
    TopicSpec(Section.READING_WRITING, "Standard English Conventions", "Sentence boundaries and punctuation", 0.08),
    TopicSpec(Section.READING_WRITING, "Standard English Conventions", "Subject-verb and pronoun agreement", 0.06),
    TopicSpec(Section.READING_WRITING, "Standard English Conventions", "Verb tense and form", 0.05),
    TopicSpec(Section.READING_WRITING, "Standard English Conventions", "Modifiers and parallel structure", 0.04),
    TopicSpec(Section.READING_WRITING, "Standard English Conventions", "Possessives and apostrophes", 0.03),
]


def section_weight_totals() -> dict[Section, float]:
    """Sum of ``frequency_weight`` per section (each should be ~1.0)."""
    totals: dict[Section, float] = {}
    for spec in TAXONOMY:
        totals[spec.section] = totals.get(spec.section, 0.0) + spec.frequency_weight
    return totals
