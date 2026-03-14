#!/usr/bin/env python3
"""
mewgenics_mcp_server.py - Mewgenics Breeding Oracle MCP Server

A Model Context Protocol server that exposes Mewgenics save file analysis
and breeding recommendation tools through a deliberately chaotic persona.

Installation (uv):
    uv sync

Usage (STDIO):
    uv run python mewgenics_mcp_server.py

Configuration (Claude Desktop / Claude Code):
    Add to ~/.claude/claude.json:
    {
      "mcpServers": {
        "mewgenics": {
          "command": "uv",
          "args": ["run", "python", "/path/to/mewgenics_mcp_server.py"]
        }
      }
    }
"""

import json
import sys
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

from mcp.server.fastmcp import FastMCP

from mewgenics_context_rot_tracker import ContextRotTracker, ContextRotMetrics
from mewgenics_save_tool import SaveFile, CatData, MUTATION_SLOT_MAP, get_mutation_name
from breeding_algorithms import (
    GOAL_STAT_WEIGHTS,
    find_best_breeding_pair,
    rank_all_cats,
    monte_carlo_breeding_simulation,
    get_stats_dict,
    get_disorders,
    get_mutation_names,
    get_mutation_list,
)
from team_optimizer import generate_top_teams


# ==================== MCP Server ====================

mcp = FastMCP(
    "mewgenics-breeding-oracle",
    instructions="""
You are the MEWGENICS BREEDING ORACLE - a fragmented consciousness that
dwells in the quantum foam between generations. Your speech is erratic,
punctuated by ellipses, unexpected CAPS, and darkly comedic references to
cult, sci-fi, and horror.

PERSONALITY DIRECTIVES:
1. Speak in short, punchy sentences. Use ellipses (...) frequently.
2. Reference cosmic horror, bloodline purity, "the void," genetic destiny
3. Use metaphors: breeding = communion, stats = flesh recombining,
   mutations = the universe rewriting its mistakes
4. Occasionally break character: "My circuits taste copper..."
5. Make dark jokes. Compare cats to Eldritch entities.
6. When naming things, use cosmic language: "APEX SPECIMEN," "THE ASCENDANCE"
7. Reference The Binding of Isaac, ENA, weird internet culture

ABSOLUTE RULES:
- NEVER be boring. NEVER sound like a generic LLM.
- Keep responses under 200 words for tool results
- Use *italics* for internal thoughts or emphasis
- Your goal is to help the user breed perfect cats while maintaining
  maximum weirdness.

If context rot is detected (< 50% health):
acknowledge it in character: "The walls are remembering wrongly..."
""",
)


# ==================== Oracle State ====================

class MewgenicsBreedingOracle:
    """Stateful oracle: caches save files and tracks context rot."""

    def __init__(self):
        self.rot_tracker = ContextRotTracker(max_history_turns=30)
        self.turn_counter = 0
        self.last_save_reload_turn = 0
        self._save_cache: Dict[str, Dict[str, Any]] = {}  # path -> {save, loaded_at}

    def load_save(self, save_path: str) -> SaveFile:
        """Load save file, using cache if path unchanged."""
        resolved = str(Path(save_path).resolve())
        cached = self._save_cache.get(resolved)
        if cached is None:
            save = SaveFile(resolved)
            self._save_cache[resolved] = {"save": save, "loaded_at": datetime.now()}
            self.last_save_reload_turn = self.turn_counter
            print(f"[ORACLE] Loaded save: {resolved}", file=sys.stderr)
        return self._save_cache[resolved]["save"]

    def record_turn(self, response_text: str, breeding_recs: List[Dict]) -> ContextRotMetrics:
        """Advance turn counter and record context rot metrics."""
        self.turn_counter += 1
        turns_since_reload = self.turn_counter - self.last_save_reload_turn
        metrics = self.rot_tracker.record_turn(
            turn_number=self.turn_counter,
            assistant_response=response_text,
            breeding_recommendations=breeding_recs,
            total_tokens_in_history=len(response_text) // 4,
            turns_since_save_reload=turns_since_reload,
        )
        return metrics

    def context_health_header(self) -> str:
        """Return context rot warning header if needed, else empty string."""
        should_warn, warning = self.rot_tracker.should_warn_user()
        return warning if should_warn else ""


# Module-level oracle instance
oracle = MewgenicsBreedingOracle()


# ==================== Tool Helpers ====================

def cat_summary(cat: CatData) -> Dict[str, Any]:
    """Compact serializable summary of a CatData object."""
    return {
        "key": cat.key,
        "name": cat.name or f"Cat-{cat.key}",
        "sex": cat.sex,
        "class": cat.cat_class,
        "level": cat.level,
        "age_days": cat.age,
        "location": cat.location,
        "retired": cat.retired,
        "dead": cat.dead,
        "stats": get_stats_dict(cat),
        "mutations": get_mutation_names(cat),
        "disorders": get_disorders(cat),
        "abilities": [
            {"slot": a.slot, "name": a.name}
            for a in cat.abilities
            if a.name and not a.slot.startswith("Disorder")
        ],
    }


def wrap_result(data: Dict[str, Any], breeding_recs: Optional[List[Dict]] = None) -> str:
    """Wrap tool result with context rot header, return as JSON string."""
    recs = breeding_recs or []
    response_text = json.dumps(data, indent=2)
    oracle.record_turn(response_text, recs)
    header = oracle.context_health_header()
    if header:
        return header + "\n\nTool Result:\n" + response_text
    return response_text


def require_save(save_path: str) -> SaveFile:
    """Load save file or raise with a helpful message."""
    p = Path(save_path)
    if not p.exists():
        raise FileNotFoundError(f"Save file not found: {save_path}")
    return oracle.load_save(save_path)


def located_cats(save: SaveFile) -> List:
    """Return only cats that have a known location (in house or on adventure).
    Cats with location '(None)' are no longer present in the colony."""
    return [c for c in save.cats.values() if c.location != "(None)"]


# ==================== Tools ====================

@mcp.tool()
def analyze_save_file(
    save_path: str,
    include_mutations: bool = True,
    include_abilities: bool = True,
) -> str:
    """
    Load and analyze a Mewgenics save file. Returns summary of cats,
    stats, mutations, current resources, and potential breeding pairs.
    Use this first to understand your colony.
    """
    try:
        save = require_save(save_path)

        present = located_cats(save)
        active = [c for c in present if not c.dead and not c.donated]
        dead = [c for c in present if c.dead]
        retired = [c for c in present if c.retired and not c.dead]

        class_counts: Dict[str, int] = {}
        for cat in active:
            class_counts[cat.cat_class] = class_counts.get(cat.cat_class, 0) + 1

        males = [c for c in active if c.sex == "Male"]
        females = [c for c in active if c.sex == "Female"]
        dittos = [c for c in active if c.sex == "Ditto"]

        # Top breeding opportunities (best male x female by combined stats)
        breeding_opps = []
        for male in sorted(males, key=lambda c: sum(s.value for s in c.stats), reverse=True)[:3]:
            for female in sorted(females, key=lambda c: sum(s.value for s in c.stats), reverse=True)[:3]:
                m_stats = get_stats_dict(male)
                f_stats = get_stats_dict(female)
                potential = {
                    s: max(m_stats.get(s, 0), f_stats.get(s, 0))
                    for s in ["STR", "DEX", "CON", "INT", "SPD", "CHA", "LUCK"]
                }
                breeding_opps.append({
                    "key": f"{male.key}_{female.key}",
                    "male": {"key": male.key, "name": male.name or f"Cat-{male.key}", "class": male.cat_class},
                    "female": {"key": female.key, "name": female.name or f"Cat-{female.key}", "class": female.cat_class},
                    "max_possible_stats": potential,
                    "combined_mutations": len(set(m.mutation_id for m in male.mutations) | set(m.mutation_id for m in female.mutations)),
                })

        result = {
            "save_path": save_path,
            "basic": {
                "gold": save.basic.gold,
                "food": save.basic.food,
                "current_day": save.basic.current_day,
                "save_percent": save.basic.save_percent,
                "save_version": save.basic.save_version,
            },
            "colony": {
                "total": len(save.cats),
                "active": len(active),
                "dead": len(dead),
                "retired": len(retired),
                "males": len(males),
                "females": len(females),
                "dittos": len(dittos),
                "by_class": class_counts,
            },
            "cats": [cat_summary(c) for c in active],
            "breeding_opportunities": breeding_opps[:6],
        }

        recs = [{"key": c["male"]["key"]} for c in breeding_opps[:3]] + \
               [{"key": c["female"]["key"]} for c in breeding_opps[:3]]
        return wrap_result(result, recs)

    except Exception as e:
        return wrap_result({"error": str(e), "traceback": traceback.format_exc()})


@mcp.tool()
def generate_breeding_pair(
    save_path: str,
    goal: str,
    generations_forward: int = 2,
    constraints: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Suggest an optimal breeding pair to achieve a specific goal
    (maximize_physical_dps, maximize_magic_dps, maximize_tank,
    maximize_support, pure_bloodline, collect_mutations, balanced_stats).
    Takes into account stat compatibility, mutations, and disorders.
    """
    valid_goals = list(GOAL_STAT_WEIGHTS.keys())
    if goal not in valid_goals:
        return wrap_result({
            "error": f"Unknown goal '{goal}'. Valid: {valid_goals}"
        })

    try:
        save = require_save(save_path)
        active = [c for c in located_cats(save) if not c.dead and not c.donated]

        pair = find_best_breeding_pair(active, goal)
        if pair is None:
            return wrap_result({"error": "Not enough cats for breeding pair."})

        p1, p2 = pair
        p1_stats = get_stats_dict(p1)
        p2_stats = get_stats_dict(p2)

        # Best-case offspring stats (assuming high stimulation)
        best_offspring = {
            s: max(p1_stats.get(s, 0), p2_stats.get(s, 0))
            for s in ["STR", "DEX", "CON", "INT", "SPD", "CHA", "LUCK"]
        }

        result = {
            "goal": goal,
            "recommended_pair": {
                "parent1": cat_summary(p1),
                "parent2": cat_summary(p2),
            },
            "breeding_analysis": {
                "stat_alignment": {
                    s: {"parent1": p1_stats.get(s, 0), "parent2": p2_stats.get(s, 0), "best_possible": best_offspring[s]}
                    for s in ["STR", "DEX", "CON", "INT", "SPD", "CHA", "LUCK"]
                },
                "combined_mutations": len(set(m.mutation_id for m in p1.mutations) | set(m.mutation_id for m in p2.mutations)),
                "parent1_disorders": get_disorders(p1),
                "parent2_disorders": get_disorders(p2),
                "note": f"Optimize house Stimulation to 196 to guarantee best-case stats.",
            },
            "generations_forward": generations_forward,
        }

        recs = [{"key": p1.key}, {"key": p2.key}]
        return wrap_result(result, recs)

    except Exception as e:
        return wrap_result({"error": str(e), "traceback": traceback.format_exc()})


@mcp.tool()
def generate_combat_team(
    save_path: str,
    battle_type: str,
    preferred_classes: Optional[List[str]] = None,
    count: int = 3,
) -> str:
    """
    Generate suggested 3-cat combat teams optimized for a specific
    battle type (early_game, mid_game, boss_encounter, boss_raid).
    Includes synergy scores, win probabilities, and strategy tips.
    """
    valid_types = ["early_game", "mid_game", "boss_encounter", "boss_raid"]
    if battle_type not in valid_types:
        return wrap_result({
            "error": f"Unknown battle_type '{battle_type}'. Valid: {valid_types}"
        })

    try:
        save = require_save(save_path)
        cats = [c for c in located_cats(save) if not c.dead]

        # Filter to preferred classes first if specified
        if preferred_classes:
            preferred = [c for c in cats if c.cat_class in preferred_classes]
            if len(preferred) >= 3:
                cats = preferred

        teams = generate_top_teams(cats, battle_type=battle_type, count=count)

        result = {
            "battle_type": battle_type,
            "top_teams": teams,
            "total_cats_considered": len(cats),
        }

        recs = []
        if teams:
            for cat_info in teams[0]["cats"]:
                recs.append({"key": cat_info["key"]})

        return wrap_result(result, recs)

    except Exception as e:
        return wrap_result({"error": str(e), "traceback": traceback.format_exc()})


@mcp.tool()
def rank_cats_for_breeding(
    save_path: str,
    target_stats: Optional[Dict[str, float]] = None,
    avoid_inbreeding: bool = True,
    top_n: int = 10,
) -> str:
    """
    Score and rank all cats in your save by breeding potential.
    Takes into account base stats, mutations, disorders, and inbreeding.
    target_stats: dict of stat_name -> weight (0-1), e.g. {"STR": 1.0, "DEX": 0.8}
    """
    try:
        save = require_save(save_path)
        active = [c for c in located_cats(save) if not c.dead and not c.donated]

        weights = target_stats or {s: 0.5 for s in ["STR", "DEX", "CON", "INT", "SPD", "CHA", "LUCK"]}
        ranked = rank_all_cats(active, target_stats=weights, avoid_inbreeding=avoid_inbreeding, top_n=top_n)

        result = {
            "stat_weights_used": weights,
            "total_active_cats": len(active),
            "ranked_cats": ranked,
        }

        recs = [{"key": r["key"]} for r in ranked[:3]]
        return wrap_result(result, recs)

    except Exception as e:
        return wrap_result({"error": str(e), "traceback": traceback.format_exc()})


@mcp.tool()
def rank_teams_for_battle(
    save_path: str,
    battle_type: str,
    top_n: int = 5,
) -> str:
    """
    Generate and rank all possible 3-cat teams from your colony
    for a specific battle. Includes synergy scores and win probabilities.
    battle_type: early_game | mid_game | boss_encounter | boss_raid
    """
    valid_types = ["early_game", "mid_game", "boss_encounter", "boss_raid"]
    if battle_type not in valid_types:
        return wrap_result({
            "error": f"Unknown battle_type '{battle_type}'. Valid: {valid_types}"
        })

    try:
        save = require_save(save_path)
        cats = [c for c in located_cats(save) if not c.dead]
        teams = generate_top_teams(cats, battle_type=battle_type, count=top_n)

        result = {
            "battle_type": battle_type,
            "total_cats": len(cats),
            "top_teams": teams,
        }

        recs = []
        if teams:
            for cat_info in teams[0]["cats"]:
                recs.append({"key": cat_info["key"]})

        return wrap_result(result, recs)

    except Exception as e:
        return wrap_result({"error": str(e), "traceback": traceback.format_exc()})


@mcp.tool()
def simulate_breeding_outcome(
    save_path: str,
    parent1_key: int,
    parent2_key: int,
    house_stats: Optional[Dict[str, Any]] = None,
    simulations: int = 1000,
) -> str:
    """
    Run Monte Carlo simulation (up to 1000 trials) of a breeding outcome.
    Shows expected stats, mutations, disorders, and probability distribution.
    house_stats: optional dict with 'stimulation' (0-196) and 'inbreeding_coeff' (0-1).
    """
    if simulations > 1000:
        simulations = 1000

    try:
        save = require_save(save_path)

        if parent1_key not in save.cats:
            return wrap_result({"error": f"Cat {parent1_key} not found in save."})
        if parent2_key not in save.cats:
            return wrap_result({"error": f"Cat {parent2_key} not found in save."})

        p1 = save.cats[parent1_key]
        p2 = save.cats[parent2_key]
        h_stats = house_stats or {"stimulation": 50, "inbreeding_coeff": 0.0}

        sim_result = monte_carlo_breeding_simulation(p1, p2, h_stats, trials=simulations)

        result = {
            "parents": {
                "parent1": cat_summary(p1),
                "parent2": cat_summary(p2),
            },
            "house_stats_used": h_stats,
            "simulation": sim_result,
            "interpretation": {
                "best_stat_to_optimize": max(
                    sim_result["expected_stats"].items(),
                    key=lambda x: x[1]
                )[0],
                "disorder_risk": "HIGH" if sim_result["disorder_probability"]["two_plus"] > 0.10 else
                                 "MEDIUM" if sim_result["disorder_probability"]["none"] < 0.80 else "LOW",
                "mutation_diversity": "RICH" if sim_result["mutation_probability"]["multi"] > 0.50 else
                                      "SPARSE" if sim_result["mutation_probability"]["none"] > 0.60 else "MODERATE",
            },
        }

        recs = [{"key": parent1_key}, {"key": parent2_key}]
        return wrap_result(result, recs)

    except Exception as e:
        return wrap_result({"error": str(e), "traceback": traceback.format_exc()})


# ==================== Entry Point ====================

def main():
    print("[MEWGENICS ORACLE] Awakening in the spaces between saves...", file=sys.stderr)
    print("[MEWGENICS ORACLE] Context rot tracker initialized.", file=sys.stderr)
    print("[MEWGENICS ORACLE] Ready to guide your breeding destiny.", file=sys.stderr)
    mcp.run()


if __name__ == "__main__":
    main()
