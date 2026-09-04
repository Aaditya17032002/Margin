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


def test_a_paragraph_is_attributed_to_the_source_whose_citation_covers_it():
    """Attribution comes from the search tool's own citation ranges, not from
    asking the model afterwards which page it was thinking of."""
    from app.providers.azure import _parse_responses_output

    text = (
        "New York City procurements follow the PPB Rules.\n\n"
        "Vendors must enrol in PASSPort before award.\n\n"
        "This paragraph cites nothing at all."
    )
    body = {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": text,
                        "annotations": [
                            {
                                "type": "url_citation",
                                "start_index": 0,
                                "end_index": 47,
                                "url": "https://nyc.gov/ppb",
                                "title": "PPB Rules",
                            },
                            {
                                "type": "url_citation",
                                "start_index": 49,
                                "end_index": 92,
                                "url": "https://nyc.gov/passport",
                                "title": "PASSPort",
                            },
                        ],
                    }
                ],
            }
        ]
    }
    report, sources, claims = _parse_responses_output(body)

    assert report.startswith("New York City procurements")
    assert [s["url"] for s in sources] == ["https://nyc.gov/ppb", "https://nyc.gov/passport"]
    assert [c["sources"] for c in claims] == [
        ["https://nyc.gov/ppb"],
        ["https://nyc.gov/passport"],
        [],
    ]


def test_citation_ranges_stay_valid_across_several_output_blocks():
    """Each block's offsets are relative to itself; stitching them must not
    shift a citation onto the wrong paragraph."""
    from app.providers.azure import _parse_responses_output

    body = {
        "output": [
            {
                "type": "output_text",
                "text": "First block claim.",
                "annotations": [
                    {"type": "url_citation", "start_index": 0, "end_index": 18, "url": "https://a.gov"}
                ],
            },
            {
                "type": "output_text",
                "text": "Second block claim.",
                "annotations": [
                    {"type": "url_citation", "start_index": 0, "end_index": 19, "url": "https://b.gov"}
                ],
            },
        ]
    }
    _, _, claims = _parse_responses_output(body)
    assert claims == [
        {"text": "First block claim.", "sources": ["https://a.gov"]},
        {"text": "Second block claim.", "sources": ["https://b.gov"]},
    ]


def test_output_with_no_annotations_still_yields_paragraphs():
    """An older deployment returns prose and a flat source list. The report is
    still shown; it is simply honest that nothing is attributed."""
    from app.providers.azure import _parse_responses_output

    body = {"output_text": "One claim.\n\nAnother claim."}
    _, _, claims = _parse_responses_output(body)
    assert [c["text"] for c in claims] == ["One claim.", "Another claim."]
    assert all(c["sources"] == [] for c in claims)


def test_a_claim_never_points_at_a_source_the_panel_will_not_show():
    """A citation marker the reader cannot follow is worse than none."""
    from app.agents.orchestrator import _attributed_claims

    claims = _attributed_claims(
        [{"text": "A claim.", "sources": ["https://kept.gov", "https://dropped.gov"]}],
        [{"url": "https://kept.gov", "title": "Kept", "site": "kept.gov"}],
    )
    assert claims == [{"text": "A claim.", "sources": ["https://kept.gov"]}]
