#!/usr/bin/env python3
"""
breeding_algorithms.py

Genetic simulation and breeding optimization for Mewgenics.
Uses CatData structures from mewgenics_save_tool directly.
"""

import random
from typing import Dict, List, Optional, Tuple, Any

import numpy as np

from mewgenics_save_tool import (
    CatData,
    StatInfo,
    MutationInfo,
    STAT_NAMES,
    MUTATION_SLOT_MAP,
    get_mutation_name,
)


# ==================== Stat Helpers ====================

def get_stat(cat: CatData, stat_name: str) -> int:
    """Get a specific stat value from a CatData object."""
    for s in cat.stats:
        if s.name == stat_name:
            return s.value
    return 0


def get_stats_dict(cat: CatData) -> Dict[str, int]:
    """Return all stats as a name->value dict."""
    return {s.name: s.value for s in cat.stats}


def get_disorders(cat: CatData) -> List[str]:
    """Extract disorder names from cat abilities (Disorder1, Disorder2 slots)."""
    return [
        a.name for a in cat.abilities
        if a.slot.startswith("Disorder") and a.name and a.name != "DefaultMove"
    ]


def get_mutation_list(cat: CatData) -> List[Tuple[str, int]]:
    """Return list of (part_key, mutation_id) for non-zero mutations."""
    result = []
    for m in cat.mutations:
        part_info = MUTATION_SLOT_MAP.get(m.body_part, ("", "unknown"))
        part_key = part_info[1]
        result.append((part_key, m.mutation_id))
    return result


def get_mutation_names(cat: CatData) -> List[str]:
    """Return human-readable mutation names for a cat."""
    names = []
    for m in cat.mutations:
        part_info = MUTATION_SLOT_MAP.get(m.body_part, ("", "unknown"))
        names.append(get_mutation_name(m.mutation_id, part_info[1]))
    return names


# ==================== Stat Inheritance ====================

def simulate_stat_inheritance(
    parent1_stats: Dict[str, int],
    parent2_stats: Dict[str, int],
    stimulation: int,
) -> Dict[str, int]:
    """
    Simulate stat inheritance for one offspring.

    At high Stimulation (196+), always takes the higher parent stat.
    Otherwise weighted random selection toward the higher stat.
    """
    child = {}
    for stat in STAT_NAMES:
        p1 = parent1_stats.get(stat, 0)
        p2 = parent2_stats.get(stat, 0)

        if stimulation >= 196:
            child[stat] = max(p1, p2)
        elif stimulation >= 95:
            child[stat] = max(p1, p2) if random.random() < 0.70 else min(p1, p2)
        elif stimulation >= 32:
            child[stat] = max(p1, p2) if random.random() < 0.55 else min(p1, p2)
        else:
            child[stat] = random.choice([p1, p2])

    return child


def simulate_mutation_inheritance(
    parent1_muts: List[Tuple[str, int]],
    parent2_muts: List[Tuple[str, int]],
    stimulation: int,
) -> List[Tuple[str, int]]:
    """
    Simulate mutation inheritance.

    - 80% chance: inherit from parents
    - 20% chance: regenerate a random mutation
    """
    child_mutations = []
    body_parts = [v[1] for v in MUTATION_SLOT_MAP.values()]
    body_parts_unique = list(dict.fromkeys(body_parts))  # preserve order, deduplicate

    for part_key in body_parts_unique:
        p1_mut = next((m[1] for m in parent1_muts if m[0] == part_key), 0)
        p2_mut = next((m[1] for m in parent2_muts if m[0] == part_key), 0)

        if random.random() < 0.20:
            child_mut = random.randint(300, 330)
        else:
            if p1_mut and p2_mut:
                child_mut = random.choice([p1_mut, p2_mut])
            elif p1_mut or p2_mut:
                child_mut = p1_mut or p2_mut
            else:
                child_mut = 0

        if child_mut:
            child_mutations.append((part_key, child_mut))

    return child_mutations


def simulate_disorder_inheritance(
    parent1_disorders: List[str],
    parent2_disorders: List[str],
    inbreeding_coeff: float,
) -> List[str]:
    """
    Simulate disorder inheritance.

    - 15% chance to inherit from each parent (independent)
    - Additional birth defect roll based on inbreeding coefficient
    """
    child_disorders = []

    if parent1_disorders and random.random() < 0.15:
        child_disorders.append(random.choice(parent1_disorders))
    if parent2_disorders and random.random() < 0.15:
        child_disorders.append(random.choice(parent2_disorders))

    if len(child_disorders) < 2:
        defect_chance = 0.02 + 0.40 * max(inbreeding_coeff - 0.20, 0)
        if random.random() < defect_chance:
            child_disorders.append("birth_defect")

    return child_disorders


# ==================== Scoring ====================

GOAL_STAT_WEIGHTS: Dict[str, Dict[str, float]] = {
    "maximize_physical_dps": {"STR": 1.0, "DEX": 0.8, "SPD": 0.5, "CON": 0.3},
    "maximize_magic_dps":    {"INT": 1.0, "CHA": 0.7, "SPD": 0.5, "LUCK": 0.4},
    "maximize_tank":         {"CON": 1.0, "STR": 0.5, "LUCK": 0.3},
    "maximize_support":      {"CHA": 1.0, "INT": 0.6, "LUCK": 0.5},
    "pure_bloodline":        {s: 0.3 for s in STAT_NAMES},
    "collect_mutations":     {s: 0.2 for s in STAT_NAMES},
    "balanced_stats":        {s: 0.5 for s in STAT_NAMES},
}


def score_cat_for_breeding(
    cat: CatData,
    target_stats: Dict[str, float],
    avoid_inbreeding: bool = True,
    inbreeding_coeff: float = 0.0,
) -> float:
    """Score a cat's breeding potential given target stat weights (0-1 each)."""
    score = 0.0
    cat_stats = get_stats_dict(cat)

    for stat_name, weight in target_stats.items():
        stat_value = cat_stats.get(stat_name, 0)
        normalized = stat_value / 20.0  # 0-20 range assumed
        score += weight * normalized * 100

    # Mutation bonus (collect_mutations goal values this heavily)
    score += len(cat.mutations) * 10

    # Disorder penalty
    disorders = get_disorders(cat)
    score -= len(disorders) * 15

    # Inbreeding penalty (quadratic)
    if avoid_inbreeding and inbreeding_coeff > 0:
        score -= (inbreeding_coeff ** 2) * 50

    return max(0.0, score)


def rank_all_cats(
    cats: List[CatData],
    target_stats: Dict[str, float],
    avoid_inbreeding: bool = True,
    top_n: int = 10,
) -> List[Dict[str, Any]]:
    """
    Score and rank all cats by breeding potential.

    Returns list of result dicts sorted by score descending.
    """
    scored = []
    for cat in cats:
        score = score_cat_for_breeding(cat, target_stats, avoid_inbreeding)
        disorders = get_disorders(cat)
        notes = []
        if len(cat.mutations) > 3:
            notes.append(f"Mutation-rich ({len(cat.mutations)} mutations)")
        if disorders:
            notes.append(f"{len(disorders)} disorder(s): {', '.join(disorders[:2])}")

        scored.append({
            "key": cat.key,
            "name": cat.name or f"Cat-{cat.key}",
            "sex": cat.sex,
            "cat_class": cat.cat_class,
            "level": cat.level,
            "score": round(score, 2),
            "stats": get_stats_dict(cat),
            "mutations": get_mutation_names(cat),
            "mutation_count": len(cat.mutations),
            "disorders": disorders,
            "notes": notes,
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    for i, entry in enumerate(scored):
        entry["rank"] = i + 1

    return scored[:top_n]


def find_best_breeding_pair(
    cats: List[CatData],
    goal: str = "maximize_physical_dps",
) -> Optional[Tuple[CatData, CatData]]:
    """
    Find the best breeding pair for a given goal.

    Prefers male+female pairing; falls back to any pair.
    Returns (parent1, parent2) or None if fewer than 2 cats.
    """
    target_stats = GOAL_STAT_WEIGHTS.get(
        goal, {s: 0.5 for s in STAT_NAMES}
    )

    scores = {cat.key: score_cat_for_breeding(cat, target_stats) for cat in cats}
    sorted_cats = sorted(cats, key=lambda c: scores[c.key], reverse=True)
    top = sorted_cats[:8]

    # Prefer male+female or Ditto combos
    for i, cat1 in enumerate(top):
        for cat2 in top[i + 1:]:
            if cat1.sex != cat2.sex or "Ditto" in (cat1.sex, cat2.sex):
                return (cat1, cat2)

    # Fallback: any top 2
    if len(sorted_cats) >= 2:
        return (sorted_cats[0], sorted_cats[1])

    return None


# ==================== Monte Carlo Simulation ====================

def monte_carlo_breeding_simulation(
    parent1: CatData,
    parent2: CatData,
    house_stats: Dict[str, Any],
    trials: int = 1000,
) -> Dict[str, Any]:
    """
    Run Monte Carlo simulation of breeding outcomes.

    Returns stat distributions, mutation probabilities, and disorder rates.
    """
    p1_stats = get_stats_dict(parent1)
    p2_stats = get_stats_dict(parent2)
    p1_muts = get_mutation_list(parent1)
    p2_muts = get_mutation_list(parent2)
    p1_disorders = get_disorders(parent1)
    p2_disorders = get_disorders(parent2)

    stimulation = house_stats.get("stimulation", 50)
    inbreeding_coeff = house_stats.get("inbreeding_coeff", 0.0)

    stat_results: Dict[str, List[int]] = {s: [] for s in STAT_NAMES}
    mutation_counts = {"none": 0, "one": 0, "multi": 0}
    disorder_counts = {"none": 0, "one": 0, "two_plus": 0}

    for _ in range(trials):
        child_stats = simulate_stat_inheritance(p1_stats, p2_stats, stimulation)
        for stat in STAT_NAMES:
            stat_results[stat].append(child_stats[stat])

        mutations = simulate_mutation_inheritance(p1_muts, p2_muts, stimulation)
        if len(mutations) == 0:
            mutation_counts["none"] += 1
        elif len(mutations) == 1:
            mutation_counts["one"] += 1
        else:
            mutation_counts["multi"] += 1

        disorders = simulate_disorder_inheritance(p1_disorders, p2_disorders, inbreeding_coeff)
        if len(disorders) == 0:
            disorder_counts["none"] += 1
        elif len(disorders) == 1:
            disorder_counts["one"] += 1
        else:
            disorder_counts["two_plus"] += 1

    # Summarize stats
    stat_summary = {}
    for stat, values in stat_results.items():
        arr = np.array(values)
        stat_summary[stat] = {
            "mean": round(float(np.mean(arr)), 2),
            "std": round(float(np.std(arr)), 2),
            "p5":  int(np.percentile(arr, 5)),
            "p50": int(np.percentile(arr, 50)),
            "p95": int(np.percentile(arr, 95)),
        }

    for key in mutation_counts:
        mutation_counts[key] = round(mutation_counts[key] / trials, 3)
    for key in disorder_counts:
        disorder_counts[key] = round(disorder_counts[key] / trials, 3)

    return {
        "trials": trials,
        "stimulation_used": stimulation,
        "stat_distribution": stat_summary,
        "expected_stats": {s: stat_summary[s]["mean"] for s in STAT_NAMES},
        "best_case_stats": {s: stat_summary[s]["p95"] for s in STAT_NAMES},
        "mutation_probability": mutation_counts,
        "disorder_probability": disorder_counts,
    }
