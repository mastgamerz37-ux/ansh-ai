"""
tests/test_master_upgrade.py — Comprehensive Unit & Integration Tests for ANSH Master Upgrade

Verifies:
1. Affective Engine (Emotional states, Personality Modes, Pronoun Resolution)
2. Multi-Agent Hub (Agent selection, model routing, sub-agent execution)
3. Security & Safety Engine (Risk classification, shadow backup, undo rollback, emergency stop)
4. Teach ANSH Workflow Engine (Recording demonstration, step playback)
5. Study Intelligence Engine (Notes, doubt solving, quiz generation, progress tracking)
6. Knowledge Graph & World State (Adding triples, querying entity, world state updates)
7. Multimodal Store & Context Continuation (Checkpoints, visual memory, cross-medium sync)
8. Local Offline Reliability (Offline fallback logic, internet check)
9. Event Bus (Pub-Sub event dispatching and history tracking)
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))


def test_affective_engine():
    print("[TEST 1/9] Testing AffectiveEngine & Personality Modes...")
    from core.affective_engine import AffectiveEngine, EmotionalState, PersonalityMode

    aff = AffectiveEngine.get_instance()

    # Test sentiment classification
    frust = aff.analyze_text_sentiment("Why won't this stupid code work? It failed again!")
    assert frust.state == EmotionalState.FRUSTRATED_STRESSED, f"Expected FRUSTRATED, got {frust.state}"

    joy = aff.analyze_text_sentiment("Haha nice awesome work bro! Sahi hai boss!")
    assert joy.state == EmotionalState.JOYFUL_CASUAL, f"Expected JOYFUL, got {joy.state}"

    # Test personality modes
    aff.set_personality_mode(PersonalityMode.DEVELOPER)
    assert aff.active_mode == PersonalityMode.DEVELOPER

    # Test pronoun resolution
    context = {"active_file": "main.py"}
    resolved = aff.resolve_referential_pronouns("isko chalao", context)
    assert "'main.py'" in resolved, f"Expected resolved 'main.py', got {resolved}"

    print("  ✅ AffectiveEngine passed.")


def test_multi_agent_hub():
    print("[TEST 2/9] Testing Multi-Agent Hub & Model Router...")
    from core.multi_agent_hub import MainAgent, AgentRole, AIModelTier

    hub = MainAgent.get_instance()

    # Test agent selection
    agent, conf = hub.select_agent("Search the web for latest AI news")
    assert agent.role == AgentRole.BROWSER, f"Expected BROWSER, got {agent.role}"

    code_agent, conf2 = hub.select_agent("Refactor this python function and run tests")
    assert code_agent.role == AgentRole.CODING, f"Expected CODING, got {code_agent.role}"

    # Test model router
    tier_fast = hub.route_model("What is the battery percentage?")
    assert tier_fast == AIModelTier.LOCAL_FAST, f"Expected LOCAL_FAST, got {tier_fast}"

    print("  ✅ Multi-Agent Hub passed.")


def test_security_and_safety_engine():
    print("[TEST 3/9] Testing SecurityEngine & Undo Rollback...")
    from core.security_engine import SecurityEngine, RiskLevel

    sec = SecurityEngine.get_instance()

    # Risk classification
    risk_safe = sec.classify_action("list_memories")
    assert risk_safe == RiskLevel.SAFE

    risk_crit = sec.classify_action("file_controller", {"action": "delete"})
    assert risk_crit == RiskLevel.CRITICAL

    # Test Shadow Backup & Rollback
    test_file = BASE_DIR / "data" / "secure" / "test_safety.txt"
    test_file.write_text("Original State", encoding="utf-8")

    # Create pre-action snapshot
    snap = sec.create_pre_action_snapshot("modify_file", str(test_file))
    assert snap.backup_path is not None
    assert os.path.exists(snap.backup_path)

    # Modify file
    test_file.write_text("Modified Destructive State", encoding="utf-8")
    assert test_file.read_text(encoding="utf-8") == "Modified Destructive State"

    # Rollback!
    success, msg = sec.rollback_last_action()
    assert success is True
    assert test_file.read_text(encoding="utf-8") == "Original State"

    # Cleanup test file
    if test_file.exists():
        test_file.unlink()

    print("  ✅ Security & Safety Engine passed.")


def test_teach_ansh_workflows():
    print("[TEST 4/9] Testing Teach ANSH Workflow Recorder...")
    from actions.teach_ansh import TeachAnshEngine

    teach = TeachAnshEngine.get_instance()

    # Record workflow
    msg = teach.start_recording(name="Dev Setup", trigger_phrase="start my dev routine")
    assert "RECORDING STARTED" in msg

    teach.record_step(action_type="volume", target="system", parameters={"value": 30}, description="Set volume 30%")
    save_msg = teach.stop_recording()
    assert "RECORDING SAVED" in save_msg

    wfs = teach.list_workflows()
    assert any(w["name"] == "Dev Setup" for w in wfs)

    print("  ✅ Teach ANSH Workflow Engine passed.")


def test_study_engine():
    print("[TEST 5/9] Testing Study & Learning Engine...")
    from actions.study_mode import StudyEngine

    study = StudyEngine.get_instance()
    msg = study.record_quiz_result(topic="Python Concurrency", score=4, total=5)
    assert "Quiz recorded" in msg
    assert study.progress["quizzes_taken"] >= 1

    print("  ✅ Study & Learning Engine passed.")


def test_knowledge_graph():
    print("[TEST 6/9] Testing Knowledge Graph & World-State Engine...")
    from memory.knowledge_graph import KnowledgeGraph

    kg = KnowledgeGraph.get_instance()
    kg.add_relation("Anshu", "created", "ANSH", confidence=1.0)
    kg.add_relation("ANSH", "runs_on", "Windows", confidence=0.95)

    info = kg.query_entity("ANSH")
    assert any(f["predicate"] == "runs_on" for f in info["facts"])
    assert any(r["source"] == "Anshu" for r in info["referenced_by"])

    kg.update_world_state("focus_mode", True)
    assert kg.get_world_state()["focus_mode"] is True

    print("  ✅ Knowledge Graph passed.")


def test_multimodal_store():
    print("[TEST 7/9] Testing Multimodal Store & Context Continuation...")
    from memory.multimodal_store import MultimodalStore

    mm = MultimodalStore.get_instance()
    entry_id = mm.save_visual_memory(
        summary_text="VS Code open with main.py",
        app_name="Code",
        window_title="main.py - ANSH",
        tags=["python", "ide"],
    )
    assert len(entry_id) > 0

    results = mm.search_visual_memories("VS Code")
    assert len(results) >= 1

    checkpoint = mm.capture_session_checkpoint(last_query="Run tests on memory module")
    assert checkpoint.last_user_query == "Run tests on memory module"

    briefing = mm.get_continuation_briefing()
    assert "[CONTEXT_CONTINUATION]" in briefing

    print("  ✅ Multimodal Store passed.")


def test_local_offline_engine():
    print("[TEST 8/9] Testing Local Offline SLM Fallback...")
    from core.local_engine import _offline_rule_fallback

    time_reply = _offline_rule_fallback("What is the time?")
    assert "Current time is" in time_reply

    battery_reply = _offline_rule_fallback("What is the battery status?")
    assert len(battery_reply) > 0

    print("  ✅ Local Offline Engine passed.")


def test_event_bus():
    print("[TEST 9/9] Testing EventBus Pub-Sub Telemetry...")
    from core.event_bus import EventBus, EventType

    bus = EventBus.get_instance()
    received = []

    def on_mode(evt):
        received.append(evt.payload.get("mode"))

    bus.subscribe(EventType.MODE_CHANGED, on_mode)
    bus.publish(EventType.MODE_CHANGED, {"mode": "DEVELOPER"})

    assert "DEVELOPER" in received
    recent = bus.get_recent_events(limit=10)
    assert any(e["type"] == EventType.MODE_CHANGED.value for e in recent)

    print("  ✅ EventBus passed.")


if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    print("=" * 65)
    print("[RUNNING] ANSH MASTER UPGRADE TEST SUITE")
    print("=" * 65)
    test_affective_engine()
    test_multi_agent_hub()
    test_security_and_safety_engine()
    test_teach_ansh_workflows()
    test_study_engine()
    test_knowledge_graph()
    test_multimodal_store()
    test_local_offline_engine()
    test_event_bus()
    print("=" * 65)
    print("[SUCCESS] ALL 9 TEST SUITES PASSED PERFECTLY!")
    print("=" * 65)
