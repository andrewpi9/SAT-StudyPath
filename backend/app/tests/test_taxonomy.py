"""The taxonomy is reference data the whole app leans on -- guard its shape."""

from __future__ import annotations

import pytest

from app.data.taxonomy import TAXONOMY, section_weight_totals
from app.models.enums import Section
from app.services.topics import load_taxonomy


def test_every_section_has_four_domains() -> None:
    domains_by_section: dict[Section, set[str]] = {}
    for spec in TAXONOMY:
        domains_by_section.setdefault(spec.section, set()).add(spec.domain)

    assert set(domains_by_section) == {Section.MATH, Section.READING_WRITING}
    for section, domains in domains_by_section.items():
        assert len(domains) == 4, f"{section} has {len(domains)} domains"


def test_each_domain_has_three_to_six_skills() -> None:
    counts: dict[str, int] = {}
    for spec in TAXONOMY:
        counts[spec.domain] = counts.get(spec.domain, 0) + 1
    for domain, count in counts.items():
        assert 3 <= count <= 6, f"{domain} has {count} skills"


def test_skill_names_are_unique() -> None:
    names = [spec.skill_name for spec in TAXONOMY]
    assert len(names) == len(set(names))


@pytest.mark.parametrize("section", [Section.MATH, Section.READING_WRITING])
def test_frequency_weights_sum_to_one_per_section(section: Section) -> None:
    assert section_weight_totals()[section] == pytest.approx(1.0, abs=1e-9)


def test_load_taxonomy_is_idempotent(db) -> None:
    first = load_taxonomy(db)
    db.commit()
    assert len(first) == len(TAXONOMY)

    second = load_taxonomy(db)
    db.commit()
    assert second == []  # nothing new inserted the second time

    # Every topic gets a cold-start mastery row.
    assert all(topic.mastery is not None for topic in first)
