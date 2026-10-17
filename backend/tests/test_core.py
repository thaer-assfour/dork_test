"""Core unit tests: renderer merging, classifier, URL normalization."""
from app.discovery.classifier import classify_bounty, is_self_hosted
from app.dorks.renderer import render_one, render_target
from app.scanner.dedup import normalize_url


class _D:
    def __init__(self, id, template, mergeable=False, merge_group=None):
        self.id = id
        self.template = template
        self.mergeable = mergeable
        self.merge_group = merge_group


def test_render_one_substitutes_domain():
    assert render_one("site:{domain} ext:env", "example.com", "domain") == "site:example.com ext:env"


def test_render_merges_same_group():
    dorks = [
        _D(1, "site:{domain} ext:bak", True, "file_ext"),
        _D(2, "site:{domain} ext:env", True, "file_ext"),
        _D(3, "site:{domain} inurl:admin", False),
    ]
    out = render_target(dorks, "example.com", "domain", max_merge=8)
    queries = {q.query for q in out}
    assert "site:example.com inurl:admin" in queries
    merged = [q for q in out if len(q.dork_ids) > 1]
    assert merged and "OR" in merged[0].query


def test_render_respects_max_merge():
    dorks = [_D(i, f"site:{{domain}} ext:x{i}", True, "g") for i in range(5)]
    out = render_target(dorks, "example.com", "domain", max_merge=2)
    # 5 terms, chunked by 2 -> 3 queries
    assert len(out) == 3


def test_classify_bounty():
    assert classify_bounty("We offer a monetary reward / bounty")[0] is True
    assert classify_bounty("We are unable to offer monetary rewards, recognition only")[0] is False
    assert classify_bounty(None)[0] is None


def test_is_self_hosted():
    assert is_self_hosted("https://security.acme.com/policy", None) is True
    assert is_self_hosted("https://hackerone.com/acme", None) is False


def test_normalize_url():
    assert normalize_url("https://a.com/path/") == normalize_url("https://a.com/path")
    assert normalize_url("HTTP://A.com") == "http://a.com/"
