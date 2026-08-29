"""
Regression tests for demo/serve.py matching.

Two bugs guarded against here (see DEMO-SPEC.md's "Demo queries" section):

1. Substring-inside-a-word false positives: "cat" must match "cat" as a
   whole word but never as a substring inside a longer word like
   "catcher" or a caption containing "location"/"scattered".

2. Objects-channel phrase matching: a term must match a multi-word object
   phrase only via the whole phrase or its head noun (last word) — "cup"
   matches "coffee cup", but "cat" must NOT match "cat toy" and "dog"
   must NOT match "dog house". A small lexical exception list on top of
   that blocks compounds where even the head noun isn't the referent
   ("hot dog" is food, not a dog) — see OBJECT_LEXICAL_EXCEPTIONS.

Run: python demo/test_matching.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import serve  # noqa: E402


def whole_words(text: str) -> set:
    return set(re.findall(r"[a-z]+", text.lower()))


def test_cat_query_has_no_substring_false_positives():
    result = serve.search([{"label": "cat", "terms": ["cat"]}])
    assert result["total"] > 0, "expected at least one real cat match"

    for match in result["matches"]:
        photo = serve.CATALOG[match["id"]]
        (reason,) = [r for r in match["reasons"] if r["label"] == "cat"]

        if reason["channel"] == "objects":
            tokens = whole_words(" ".join(photo["objects"]))
        else:
            tokens = whole_words(photo["caption"] + " " + photo["setting"])

        assert "cat" in tokens or "cats" in tokens, (
            f"{match['id']}: 'cat' matched via {reason['channel']} but is not "
            f"a whole word there — likely a substring-inside-a-longer-word "
            f"false positive (e.g. 'catcher', 'location', 'scattered')"
        )


def test_known_substring_false_positives_excluded():
    # 0003/0043/0125 are baseball "catcher" photos; 0105's caption
    # contains "scattered". None contain a real cat. These are the exact
    # false positives the old substring-containment matcher produced.
    result = serve.search([{"label": "cat", "terms": ["cat"]}])
    ids = {m["id"] for m in result["matches"]}
    for false_positive_id in ("0003", "0043", "0125", "0105"):
        assert false_positive_id not in ids, (
            f"{false_positive_id} is a known substring false positive for "
            f"'cat' and must not match"
        )


def test_objects_channel_matches_head_word_only():
    assert serve.objects_match("cup", "coffee cup") is True
    assert serve.objects_match("cup", "cup") is True
    assert serve.objects_match("table", "dining table") is True
    assert serve.objects_match("table", "wooden table") is True

    # A modifier word is not the head noun — must not match.
    assert serve.objects_match("cat", "cat toy") is False
    assert serve.objects_match("dog", "dog house") is False
    assert serve.objects_match("coffee", "coffee cup") is False


def test_hot_dog_lexical_exception():
    # These are the exact compounds DEMO-SPEC.md calls out: the head noun
    # is technically "dog", but the referent is food, not an animal.
    for phrase in ("hot dog", "hot dogs", "hot dog bun", "corn dog"):
        assert serve.objects_match("dog", phrase) is False, (
            f"'{phrase}' must not satisfy 'dog' — lexical exception, not synonym tuning"
        )
    # Sanity: the exception list doesn't break real dog matches.
    assert serve.objects_match("dog", "dog") is True


def test_dog_query_never_claims_hot_dog_as_objects_match():
    result = serve.search([{"label": "dog", "terms": ["dog"]}])
    hot_dog_photo = next((m for m in result["matches"] if m["id"] == "0030"), None)

    if hot_dog_photo is not None:
        # It may still surface via the caption channel ("hot dogs" is a
        # genuine whole word in the caption) — that's fine, it's correctly
        # downgraded to borderline. It must never claim an objects match.
        (reason,) = [r for r in hot_dog_photo["reasons"] if r["label"] == "dog"]
        assert reason["channel"] != "objects", (
            "0030 (hot dog food photo) must not satisfy 'dog' via the objects channel"
        )
        assert hot_dog_photo["confidence"] == "borderline"

    real_dog_ids = {"0009", "0012", "0028", "0036", "0045", "0046", "0047", "0052", "0104", "0112"}
    matched_ids = {m["id"] for m in result["matches"]}
    assert real_dog_ids <= matched_ids, "all known real-dog photos must still match"
    for photo_id in real_dog_ids:
        match = next(m for m in result["matches"] if m["id"] == photo_id)
        assert match["confidence"] == "certain"


if __name__ == "__main__":
    test_cat_query_has_no_substring_false_positives()
    test_known_substring_false_positives_excluded()
    test_objects_channel_matches_head_word_only()
    test_hot_dog_lexical_exception()
    test_dog_query_never_claims_hot_dog_as_objects_match()
    print("OK: matching regression tests passed")
