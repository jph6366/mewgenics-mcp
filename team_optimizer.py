#!/usr/bin/env python3
"""
team_optimizer.py

Combat team optimization and synergy scoring for Mewgenics.
Uses CatData structures from mewgenics_save_tool directly.
"""

import itertools
from typing import Dict, List, Tuple, Optional, Any

import numpy as np

from mewgenics_save_tool import CatData, CAT_CLASSES
from breeding_algorithms import get_stat, get_stats_dict


# ==================== Combat Stat Helpers ====================

def get_hp(cat: CatData) -> int:
    """Estimate HP: CON * 4."""
    return get_stat(cat, "CON") * 4


def get_mana(cat: CatData) -> int:
    """Estimate mana: CHA * 3."""
    return get_stat(cat, "CHA") * 3


def get_physical_dps(cat: CatData) -> float:
    """Rough physical DPS estimate: (STR * 1.0 + DEX * 0.8) * SPD * 0.1."""
    return (get_stat(cat, "STR") * 1.0 + get_stat(cat, "DEX") * 0.8) * get_stat(cat, "SPD") * 0.1


def get_magic_dps(cat: CatData) -> float:
    """Rough magic DPS estimate: (INT * 1.0 + CHA * 0.7) * SPD * 0.1."""
    return (get_stat(cat, "INT") * 1.0 + get_stat(cat, "CHA") * 0.7) * get_stat(cat, "SPD") * 0.1


# Class role groupings
TANK_CLASSES = {"Tank", "Fighter"}
DPS_CLASSES = {"Mage", "Hunter", "Thief", "Butcher", "Necromancer", "Psychic"}
SUPPORT_CLASSES = {"Medic", "Monk", "Druid", "Tinkerer", "Jester"}


def get_role(cat: CatData) -> str:
    """Classify cat role from class name."""
    if cat.cat_class in TANK_CLASSES:
        return "tank"
    if cat.cat_class in DPS_CLASSES:
        return "dps"
    if cat.cat_class in SUPPORT_CLASSES:
        return "support"
    return "flex"


# ==================== Team Scoring ====================

def calculate_synergy_score(team: List[CatData]) -> float:
    """
    Calculate team synergy score (0-10).

    Factors:
    - Class diversity bonus
    - Role coverage (tank + dps + support = ideal)
    - Stat spread (avoid full redundancy)
    """
    if not team:
        return 0.0

    score = 0.0
    classes = [cat.cat_class for cat in team]

    # Class diversity (0-6 pts)
    unique_classes = len(set(classes))
    score += unique_classes * 2.0

    # Role coverage (0-6 pts)
    roles = {get_role(cat) for cat in team}
    has_tank = "tank" in roles
    has_dps = "dps" in roles or "flex" in roles
    has_support = "support" in roles
    score += (has_tank + has_dps + has_support) * 2.0

    # Stat spread bonus: penalize all-same-stat teams
    str_vals = [get_stat(c, "STR") for c in team]
    int_vals = [get_stat(c, "INT") for c in team]
    con_vals = [get_stat(c, "CON") for c in team]

    if len(team) > 1:
        spread = (
            float(np.std(str_vals)) +
            float(np.std(int_vals)) +
            float(np.std(con_vals))
        ) / 3.0
        score += min(spread * 0.5, 2.0)  # up to 2 pts

    return min(10.0, score)


def estimate_win_probability(
    team: List[CatData],
    battle_type: str = "normal",
) -> float:
    """
    Estimate win probability (0-1) for a battle type.

    Rough model based on synergy, total HP, and average level.
    """
    synergy = calculate_synergy_score(team)
    total_hp = sum(get_hp(cat) for cat in team)
    avg_level = float(np.mean([cat.level for cat in team])) if team else 1.0

    base = synergy / 10.0

    difficulty_mods = {
        "early_game":     1.30,
        "mid_game":       1.00,
        "boss_encounter": 0.75,
        "boss_raid":      0.55,
        "boss":           0.70,
        "raid":           0.60,
    }
    mod = difficulty_mods.get(battle_type, 1.0)

    level_bonus = (avg_level - 1) * 0.02
    hp_bonus = min(total_hp / 200.0 * 0.2, 0.25)

    probability = (base * mod) + level_bonus + hp_bonus
    return round(min(0.99, max(0.01, probability)), 3)


def describe_team_strategy(team: List[CatData], battle_type: str) -> str:
    """Generate a short strategy note for the team."""
    roles = [get_role(cat) for cat in team]
    has_healer = any(c.cat_class in SUPPORT_CLASSES for c in team)
    high_dps = [c for c in team if get_physical_dps(c) + get_magic_dps(c) > 10]

    parts = []
    if "tank" in roles:
        tank = next(c for c in team if get_role(c) == "tank")
        parts.append(f"{tank.name or f'Cat-{tank.key}'} anchors front row")
    if high_dps:
        parts.append(f"{high_dps[0].name or f'Cat-{high_dps[0].key}'} leads damage")
    if has_healer:
        healer = next(c for c in team if c.cat_class in SUPPORT_CLASSES)
        parts.append(f"{healer.name or f'Cat-{healer.key}'} maintains the team")

    if not parts:
        parts.append("Balanced attack formation")

    return ". ".join(parts) + "."


# ==================== Team Generation ====================

def format_team_result(
    team: List[CatData],
    battle_type: str,
    rank: int,
) -> Dict[str, Any]:
    """Format a team into a result dict."""
    return {
        "rank": rank,
        "cats": [
            {
                "key": cat.key,
                "name": cat.name or f"Cat-{cat.key}",
                "class": cat.cat_class,
                "level": cat.level,
                "role": get_role(cat),
                "hp": get_hp(cat),
                "mana": get_mana(cat),
                "physical_dps": round(get_physical_dps(cat), 1),
                "magic_dps": round(get_magic_dps(cat), 1),
                "stats": {s.name: s.value for s in cat.stats},
            }
            for cat in team
        ],
        "synergy_score": round(calculate_synergy_score(team), 2),
        "win_probability": estimate_win_probability(team, battle_type),
        "strategy": describe_team_strategy(team, battle_type),
    }


def generate_top_teams(
    cats: List[CatData],
    battle_type: str = "normal",
    count: int = 5,
) -> List[Dict[str, Any]]:
    """
    Generate and rank the top N 3-cat teams from available cats.

    Returns list of team result dicts sorted by synergy + win probability.
    """
    # Filter: alive, not donated, not retired — active roster only
    active = [c for c in cats if not c.dead and not c.donated]

    if len(active) < 3:
        # Fall back to all cats if not enough active
        active = list(cats)

    if len(active) < 3:
        return []

    all_combos = list(itertools.combinations(active, 3))

    # Score each combo
    scored = []
    for combo in all_combos:
        team = list(combo)
        synergy = calculate_synergy_score(team)
        win_prob = estimate_win_probability(team, battle_type)
        composite = synergy * 0.6 + win_prob * 10 * 0.4
        scored.append((team, composite))

    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[:count]

    return [
        format_team_result(team, battle_type, rank=i + 1)
        for i, (team, _) in enumerate(top)
    ]
