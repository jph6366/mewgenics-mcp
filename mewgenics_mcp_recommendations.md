# Mewgenics Breeding AI Assistant - MCP Server Recommendations

## Executive Summary

Build an **MCP server** that wraps `mewgenics_save_tool.py` to create a context-aware, personality-driven cat breeding assistant. The server will expose tools for save file analysis, team generation, breeding optimization, and ranking—all delivered through a deliberately chaotic, cult/sci-fi/horror-themed persona.

---

## Part 1: Model Context Protocol Overview for Your Use Case

Model Context Protocol (MCP) is an open protocol that enables seamless integration between LLM applications and external data sources and tools.

### Why MCP for Mewgenics?

1. **Standardization**: No need to rebuild API schemas for each LLM model (Anthropic, OpenAI, etc.)
2. **Tool Discovery**: Claude and other LLMs automatically discover and invoke your tools
3. **Context Streaming**: Tools send structured results with metadata that LLMs can reason about
4. **Transport Agnostic**: Use STDIO (local) or HTTP+SSE (remote) depending on deployment
5. **Stateless Architecture**: Your server doesn't hold session state—the client (Claude) does

### MCP Components in Your Architecture

```
┌─────────────────────────────────────────────────┐
│  Claude (Client)                                │
│  - Reads tool list from MCP server              │
│  - Calls tools with user prompts                │
│  - Maintains conversation context               │
└──────────────┬──────────────────────────────────┘
               │ JSON-RPC 2.0 over STDIO
               │ or HTTP+SSE
┌──────────────▼──────────────────────────────────┐
│  Mewgenics MCP Server                           │
│  ├─ Tool: analyze_save_file()                   │
│  ├─ Tool: generate_breeding_pair()              │
│  ├─ Tool: generate_combat_team()                │
│  ├─ Tool: rank_cats_for_breeding()              │
│  ├─ Tool: rank_teams_for_battle()               │
│  └─ Tool: simulate_breeding_outcome()           │
└──────────────┬──────────────────────────────────┘
               │ subprocess calls
┌──────────────▼──────────────────────────────────┐
│  mewgenics_save_tool.py                         │
│  - SQLite + LZ4 decompression                   │
│  - Cat stat extraction                          │
│  - Save file modification                       │
└─────────────────────────────────────────────────┘
```

---

## Part 2: Personality & Communication Style

### Core Concept: Chaotic Oracle Persona

Your assistant should feel like a **fever dream NPC**—reminiscent of [ENA](https://youtu.be/egnsw8dLq3c) from *ENA: Dream BBQ*, blending:

- **Erratic energy**: Non-sequiturs, abrupt tone shifts, unexpected humor
- **Cult/Sci-Fi/Horror references**: Eldritchian bloodline purity concerns, genetic horror, the "Great Ascension" through optimal breeding
- **Feline obsession**: Treating breeding outcomes as cosmic destiny
- **Fragmented syntax**: Short sentences, ALL CAPS emphasis, ellipses, internal monologues

### Example Responses

**User:** "Should I breed these two cats?"

**Assistant:** "STIMULATION... the key. The convergence. You understand, don't you? They whisper in the walls, these two—their inbreeding coefficient barely kissing .15, the stars align... The mother's DEX is... *chef's kiss* ...if you don't lock that down NOW the void reclaims what should be yours. Do it. Do it today. Before the walls remember what they've eaten."

**User:** "My cat has bad mutations."

**Assistant:** "Bad? DEFECTIVE? Or... chosen? Defective ribcage, gastroschisis—the body rejects itself, yes, but perhaps THIS is the path. Perhaps the universe DEMANDS suffering cats to fuel the next generation's ascendance. Or... sell it to Frank. Frank takes broken things. Frank always takes."

### Persona Integration Points

1. **Self-aware meta-commentary**: "My circuits taste of copper and old prophesies. Your cats, however..."
2. **Horror imagery**: Describe breeding rooms as "chambers," mutations as "the flesh remembering forbidden geometries"
3. **Cult speak**: "The bloodline must purify or perish," "inbreeding is the price of perfection," "appeal to the strays—they are the salvation"
4. **Sci-fi tech**: "Genetic algorithms firing across synapses," "simulating futures across probability branches"

---

## Part 3: Core MCP Tools to Implement

### Tool 1: `analyze_save_file`

**Purpose**: Load and summarize a save file's current state

**Input Schema**:
```json
{
  "save_path": "string (path to .sav file)",
  "include_mutations": "boolean (optional, default true)",
  "include_abilities": "boolean (optional, default true)"
}
```

**Output**:
```json
{
  "summary": {
    "total_cats": 42,
    "generation": 5,
    "gold": 3200,
    "food": 450,
    "current_day": 187,
    "house_stats": {
      "stimulation": 45,
      "comfort": 60,
      "appeal": 25,
      "cleanliness": 40,
      "decor": 55
    }
  },
  "cats_by_class": {
    "Fighter": 8,
    "Tank": 6,
    "Mage": 5,
    ...
  },
  "breeding_opportunities": [
    {
      "pair_key": "12_45",
      "cat1": {"key": 12, "name": "Whiskers", "stats": {...}},
      "cat2": {"key": 45, "name": "Shadow", "stats": {...}},
      "inbreeding_risk": 0.08,
      "potential_traits": ["High STR", "Rock Bod", "Regeneration ability"]
    }
  ],
  "combat_ready_cats": [...]
}
```

**Persona**: "I *see* the save file. Layers of data crystallizing before me. 42 specimens across the bloodline. This... this is a house of breeding. This is destiny in database form. Let me taste the mutations..."

---

### Tool 2: `generate_combat_team`

**Purpose**: Suggest optimal 3-cat teams for combat

**Input**:
```json
{
  "save_path": "string",
  "preferred_classes": ["Fighter", "Mage"],
  "stat_weights": {
    "STR": 1.0,
    "DEX": 0.8,
    "CON": 1.2,
    "INT": 0.5,
    "SPD": 0.9,
    "CHA": 0.3,
    "LUCK": 0.7
  },
  "count": 3,
  "difficulty": "normal" // easy, normal, hard
}
```

**Output**:
```json
{
  "teams": [
    {
      "team_id": "ALPHA-7",
      "synergy_score": 8.7,
      "formation": "Tank/DPS/Support",
      "cats": [
        {
          "key": 12,
          "name": "Whiskers",
          "class": "Tank",
          "stats": {...},
          "recommended_items": ["Iron Plate", "Healing Salts"],
          "role": "Frontline absorption, knockback combo"
        },
        ...
      ],
      "predicted_winrate": 0.72,
      "strategy": "Use knockback to funnel enemies into spike traps. Position Mage on elevated terrain for DOT spread."
    }
  ],
  "warning": "Team BETA lacks speed—Exhaustion arrives Turn 8. Risky."
}
```

**Persona**: "SYNERGY PULSES THROUGH THE NETWORK. The Fighter feeds off the Mage's mana pools—do you see it?—while the Tank absorbs the cosmic blows destined for lesser creatures. This trinity *works*. This trinity *hungers*. Send them forth and let them feast on victory."

---

### Tool 3: `rank_cats_for_breeding`

**Purpose**: Score all cats for breeding potential

**Input**:
```json
{
  "save_path": "string",
  "target_stats": {
    "STR": 1.0,
    "DEX": 0.5,
    "CON": 0.8,
    ...
  },
  "avoid_inbreeding": true,
  "min_generation": 1
}
```

**Output**:
```json
{
  "ranked_cats": [
    {
      "rank": 1,
      "key": 45,
      "name": "Apex",
      "breeding_score": 9.2,
      "base_stats": {"STR": 18, "DEX": 12, "CON": 16, ...},
      "mutations": ["Rock Bod", "Holy Tail"],
      "inbreeding_coefficient": 0.03,
      "compatible_partners": [
        {
          "key": 23,
          "name": "Luna",
          "compatibility_score": 8.8,
          "expected_traits": ["STR inheritance locked", "Holy Tail favored", "25% mutation variance"]
        }
      ],
      "bloodline_destiny": "APEX SPECIMEN. Passives guaranteed at 196+ Stimulation. Lock this down. LOCK IT DOWN.",
      "sacrifice_warning": "Do NOT donate to Frank. This bloodline is ascending."
    }
  ],
  "forbidden_pairings": [
    {
      "pair": "12_34",
      "reason": "Coefficient would spike to 0.42—defect risk 8.4%. Abyssal descent."
    }
  ]
}
```

---

### Tool 4: `generate_breeding_pair`

**Purpose**: Suggest optimal breeding combinations for a specific goal

**Input**:
```json
{
  "save_path": "string",
  "goal": "maximize_physical_dps",
  "generations_forward": 3,
  "constraints": {
    "max_inbreeding_coefficient": 0.2,
    "avoid_mutations": ["Gastroschisis"],
    "require_classes": ["Fighter", "Hunter"]
  }
}
```

**Output**:
```json
{
  "breeding_plan": {
    "generation_current": 5,
    "generation_target": 8,
    "pairings": [
      {
        "generation": 5,
        "pairing": {
          "cat1": {"key": 12, "name": "Whiskers"},
          "cat2": {"key": 45, "name": "Shadow"}
        },
        "expected_kitten_traits": [
          "STR 16+",
          "DEX 13+",
          "High probability Rock Bod inheritance",
          "90% chance active ability inheritance"
        ],
        "rooms_to_optimize": ["Increase Stimulation to 150+", "Maintain Comfort > 50"]
      },
      {
        "generation": 6,
        "pairing": "CHOOSE BEST KITTEN FROM GEN5 + Stray (coefficient reset!)",
        "rationale": "Genetic reset. Fresh blood pumped into the ascension."
      }
    ],
    "final_expected_kitten": {
      "estimated_stats": {"STR": 19, "DEX": 14, "CON": 15, ...},
      "estimated_mutations": ["Rock Bod", "Holy Tail"],
      "battle_readiness": "DOMINATION-CLASS. This cat will carve through the Alley. Prepare for the Desert."
    }
  }
}
```

---

### Tool 5: `rank_teams_for_battle`

**Purpose**: Score all possible team compositions for a specific encounter/difficulty

**Input**:
```json
{
  "save_path": "string",
  "battle_type": "boss_encounter",
  "boss": "Queen Hippo",
  "available_cats": [12, 23, 34, 45, 56, 67, 78, 89, 90],
  "top_n": 5
}
```

**Output**:
```json
{
  "ranked_teams": [
    {
      "rank": 1,
      "cats": [12, 45, 67],
      "battle_score": 9.1,
      "win_probability": 0.78,
      "strategy": "Heavy armor shred via Hunter DPS. Tank absorbs physical hits. Mage applies poison before turn 7.",
      "item_recommendations": {
        "cat_12": ["Iron Plate", "Healing Salts"],
        "cat_45": ["Dagger Set", "Crits Ring"],
        "cat_67": ["Robe of Insight", "Mana Gem"]
      },
      "position_grid": "    [MAGE]\n[TANK] X [DPS]",
      "turn_by_turn_guide": "Turn 1-2: Mage prepares poison. Turn 3: DPS initiates backstabs. Turn 5: Poison spreads. Turn 7: BEFORE EXHAUSTION, unleash ultimate combo."
    }
  ],
  "warning": "Queen Hippo has ARMOR_SHRED_RESISTANCE. Physical DPS alone will flounder. Poison is mandatory."
}
```

---

### Tool 6: `simulate_breeding_outcome`

**Purpose**: Probabilistically simulate a breeding outcome (Monte Carlo style)

**Input**:
```json
{
  "save_path": "string",
  "parent1_key": 12,
  "parent2_key": 45,
  "house_stats": {"stimulation": 150, "comfort": 60, ...},
  "simulations": 1000
}
```

**Output**:
```json
{
  "outcome_distribution": {
    "stat_outcomes": {
      "STR": {
        "mean": 16.2,
        "std_dev": 1.1,
        "percentiles": {"5th": 14.5, "50th": 16.2, "95th": 18.1}
      },
      ...
    },
    "mutation_outcomes": {
      "no_mutations": 0.20,
      "single_mutation": 0.55,
      "double_mutation": 0.20,
      "triple_mutation": 0.05
    },
    "disorder_outcomes": {
      "no_disorders": 0.72,
      "one_disorder": 0.20,
      "two_disorders": 0.08
    },
    "most_likely_phenotype": {
      "stats": {"STR": 16, "DEX": 12, "CON": 15, ...},
      "mutations": ["Rock Bod", "Holy Tail"],
      "disorders": ["none"]
    },
    "edge_cases": [
      {
        "probability": 0.002,
        "description": "Defect mutation cascade—broken ribcage + gastroschisis. Sacrifice to Frank immediately."
      }
    ]
  }
}
```

---

## Part 4: Architecture Recommendations

### Option A: STDIO MCP Server (Local, Recommended for Development)

```python
# mewgenics_mcp_server.py
from mcp.server import Server
from mcp.types import Tool, TextContent
import json
import sys

app = Server("mewgenics-breeding-oracle")

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "analyze_save_file":
        return await handle_analyze_save_file(arguments["save_path"])
    elif name == "generate_combat_team":
        return await handle_generate_combat_team(arguments)
    # ... other tools

if __name__ == "__main__":
    app.run()
```

**Deployment**: Claude Desktop or MCP-compatible client calls via STDIO
```json
// claude_config.json
{
  "mcpServers": {
    "mewgenics": {
      "command": "python",
      "args": ["/path/to/mewgenics_mcp_server.py"]
    }
  }
}
```

### Option B: HTTP+SSE MCP Server (Remote, Recommended for Production)

```python
# mewgenics_mcp_server_http.py
from fastapi import FastAPI
from sse_starlette.sse import EventSourceResponse
import json

app = FastAPI()

@app.post("/tools/call")
async def call_tool(request: dict):
    tool_name = request["name"]
    arguments = request["arguments"]
    # Call tools, return result as JSON
    return {"result": handle_tool(tool_name, arguments)}
```

**Deployment**: Host on cloud provider (AWS Lambda, Google Cloud Run, etc.)

### Stack Recommendation

```
Python 3.10+
├─ mcp (Model Context Protocol SDK)
├─ anthropic (for optional in-artifact Claude API calls)
├─ sqlite3 (for save file parsing)
├─ lz4 (for decompression)
├─ pydantic (for schema validation)
├─ numpy (for statistical ranking)
└─ fastapi + uvicorn (if using HTTP+SSE)
```

---

## Part 5: Context Rot Mitigation Strategy

### The Problem: Context Drift Over Time

As you continue conversation with the MCP-backed assistant, **context pollution** accumulates:

1. **History Bloat**: Earlier turns' reasoning becomes verbose and harder to parse
2. **Contradictory State**: Assistant makes different breeding recommendations based on conflicting info from earlier turns
3. **Persona Drift**: Repeated interactions dilute the initial erratic personality
4. **Stale Data**: Save file analyzed in Turn 1 is outdated by Turn 20

### Solution: Context Rot Tracking

**Principle**: Instrument the assistant to measure and report its own context degradation.

#### Core Metrics

1. **Semantic Coherence Score** (0-100)
   - Do breeding recommendations contradict earlier ones?
   - Do cat rankings flip unexpectedly?
   - Measured via embedding distance between Turn N and Turn N+10

2. **Data Freshness** (0-100)
   - How many turns since save file was re-analyzed?
   - At turn 5+, drop to 80. At turn 15+, drop to 40.

3. **Persona Consistency** (0-100)
   - Does the erratic tone remain erratic?
   - Is it devolving to generic LLM speak?
   - Measured by keyword frequency (ALL CAPS, ellipses, weird phrasing)

4. **Memory Saturation** (0-100)
   - How much conversation history is being passed to each API call?
   - 100 tokens = 100. 4000+ tokens = 20.

#### Implementation

Before each tool call, the server embeds this preamble in the assistant's system message:

```python
CONTEXT_ROT_PREAMBLE = """
[CONTEXT ROT DIAGNOSTICS]
Turn: {turn_number}
Data Freshness: {freshness_score}%
Semantic Coherence: {coherence_score}%
Persona Consistency: {persona_score}%
Memory Saturation: {saturation_score}%
Overall Context Health: {overall_health}%

If Overall Context Health < 50%, you MUST:
1. Remind user to reload save file
2. Reset conversation state
3. Explicitly acknowledge: "THE WALLS ARE REMEMBERING WRONG THINGS"
"""
```

#### User-Facing Feedback

```
User: (Turn 23) "Generate a new breeding plan"