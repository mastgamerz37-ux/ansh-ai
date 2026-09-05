"""
tests/test_agi_engine.py — Unit Tests for ANSH AGI Engine (Planner, Memory, Proactive Brain)
"""
import unittest
import json
import tempfile
import shutil
from pathlib import Path

from core.agi_memory import AGIMemoryEngine
from core.agi_planner import AGIPlanner
from core.agi_proactive import AGIProactiveBrain


class TestAGIEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.memory_engine = AGIMemoryEngine(data_dir=self.temp_dir)
        self.planner = AGIPlanner(memory_engine=self.memory_engine)
        self.proactive_brain = AGIProactiveBrain(memory_engine=self.memory_engine)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_goal_state_persistence(self):
        goal_id = "test_goal_123"
        steps = [
            {"step_number": 1, "action_name": "web_search", "description": "Search AI news"},
            {"step_number": 2, "action_name": "file_processor", "description": "Save summary"},
        ]
        self.memory_engine.save_goal_state(
            goal_id=goal_id,
            goal_title="Research AI News",
            steps=steps,
            current_step=1,
            status="in_progress",
        )

        state = self.memory_engine.get_goal_state(goal_id)
        self.assertIsNotNone(state)
        self.assertEqual(state["title"], "Research AI News")
        self.assertEqual(state["current_step"], 1)

        active = self.memory_engine.get_all_active_goals()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["goal_id"], goal_id)

        self.memory_engine.clear_goal_state(goal_id)
        self.assertIsNone(self.memory_engine.get_goal_state(goal_id))

    def test_planner_decompose(self):
        plan = self.planner.decompose_goal("Find tech news and save to report")
        self.assertIn("steps", plan)
        self.assertTrue(len(plan["steps"]) >= 1)

    def test_planner_execution_loop(self):
        executed_actions = []

        def mock_dispatcher(action_name, params):
            executed_actions.append(action_name)
            if action_name == "fail_test":
                raise RuntimeError("Simulated failure")
            return f"Success: {action_name}"

        status_logs = []

        def mock_status_callback(goal_id, msg, current_step, total_steps):
            status_logs.append((current_step, msg))

        # Run planner execution
        res = self.planner.execute_goal(
            goal="Simple mock task",
            action_dispatcher=mock_dispatcher,
            status_callback=mock_status_callback,
        )

        self.assertIn("status", res)
        self.assertTrue(len(executed_actions) >= 1)

    def test_proactive_brain_prompt(self):
        prompt = self.proactive_brain.build_enhanced_prompt(
            clipboard_text="https://github.com/mastgamerz37-ux/ansh-ai",
            system_telemetry={"cpu_percent": 15, "ram_percent": 45},
        )
        self.assertIn("PROACTIVE_CHECK_2.0", prompt)
        self.assertIn("Anshu", prompt)
        self.assertIn("CPU 15%", prompt)


    def test_all_action_operations(self):
        actions_to_test = [
            "save_file", "edit_file", "create_file", "open_app", "make_new",
            "web_search", "code_helper", "dev_agent", "browser_control"
        ]
        results = []
        for act in actions_to_test:
            res = self.planner.execute_goal(
                goal=f"Test {act} operation",
                action_dispatcher=lambda name, params: f"Executed {name}",
            )
            results.append(res["status"])
        self.assertTrue(all(s in ("completed", "partial_success") for s in results))


if __name__ == "__main__":
    unittest.main()
