from __future__ import annotations

from app.services.clinical import generator as gen


def test_ranker_selects_recent_higher():
    topic = "fractura de cadera"

    base = {
        "title": "Hip fracture management guideline",
        "abstract": "management of hip fracture",
        "publication_types": ["Practice Guideline"],
        "is_open_access": True,
    }

    it_new = {**base, "pub_year": 2024}
    it_old = {**base, "pub_year": 2010}

    s_new = gen._score_pubmed_item(topic=topic, it=it_new)
    s_old = gen._score_pubmed_item(topic=topic, it=it_old)

    assert s_new > s_old


def test_ranker_boosts_guideline_over_review():
    topic = "tendinopatía aquilea"

    it_guideline = {
        "title": "Achilles tendinopathy guideline",
        "abstract": "recommendations",
        "publication_types": ["Practice Guideline"],
        "pub_year": 2022,
        "is_open_access": False,
    }
    it_review = {
        "title": "Achilles tendinopathy review",
        "abstract": "overview",
        "publication_types": ["Review"],
        "pub_year": 2022,
        "is_open_access": False,
    }

    assert gen._score_pubmed_item(topic=topic, it=it_guideline) > gen._score_pubmed_item(topic=topic, it=it_review)
