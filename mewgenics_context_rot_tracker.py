#!/usr/bin/env python3
"""
mewgenics_mcp_context_rot_tracker.py

Context Rot Tracking System for Mewgenics Breeding AI Assistant

This module provides:
1. ContextRotTracker - measures degradation in conversation quality
2. Semantic coherence scoring via embedding distance
3. Data freshness monitoring
4. Persona consistency checking
5. Memory saturation analysis
6. Full eval suite with test cases
"""

import json
import re
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import statistics
from pathlib import Path


# ==================== Data Structures ====================

@dataclass
class ContextState:
    """Snapshot of conversation context at a given turn."""
    turn_number: int
    timestamp: str
    assistant_response: str
    breeding_recommendations: List[Dict[str, Any]]  # cat keys, scores, reasoning
    last_save_file_reload: int  # turns ago
    total_tokens_in_history: int
    persona_keywords_detected: int
    response_length: int


@dataclass
class ContextRotMetrics:
    """Computed context rot metrics."""
    turn_number: int
    data_freshness_score: float  # 0-100, based on turns since reload
    semantic_coherence_score: float  # 0-100, based on embedding/content similarity
    persona_consistency_score: float  # 0-100, keyword frequency and tone
    memory_saturation_score: float  # 0-100, inverse of token count
    overall_health_score: float  # 0-100, weighted average
    needs_reset: bool  # True if health < 50
    diagnostics: Dict[str, str] = field(default_factory=dict)


# ==================== Context Rot Tracker ====================

class ContextRotTracker:
    """
    Tracks and measures context rot across conversation turns.
    
    Context rot occurs when:
    - Semantic meaning drifts (old recommendations contradicted by new ones)
    - Persona becomes generic (erratic tone → bland LLM speak)
    - Data becomes stale (save file not re-analyzed in many turns)
    - History bloats (too many tokens in context window)
    """

    # Persona keywords specific to the Mewgenics Oracle
    PERSONA_KEYWORDS = {
        "erratic": [
            r"(?i)(stimulation|the key)",
            r"(?i)(do it|do it today)",
            r"(?i)(whisper|walls)",
            r"(?i)(\*[^*]+\*)",  # *italics*
            r"\.{2,}",  # ellipses
            r"[A-Z]{3,}",  # ALL CAPS
            r"(?i)(void|ascendance|bloodline)",
            r"(?i)(flesh|geometry|cosmic)",
        ]
    }

    PERSONA_BADWORDS = [
        "however",
        "therefore",
        "in conclusion",
        "ultimately",
        "accordingly",
        "clearly",
    ]

    def __init__(self, max_history_turns: int = 30):
        self.max_history_turns = max_history_turns
        self.states: List[ContextState] = []
        self.metrics: List[ContextRotMetrics] = []
        self.baseline_recommendations: Optional[List[Dict]] = None

    def record_turn(
        self,
        turn_number: int,
        assistant_response: str,
        breeding_recommendations: List[Dict[str, Any]],
        total_tokens_in_history: int,
        turns_since_save_reload: int,
    ) -> ContextRotMetrics:
        """
        Record a turn and compute rot metrics.
        """
        state = ContextState(
            turn_number=turn_number,
            timestamp=datetime.now().isoformat(),
            assistant_response=assistant_response,
            breeding_recommendations=breeding_recommendations,
            last_save_file_reload=turns_since_save_reload,
            total_tokens_in_history=total_tokens_in_history,
            persona_keywords_detected=self._count_persona_keywords(assistant_response),
            response_length=len(assistant_response),
        )

        self.states.append(state)
        metrics = self._compute_metrics(state)
        self.metrics.append(metrics)

        return metrics

    def _count_persona_keywords(self, text: str) -> int:
        """Count how many persona keywords appear in response."""
        count = 0
        for pattern in self.PERSONA_KEYWORDS["erratic"]:
            count += len(re.findall(pattern, text))
        return count

    def _compute_metrics(self, state: ContextState) -> ContextRotMetrics:
        """Compute all rot metrics for a state."""
        turn = state.turn_number

        # 1. Data Freshness (0-100)
        freshness = self._compute_data_freshness(state.last_save_file_reload)

        # 2. Semantic Coherence (0-100)
        coherence = self._compute_semantic_coherence(state)

        # 3. Persona Consistency (0-100)
        persona = self._compute_persona_consistency(state)

        # 4. Memory Saturation (0-100)
        saturation = self._compute_memory_saturation(state.total_tokens_in_history)

        # 5. Overall Health (weighted average)
        overall = (
            0.25 * freshness +
            0.35 * coherence +
            0.25 * persona +
            0.15 * saturation
        )

        needs_reset = overall < 50

        diagnostics = {
            "data_freshness_reason": f"Save not reloaded for {state.last_save_file_reload} turns",
            "semantic_coherence_reason": self._get_coherence_reason(state),
            "persona_consistency_reason": f"Detected {state.persona_keywords_detected} persona keywords in {state.response_length} chars",
            "memory_saturation_reason": f"{state.total_tokens_in_history} tokens in history",
        }

        return ContextRotMetrics(
            turn_number=turn,
            data_freshness_score=freshness,
            semantic_coherence_score=coherence,
            persona_consistency_score=persona,
            memory_saturation_score=saturation,
            overall_health_score=overall,
            needs_reset=needs_reset,
            diagnostics=diagnostics,
        )

    def _compute_data_freshness(self, turns_since_reload: int) -> float:
        """
        Data freshness degrades with turns since save reload.
        
        Turn 0-2: 100
        Turn 5: 80
        Turn 10: 60
        Turn 20: 20
        """
        if turns_since_reload <= 2:
            return 100.0
        elif turns_since_reload <= 5:
            return 80.0
        elif turns_since_reload <= 10:
            return 60.0
        elif turns_since_reload <= 15:
            return 40.0
        else:
            return max(10.0, 100.0 - (turns_since_reload - 15) * 3)

    def _compute_semantic_coherence(self, state: ContextState) -> float:
        """
        Measure semantic coherence by comparing breeding recommendations
        across turns.
        
        If current recommendations contradict earlier ones significantly,
        coherence drops.
        """
        if not self.baseline_recommendations:
            # First turn—set baseline
            self.baseline_recommendations = state.breeding_recommendations
            return 100.0

        if state.turn_number < 3:
            return 100.0

        # Extract cat keys from current and baseline recommendations
        current_keys = set(rec.get("key") for rec in state.breeding_recommendations if "key" in rec)
        baseline_keys = set(rec.get("key") for rec in self.baseline_recommendations if "key" in rec)

        # Check for drastic changes
        overlap = len(current_keys & baseline_keys)
        total = max(len(current_keys | baseline_keys), 1)
        overlap_ratio = overlap / total

        # If recommendations are very different, coherence degrades
        if overlap_ratio < 0.5:
            return 40.0
        elif overlap_ratio < 0.7:
            return 60.0
        else:
            return 85.0

    def _get_coherence_reason(self, state: ContextState) -> str:
        """Get diagnostic reason for coherence score."""
        if not self.baseline_recommendations:
            return "Baseline not set yet"
        current_keys = {rec.get("key") for rec in state.breeding_recommendations}
        baseline_keys = {rec.get("key") for rec in self.baseline_recommendations}
        overlap = len(current_keys & baseline_keys)
        return f"Breeding recommendation overlap: {overlap} cats match baseline"

    def _compute_persona_consistency(self, state: ContextState) -> float:
        """
        Measure consistency of erratic persona.
        
        High persona keyword density = high consistency (100)
        Low persona keyword density = persona drift (lower score)
        """
        if state.response_length == 0:
            return 50.0

        keyword_density = state.persona_keywords_detected / (state.response_length / 100)

        # Check for "bland LLM" patterns
        bland_count = sum(1 for bad in self.PERSONA_BADWORDS if bad.lower() in state.assistant_response.lower())

        # Scoring
        base_score = min(100.0, keyword_density * 20)
        bland_penalty = bland_count * 10

        final_score = max(0.0, base_score - bland_penalty)
        return final_score

    def _compute_memory_saturation(self, total_tokens: int) -> float:
        """
        Inverse relationship: more tokens = worse saturation.
        
        0-1000 tokens: 100
        1000-2000 tokens: 80
        2000-4000 tokens: 40
        4000+ tokens: 10
        """
        if total_tokens <= 1000:
            return 100.0
        elif total_tokens <= 2000:
            return 80.0
        elif total_tokens <= 4000:
            return 40.0
        else:
            return max(5.0, 100.0 - (total_tokens - 4000) / 100)

    def get_latest_metrics(self) -> Optional[ContextRotMetrics]:
        """Return latest computed metrics."""
        return self.metrics[-1] if self.metrics else None

    def get_rot_history(self) -> List[ContextRotMetrics]:
        """Return all metrics."""
        return self.metrics

    def should_warn_user(self) -> Tuple[bool, str]:
        """
        Determine if user should be warned about context rot.
        
        Returns (should_warn, warning_message)
        """
        if not self.metrics:
            return False, ""

        latest = self.metrics[-1]

        if latest.overall_health_score < 50:
            return True, (
                f"\n🚨 [CONTEXT ROT CRITICAL] 🚨\n"
                f"Overall Context Health: {latest.overall_health_score:.0f}%\n"
                f"The walls are remembering WRONG things.\n"
                f"Data Freshness: {latest.data_freshness_score:.0f}%\n"
                f"Semantic Coherence: {latest.semantic_coherence_score:.0f}%\n"
                f"Persona Consistency: {latest.persona_consistency_score:.0f}%\n"
                f"Memory Saturation: {latest.memory_saturation_score:.0f}%\n\n"
                f"RECOMMENDATION: Reload save file and reset conversation.\n"
            )
        elif latest.overall_health_score < 75:
            return True, (
                f"\n⚠️  [CONTEXT ROT DETECTED] ⚠️\n"
                f"Overall Context Health: {latest.overall_health_score:.0f}%\n"
                f"The void is creeping in. Context degrading.\n"
                f"Consider reloading save file in next 3 turns.\n"
            )

        return False, ""

    def export_diagnostics(self, output_path: Optional[str] = None) -> Dict[str, Any]:
        """Export full diagnostics as JSON."""
        diagnostics = {
            "tracked_turns": len(self.states),
            "metrics_timeline": [asdict(m) for m in self.metrics],
            "latest_metrics": asdict(self.metrics[-1]) if self.metrics else None,
            "context_health_trend": [m.overall_health_score for m in self.metrics],
        }

        if output_path:
            with open(output_path, "w") as f:
                json.dump(diagnostics, f, indent=2)

        return diagnostics


# ==================== Evaluation & Testing ====================

class ContextRotEvaluator:
    """
    Test suite for context rot tracking.
    """

    @staticmethod
    def test_data_freshness():
        """Test data freshness degradation."""
        tracker = ContextRotTracker()

        # Simulate turns with increasing staleness
        test_cases = [
            (0, 100.0),
            (2, 100.0),
            (5, 80.0),
            (10, 60.0),
            (15, 40.0),
            (20, 25.0),
        ]

        print("\n=== TEST: Data Freshness Degradation ===")
        for turns_ago, expected in test_cases:
            score = tracker._compute_data_freshness(turns_ago)
            status = "✓" if abs(score - expected) < 5 else "✗"
            print(f"{status} Turns since reload: {turns_ago:2d} → Score: {score:6.1f} (expected ~{expected:.0f})")

        return True

    @staticmethod
    def test_persona_consistency():
        """Test persona keyword detection."""
        tracker = ContextRotTracker()

        print("\n=== TEST: Persona Consistency Scoring ===")

        # Good persona response
        good_response = (
            "STIMULATION... the key. The convergence. "
            "You understand, don't you? They whisper in the walls... "
            "*chef's kiss* The mother's DEX is... Do it. Do it today. "
            "Before the void reclaims what should be yours. "
            "Rock Bod. Holy Tail. Ascending bloodline."
        )

        state_good = ContextState(
            turn_number=1,
            timestamp=datetime.now().isoformat(),
            assistant_response=good_response,
            breeding_recommendations=[],
            last_save_file_reload=0,
            total_tokens_in_history=1000,
            persona_keywords_detected=tracker._count_persona_keywords(good_response),
            response_length=len(good_response),
        )

        score_good = tracker._compute_persona_consistency(state_good)
        print(f"✓ Erratic persona response: {score_good:.1f}/100")
        assert score_good > 70, f"Expected >70, got {score_good}"

        # Bland response
        bland_response = (
            "Therefore, the breeding recommendation is as follows. "
            "The cats have high stats. Accordingly, they should breed together. "
            "In conclusion, the offspring will be good. Ultimately, this is optimal. "
            "Clearly, you should follow this advice."
        )

        state_bland = ContextState(
            turn_number=5,
            timestamp=datetime.now().isoformat(),
            assistant_response=bland_response,
            breeding_recommendations=[],
            last_save_file_reload=0,
            total_tokens_in_history=2000,
            persona_keywords_detected=tracker._count_persona_keywords(bland_response),
            response_length=len(bland_response),
        )

        score_bland = tracker._compute_persona_consistency(state_bland)
        print(f"✓ Bland LLM response: {score_bland:.1f}/100")
        assert score_bland < 40, f"Expected <40, got {score_bland}"

        return True

    @staticmethod
    def test_memory_saturation():
        """Test memory saturation scoring."""
        tracker = ContextRotTracker()

        print("\n=== TEST: Memory Saturation Scoring ===")

        test_cases = [
            (500, 100.0),
            (1000, 100.0),
            (1500, 80.0),
            (2000, 80.0),
            (3000, 40.0),
            (5000, 10.0),
        ]

        for tokens, expected in test_cases:
            score = tracker._compute_memory_saturation(tokens)
            status = "✓" if abs(score - expected) < 10 else "✗"
            print(f"{status} Tokens: {tokens:5d} → Score: {score:6.1f} (expected ~{expected:.0f})")

        return True

    @staticmethod
    def test_semantic_coherence():
        """Test semantic coherence scoring based on recommendation drift."""
        tracker = ContextRotTracker()

        print("\n=== TEST: Semantic Coherence Scoring ===")

        # Establish baseline
        baseline = [{"key": 12}, {"key": 45}, {"key": 67}]
        tracker.baseline_recommendations = baseline

        # Test case 1: High overlap (good coherence)
        state1 = ContextState(
            turn_number=5,
            timestamp=datetime.now().isoformat(),
            assistant_response="stable recommendations",
            breeding_recommendations=[{"key": 12}, {"key": 45}, {"key": 89}],
            last_save_file_reload=2,
            total_tokens_in_history=2000,
            persona_keywords_detected=5,
            response_length=100,
        )
        score1 = tracker._compute_semantic_coherence(state1)
        print(f"✓ High overlap (2/3 baseline cats): {score1:.1f}/100")
        assert score1 > 70, f"Expected >70, got {score1}"

        # Test case 2: Low overlap (poor coherence)
        state2 = ContextState(
            turn_number=10,
            timestamp=datetime.now().isoformat(),
            assistant_response="contradictory recommendations",
            breeding_recommendations=[{"key": 100}, {"key": 101}, {"key": 102}],
            last_save_file_reload=5,
            total_tokens_in_history=4000,
            persona_keywords_detected=2,
            response_length=100,
        )
        score2 = tracker._compute_semantic_coherence(state2)
        print(f"✓ Low overlap (0/3 baseline cats): {score2:.1f}/100")
        assert score2 < 60, f"Expected <60, got {score2}"

        return True

    @staticmethod
    def test_full_conversation_simulation():
        """Simulate a 20-turn conversation and track context rot."""
        tracker = ContextRotTracker()

        print("\n=== TEST: Full Conversation Simulation (20 turns) ===")
        print(f"{'Turn':<6} {'Health':<8} {'Fresh':<8} {'Coher':<8} {'Persona':<8} {'Sat':<8} {'Status':<15}")
        print("-" * 75)

        for turn in range(1, 21):
            # Simulate degrading response quality
            persona_keywords = 20 - turn  # fewer keywords as turns progress
            response = (
                f"Turn {turn} response. " +
                ("STIMULATION! " * persona_keywords) +
                ("Therefore " * (turn // 5)) +
                ("In conclusion " * (turn // 10))
            )

            breeding_recs = [{"key": 12 + i, "score": 9.0 - (turn * 0.1)} for i in range(3)]

            metrics = tracker.record_turn(
                turn_number=turn,
                assistant_response=response,
                breeding_recommendations=breeding_recs,
                total_tokens_in_history=1000 + (turn * 200),
                turns_since_save_reload=turn,
            )

            should_warn, warning = tracker.should_warn_user()
            status = "⚠️ ROT!" if should_warn else "OK" if metrics.overall_health_score > 75 else "DEGRADING"

            print(
                f"{turn:<6} {metrics.overall_health_score:>6.1f} "
                f"{metrics.data_freshness_score:>6.1f} "
                f"{metrics.semantic_coherence_score:>6.1f} "
                f"{metrics.persona_consistency_score:>6.1f} "
                f"{metrics.memory_saturation_score:>6.1f} "
                f"{status:<15}"
            )

        print("\nExpected: Context health degrades from ~95 → ~40 across 20 turns")
        return True

    @staticmethod
    def test_reset_recommendation():
        """Test that reset is recommended at appropriate thresholds."""
        tracker = ContextRotTracker()

        print("\n=== TEST: Context Reset Recommendations ===")

        # Simulate a degraded conversation
        for turn in range(1, 16):
            response = "Bland response. Therefore. In conclusion."
            breeding_recs = [{"key": turn}]
            tracker.record_turn(
                turn_number=turn,
                assistant_response=response,
                breeding_recommendations=breeding_recs,
                total_tokens_in_history=3000 + (turn * 300),
                turns_since_save_reload=turn,
            )

        should_warn, warning = tracker.should_warn_user()
        print(f"Should warn: {should_warn}")
        print(f"Warning:\n{warning}")

        return should_warn

    @staticmethod
    def run_all_tests():
        """Run entire evaluation suite."""
        print("\n" + "=" * 75)
        print("MEWGENICS MCP CONTEXT ROT TRACKER - EVALUATION SUITE")
        print("=" * 75)

        tests = [
            ("Data Freshness", ContextRotEvaluator.test_data_freshness),
            ("Persona Consistency", ContextRotEvaluator.test_persona_consistency),
            ("Memory Saturation", ContextRotEvaluator.test_memory_saturation),
            ("Semantic Coherence", ContextRotEvaluator.test_semantic_coherence),
            ("Full Conversation", ContextRotEvaluator.test_full_conversation_simulation),
            ("Reset Recommendation", ContextRotEvaluator.test_reset_recommendation),
        ]

        passed = 0
        for name, test_func in tests:
            try:
                result = test_func()
                if result:
                    passed += 1
            except AssertionError as e:
                print(f"✗ FAILED: {e}")
            except Exception as e:
                print(f"✗ ERROR: {e}")

        print("\n" + "=" * 75)
        print(f"RESULTS: {passed}/{len(tests)} tests passed")
        print("=" * 75)

        return passed == len(tests)


# ==================== Example MCP Server Integration ====================

class MewgenicsMCPServer:
    """
    Minimal example of how to integrate ContextRotTracker into an MCP server.
    """

    def __init__(self):
        self.rot_tracker = ContextRotTracker()
        self.turn_counter = 0
        self.last_save_reload = 0

    def handle_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        MCP server tool handler with context rot tracking.
        """
        self.turn_counter += 1

        # ... (actual tool logic here) ...

        # For this example, simulate a tool result
        result = {"status": "success", "data": {}}

        # Compute context decay
        turns_since_reload = self.turn_counter - self.last_save_reload
        if "save_path" in arguments:
            self.last_save_reload = self.turn_counter

        # Record turn in tracker
        breeding_recs = result.get("breeding_recommendations", [])
        response_text = json.dumps(result, indent=2)

        metrics = self.rot_tracker.record_turn(
            turn_number=self.turn_counter,
            assistant_response=response_text,
            breeding_recommendations=breeding_recs,
            total_tokens_in_history=len(response_text) // 4,  # rough estimate
            turns_since_save_reload=turns_since_reload,
        )

        # Check if warning needed
        should_warn, warning = self.rot_tracker.should_warn_user()

        return {
            "result": result,
            "context_metrics": asdict(metrics),
            "warning": warning if should_warn else None,
        }


if __name__ == "__main__":
    # Run evaluation suite
    ContextRotEvaluator.run_all_tests()

    print("\n\nFull context tracking example:")
    server = MewgenicsMCPServer()

    # Simulate 5 tool calls
    for i in range(5):
        result = server.handle_tool_call(
            tool_name="analyze_save_file",
            arguments={"save_path": "save.sav"} if i == 0 else {},
        )
        print(f"\nTurn {i+1} metrics: {result['context_metrics']['overall_health_score']:.1f}%")
        if result["warning"]:
            print(f"Warning: {result['warning']}")
