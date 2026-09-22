"""Typed compatibility graph used for candidate evidence and reranking."""
from __future__ import annotations

from collections import defaultdict
from typing import Any


def build_graph(outfits: list[dict[str, str]]) -> dict[str, dict[str, set[str]]]:
    graph: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    slots = ("hero_id", "second_id", "layer_id", "footwear_id", "accessory_1_id", "accessory_2_id")
    for outfit in outfits:
        ids = [outfit.get(slot) for slot in slots if outfit.get(slot)]
        for left in ids:
            graph[left]["co_occurs"].update(right for right in ids if right != left)
            graph[left][f"occasion:{outfit.get('occasion', 'unknown')}"] .add(outfit.get("outfit_id", "unknown"))
    return graph


def evidence_for(items: list[dict[str, Any]], graph: dict[str, dict[str, set[str]]], outfit: dict[str, str]) -> list[dict[str, Any]]:
    ids = [str(item.get("id")) for item in items]
    paths = []
    for item_id in ids:
        neighbours = sorted(graph.get(item_id, {}).get("co_occurs", set()))
        paths.append({"type": "compatibility", "source": item_id, "relation": "co_occurs", "targets": neighbours[:5]})
    return [{"type": "outfit", "outfit_id": outfit.get("outfit_id"), "occasion": outfit.get("occasion"), "theme": outfit.get("theme")}, *paths]
