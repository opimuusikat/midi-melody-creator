from __future__ import annotations

"""
Deduplication / diversity checks for the melody corpus.

We treat melodies as "the same" if their *interval sequence* and *rhythm
signature* match, even if transposed (transposition-invariant). We also reject
near-duplicates using edit distance on interval sequences under a threshold.
"""

import hashlib
from dataclasses import dataclass, field

from src.models import Melody


def _interval_sequence(melody: Melody) -> list[int]:
    notes = melody.notes
    return [notes[i + 1].midi_pitch - notes[i].midi_pitch for i in range(len(notes) - 1)]


def _parsons_code(intervals: list[int]) -> str:
    return "".join("U" if i > 0 else "D" if i < 0 else "R" for i in intervals)


def _levenshtein(a: list[int], b: list[int]) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    # classic DP, O(len(a)*len(b)) but sequences are short (monophonic phrases)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            cur.append(min(cur[-1] + 1, prev[j] + 1, prev[j - 1] + cost))
        prev = cur
    return prev[-1]


@dataclass
class DiversityChecker:
    max_similarity_threshold: float = 0.20
    seen_hashes: set[str] = field(default_factory=set)
    seen_parsons_rhythm: dict[tuple[str, tuple[str, ...]], list[list[int]]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """
        Return a JSON-serializable representation of the dedupe state.

        Intentionally compact:
        - seen_hashes stored as a list of hex digests
        - seen_parsons_rhythm stored as a list of entries (since JSON has no tuple keys)
        """
        entries: list[dict] = []
        for (parsons, rhythm_sig), candidates in self.seen_parsons_rhythm.items():
            # Candidates order is not semantically important; sort for deterministic serialization.
            candidates_sorted = sorted((tuple(intervals) for intervals in candidates))
            entries.append(
                {
                    "parsons": parsons,
                    "rhythm": list(rhythm_sig),
                    "candidates": [list(intervals) for intervals in candidates_sorted],
                }
            )

        # Deterministic ordering for stable JSON snapshots.
        entries.sort(key=lambda e: (e["parsons"], tuple(e["rhythm"])))

        return {
            "version": 1,
            "max_similarity_threshold": float(self.max_similarity_threshold),
            "seen_hashes": sorted(self.seen_hashes),
            "seen_parsons_rhythm": entries,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DiversityChecker":
        version = int(data.get("version", 1))
        if version != 1:
            raise ValueError(f"Unsupported DiversityChecker state version: {version}")

        dc = cls(max_similarity_threshold=float(data.get("max_similarity_threshold", 0.20)))
        seen_hashes = data.get("seen_hashes", [])
        if isinstance(seen_hashes, list):
            dc.seen_hashes = set(str(x) for x in seen_hashes)

        entries = data.get("seen_parsons_rhythm", [])
        if isinstance(entries, list):
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                parsons = entry.get("parsons")
                rhythm = entry.get("rhythm")
                candidates = entry.get("candidates", [])
                if not isinstance(parsons, str) or not isinstance(rhythm, list) or not isinstance(candidates, list):
                    continue
                key = (parsons, tuple(str(x) for x in rhythm))
                dc.seen_parsons_rhythm[key] = [
                    [int(x) for x in intervals] for intervals in candidates if isinstance(intervals, list)
                ]

        return dc

    def hash_melody(self, intervals: list[int], rhythm: list[str]) -> str:
        key = f"{intervals}|{rhythm}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def is_too_similar(self, melody: Melody) -> bool:
        intervals = _interval_sequence(melody)
        rhythm = [n.duration for n in melody.notes]
        h = self.hash_melody(intervals, rhythm)

        # Tier 1: exact match on transposition-invariant fingerprint.
        if h in self.seen_hashes:
            return True

        # Tier 2: same Parsons + same rhythm signature → compare to candidates.
        parsons = _parsons_code(intervals)
        rhythm_sig = tuple(rhythm)
        candidates = self.seen_parsons_rhythm.get((parsons, rhythm_sig), [])

        # Tier 3: edit distance threshold on interval sequence
        for prev_intervals in candidates:
            if not prev_intervals and not intervals:
                return True
            dist = _levenshtein(intervals, prev_intervals)
            limit = int(max(1, round(len(intervals) * self.max_similarity_threshold)))
            if dist <= limit:
                return True

        return False

    def register(self, melody: Melody) -> None:
        intervals = _interval_sequence(melody)
        rhythm = [n.duration for n in melody.notes]
        h = self.hash_melody(intervals, rhythm)
        self.seen_hashes.add(h)

        parsons = _parsons_code(intervals)
        key = (parsons, tuple(rhythm))
        self.seen_parsons_rhythm.setdefault(key, []).append(intervals)

