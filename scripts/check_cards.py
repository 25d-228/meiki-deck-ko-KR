"""Basic content checks for one completed Korean stage and accepted predecessors."""

import json
import re
import sys
import unicodedata
from pathlib import Path


def lengths(text):
    text = unicodedata.normalize("NFC", text)
    return (
        sum(any(ch.isalnum() for ch in piece) for piece in text.split()),
        sum(not ch.isspace() for ch in text),
    )


def check(stage):
    root = Path(__file__).resolve().parents[1]
    counts = [200, 600, 800, 1200, 1400, 1600, 1800, 1200]
    required = {
        "schema_version", "id", "locale", "sentence", "cloze", "answer",
        "accepted_answers", "lemma", "meaning", "part_of_speech",
    }
    support = {
        "target_unit", "morphology", "pronunciation", "prosody", "speech_level",
        "social_context", "lexical_frame", "root", "script_note", "recognition_only",
    }
    path = root / "cards" / "ko-KR" / f"{stage}.json"
    cards = json.loads(path.read_text(encoding="utf-8"))
    expected = [f"ko-{stage}-{i:04d}" for i in range(1, counts[int(stage)] + 1)]
    assert isinstance(cards, list) and len(cards) == len(expected), "Stage count"
    assert [card["common"]["id"] for card in cards] == expected, "Ordered stage IDs"
    coverage = (root / "coverage" / "ko-KR" / f"{stage}.md").read_text(encoding="utf-8")
    rows = re.findall(r"^\| (ko-\d{2}-\d{4}) \| ([^|]+) \| ([^|]+) \|$", coverage, re.M)
    assert [row[0] for row in rows] == expected, "Exactly one ordered coverage row per card"
    assert all(block.strip() and point.strip() for _, block, point in rows), "Coverage values"
    seen_ids, seen_sentences = set(), set()
    for previous in sorted(path.parent.glob("*.json")):
        if previous.stem >= stage:
            continue
        for card in json.loads(previous.read_text(encoding="utf-8")):
            seen_ids.add(card["common"]["id"])
            seen_sentences.add(unicodedata.normalize("NFC", card["common"]["sentence"]))
    sentence_cap = (8, 32) if int(stage) < 2 else (10, 44) if int(stage) == 2 else (12, 60)
    for card in cards:
        assert set(card) == {"common", "language_specific"}, "Two card regions"
        common, specific = card["common"], card["language_specific"]
        ident = common["id"]
        assert required <= set(common) <= required | {"register", "note"}, (ident, "Common fields")
        assert type(common["schema_version"]) is int and common["schema_version"] == 2, ident
        assert common["locale"] == "ko-KR", ident
        for key, value in common.items():
            if key not in {"schema_version", "accepted_answers"}:
                assert isinstance(value, str) and value.strip(), (ident, key)
                assert value == unicodedata.normalize("NFC", value), (ident, "NFC", key)
        sentence, cloze = common["sentence"], common["cloze"]
        assert sentence.count(cloze) == 1 and common["answer"] == cloze, (ident, "Cloze")
        assert all(n <= cap for n, cap in zip(lengths(sentence), sentence_cap)), (ident, "Sentence cap")
        assert isinstance(common["accepted_answers"], list), ident
        for answer in [cloze, *common["accepted_answers"]]:
            assert isinstance(answer, str) and answer.strip(), (ident, "Answer type")
            assert answer == unicodedata.normalize("NFC", answer), (ident, "Answer NFC")
            assert all(n <= cap for n, cap in zip(lengths(answer), (3, 16))), (ident, "Answer cap")
        assert isinstance(specific, dict) and set(specific) <= support, (ident, "Support fields")
        assert specific.get("target_unit") in {"word", "attached morpheme", "phrase", "fixed utterance"}, ident
        if specific["target_unit"] == "attached morpheme":
            assert specific.get("morphology"), (ident, "Intentional morpheme boundary")
        for key, value in specific.items():
            if key == "recognition_only":
                assert value is True, ident
            else:
                assert isinstance(value, str) and value.strip(), (ident, key)
                assert value == unicodedata.normalize("NFC", value), (ident, key, "NFC")
        assert ident not in seen_ids, (ident, "Duplicate ID")
        assert sentence not in seen_sentences, (ident, "Duplicate sentence")
        seen_ids.add(ident)
        seen_sentences.add(sentence)
    print(f"PASS: stage {stage}, {len(cards)} cards and coverage rows; fields, IDs, clozes, caps and duplicates.")


if __name__ == "__main__":
    check(sys.argv[1])
