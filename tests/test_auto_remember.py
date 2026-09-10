"""
tests/test_auto_remember.py — Verification Suite for ANSH Autonomous Continuous Memory
"""
import json
import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from memory.auto_remember import AutoRememberEngine
from memory.memory_service import MemoryService
from memory.memory_manager import format_memory_for_prompt
from actions.memory_actions import search_memory_action


def test_autonomous_memory():
    print("==================================================")
    print("      TESTING ANSH CONTINUOUS MEMORY ENGINE       ")
    print("==================================================")

    auto_mem = AutoRememberEngine.get_instance()
    mem_svc = MemoryService.get_instance()

    test_turns = [
        ("mujhe cold coffee bahut pasand hai", "Sahi hai boss! Cold coffee to meri bhi pasand hai."),
        ("mera favorite color dark blue hai", "Dark blue! Badass choice, bilkul royal look deta hai."),
        ("main ek portfolio website bana rha hoon", "Superb! Modern portfolio banayenge, full animation ke sath."),
        ("mera dost Rohan software engineer hai", "Great! Developer dost humesha kaam aate hain."),
        ("yaad rakhna ki kal subah 7 baje meeting hai", "Done! 7 baje ki meeting yaad rakhunga boss."),
        ("mere paas MacBook Air M2 hai", "Nice machine! Smooth performance milta hoga.")
    ]

    print("\n[Step 1] Ingesting conversational turns synchronously for testing...")
    for user_text, assistant_response in test_turns:
        # Ingest directly
        auto_mem.append_conversation_turn("user", user_text)
        auto_mem.append_conversation_turn("ansh", assistant_response)
        facts = auto_mem.extract_and_store_facts(user_text)
        print(f"User: '{user_text}' -> Extracted {len(facts)} facts: {facts}")

    print("\n[Step 2] Verifying episodic storage files...")
    storage_dir = BASE_DIR / "memory" / "storage"
    conv_md = storage_dir / "conversations.md"
    conv_jsonl = storage_dir / "conversations.jsonl"

    assert conv_md.exists(), "conversations.md was not created!"
    assert conv_jsonl.exists(), "conversations.jsonl was not created!"

    md_content = conv_md.read_text(encoding="utf-8")
    assert "cold coffee" in md_content, "Cold coffee not found in conversations.md!"
    assert "Dark Blue" in md_content or "dark blue" in md_content, "Dark blue not found in conversations.md!"
    print("✅ Episodic Markdown & JSONL logs verified successfully!")

    print("\n[Step 3] Verifying structured Markdown memories...")
    pref_md = storage_dir / "preferences.md"
    proj_md = storage_dir / "projects.md"
    rel_md = storage_dir / "relationships.md"
    notes_md = storage_dir / "notes.md"

    assert pref_md.exists(), "preferences.md does not exist!"
    assert proj_md.exists(), "projects.md does not exist!"
    assert rel_md.exists(), "relationships.md does not exist!"
    assert notes_md.exists(), "notes.md does not exist!"

    pref_txt = pref_md.read_text(encoding="utf-8")
    proj_txt = proj_md.read_text(encoding="utf-8")
    rel_txt = rel_md.read_text(encoding="utf-8")
    notes_txt = notes_md.read_text(encoding="utf-8")

    assert "Cold Coffee" in pref_txt or "cold coffee" in pref_txt, "Cold coffee missing in preferences.md!"
    assert "Dark Blue" in pref_txt or "dark blue" in pref_txt, "Dark blue missing in preferences.md!"
    assert "Portfolio Website" in proj_txt or "portfolio website" in proj_txt, "Portfolio website missing in projects.md!"
    assert "Rohan" in rel_txt, "Rohan missing in relationships.md!"
    assert "7 baje meeting" in notes_txt, "Meeting note missing in notes.md!"
    assert "MacBook Air" in notes_txt or "macbook air" in notes_txt.lower(), "MacBook gadget missing in notes.md!"
    print("✅ Structured Markdown memories (Preferences, Projects, Relationships, Notes) verified!")

    print("\n[Step 4] Verifying prompt injection formatting...")
    prompt_mem = format_memory_for_prompt()
    print("--- PROMPT MEMORY OUTPUT ---")
    print(prompt_mem)
    print("----------------------------")

    assert "CORE PREFERENCES" in prompt_mem, "CORE PREFERENCES header missing in prompt memory!"
    assert "ACTIVE PROJECTS" in prompt_mem, "ACTIVE PROJECTS header missing in prompt memory!"
    assert "KEY RELATIONSHIPS" in prompt_mem, "KEY RELATIONSHIPS header missing in prompt memory!"
    assert "SAVED NOTES" in prompt_mem, "SAVED NOTES header missing in prompt memory!"
    assert "RECENT CONVERSATION HISTORY" in prompt_mem, "RECENT CONVERSATION HISTORY missing in prompt memory!"
    print("✅ Full prompt memory injection verified with all categories!")

    print("\n[Step 5] Verifying search across structured memory & conversational dialogue...")
    res_pref = search_memory_action({"query": "coffee"})
    print("Search 'coffee':\n", res_pref)
    assert "coffee" in res_pref.lower(), "Search failed for coffee!"

    res_proj = search_memory_action({"query": "portfolio"})
    print("\nSearch 'portfolio':\n", res_proj)
    assert "portfolio" in res_proj.lower(), "Search failed for portfolio!"

    res_conv = search_memory_action({"query": "meeting"})
    print("\nSearch 'meeting':\n", res_conv)
    assert "meeting" in res_conv.lower(), "Search failed for meeting!"
    print("✅ Search memory action verified across both structured storage and past conversations!")

    print("\n==================================================")
    print("   ALL AUTONOMOUS MEMORY TESTS PASSED 100%!       ")
    print("==================================================")


if __name__ == "__main__":
    test_autonomous_memory()
