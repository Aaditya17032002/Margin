"""What the web said must never be presented as what the document says."""

from __future__ import annotations

from app.agents.orchestrator import _dedupe_sources


def test_every_source_is_kept_not_just_the_first():
    """The bug this exists for: all but the first source was thrown away, and
    that one was stuffed into the field that holds a verbatim clause."""
    sources = _dedupe_sources(
        [
            {"url": "https://www.acquisition.gov/far/52.219-14", "title": "FAR 52.219-14"},
            {"url": "https://www.nyc.gov/site/mocs/rules/ppb-rules.page", "title": "PPB Rules"},
            {"url": "https://sam.gov/content/entity-registration", "title": "Entity registration"},
        ]
    )
    assert len(sources) == 3


def test_each_source_carries_the_host_that_published_it():
    """Whose site a claim came from is most of what makes it worth trusting."""
    sources = _dedupe_sources([{"url": "https://www.acquisition.gov/far/52.219-14", "title": "FAR"}])
    assert sources[0]["site"] == "acquisition.gov"


def test_the_same_page_cited_twice_is_listed_once():
    sources = _dedupe_sources(
        [
            {"url": "https://sam.gov/a", "title": "First mention"},
            {"url": "https://sam.gov/a", "title": "Second mention"},
        ]
    )
    assert len(sources) == 1
    assert sources[0]["title"] == "First mention"


def test_a_source_with_no_url_is_dropped():
    """An unattributable claim is worse than no claim: it looks sourced."""
    assert _dedupe_sources([{"title": "Something someone said"}, {"url": ""}]) == []


def test_a_source_with_no_title_falls_back_to_its_url():
    sources = _dedupe_sources([{"url": "https://sam.gov/a"}])
    assert sources[0]["title"] == "https://sam.gov/a"


def test_the_source_list_is_bounded():
    """A research pass that cited hundreds of pages is a reading list, not a
    citation. The panel has to stay readable."""
    many = [{"url": f"https://example.gov/{i}", "title": str(i)} for i in range(200)]
    assert len(_dedupe_sources(many)) == 40
