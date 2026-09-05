"""
core/agi_planner.py — System 2 Autonomous Goal Planner & Execution Loop for ANSH

Implements multi-step task decomposition, step-by-step tool execution,
self-reflection verification, error recovery, and UI/Voice status updates.
"""
from __future__ import annotations

import json
import time
import uuid
import traceback
from typing import Dict, Any, List, Optional, Callable

from core.task_llm import call_task_llm
from core.agi_memory import AGIMemoryEngine


class AGIPlanner:
    def __init__(self, memory_engine: Optional[AGIMemoryEngine] = None):
        self.memory = memory_engine or AGIMemoryEngine()

    def decompose_goal(self, goal: str, available_tools_summary: str = "") -> Dict[str, Any]:
        """
        Decomposes a complex goal into a structured sequence of executable steps.
        """
        system_prompt = (
            "You are the System 2 Reasoning Engine for ANSH, an AGI Personal Assistant.\n"
            "Break down the user's high-level goal into a clear, sequential plan of 2 to 6 steps.\n"
            "Available tools include: web_search, file_processor, open_app, send_message, reminder, "
            "computer_settings, computer_control, weather_report, flight_finder, youtube_video, "
            "game_updater, code_helper, dev_agent, desktop_control, browser_control, file_controller.\n"
            "Return JSON in this format:\n"
            "{\n"
            '  "goal_title": "Short title of the goal",\n'
            '  "steps": [\n'
            '    {\n'
            '      "step_number": 1,\n'
            '      "action_name": "tool_or_action_name",\n'
            '      "description": "Human-readable step description",\n'
            '      "parameters": {"param1": "val1"},\n'
            '      "expected_outcome": "Description of success criteria"\n'
            '    }\n'
            '  ]\n'
            "}\n"
        )

        user_prompt = f"Goal to accomplish: {goal}\n"
        if available_tools_summary:
            user_prompt += f"Context/Tools: {available_tools_summary}\n"

        try:
            raw = call_task_llm(prompt=user_prompt, system=system_prompt, json_mode=True, temperature=0.3)
            plan = json.loads(raw)
            if "steps" not in plan or not isinstance(plan["steps"], list):
                raise ValueError("Invalid plan structure returned by LLM.")
            return plan
        except Exception as e:
            print(f"[AGIPlanner] Plan decomposition failed ({e}), creating single fallback step.")
            return {
                "goal_title": goal[:40],
                "steps": [
                    {
                        "step_number": 1,
                        "action_name": "direct_execution",
                        "description": goal,
                        "parameters": {"goal": goal},
                        "expected_outcome": "Direct execution of goal",
                    }
                ],
            }

    def reflect_and_adjust(
        self,
        goal: str,
        failed_step: Dict[str, Any],
        error_message: str,
        completed_steps: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        Self-reflection loop: Analyzes step failure and recommends an alternative step or recovery action.
        """
        system_prompt = (
            "You are the Reflection Engine for ANSH.\n"
            "A step in an autonomous plan failed. Analyze the error and provide a recovery step or fallback.\n"
            "Return JSON in this format:\n"
            "{\n"
            '  "recovery_action": "retry|skip|alternate_action|abort",\n'
            '  "replacement_step": {\n'
            '    "action_name": "action_name",\n'
            '    "description": "Updated step description",\n'
            '    "parameters": {}\n'
            '  },\n'
            '  "reason": "Brief explanation of recovery strategy"\n'
            "}\n"
        )

        user_prompt = (
            f"Overall Goal: {goal}\n"
            f"Failed Step: {json.dumps(failed_step)}\n"
            f"Error Message: {error_message}\n"
            f"Completed Steps: {json.dumps(completed_steps)}\n"
        )

        try:
            raw = call_task_llm(prompt=user_prompt, system=system_prompt, json_mode=True, temperature=0.2)
            return json.loads(raw)
        except Exception as e:
            print(f"[AGIPlanner] Reflection failed ({e}).")
            return None

    def execute_goal(
        self,
        goal: str,
        action_dispatcher: Callable[[str, Dict[str, Any]], Any],
        status_callback: Optional[Callable[[str, str, int, int], None]] = None,
    ) -> Dict[str, Any]:
        """
        Executes a goal end-to-end with planning, step execution, self-reflection, and state updating.

        status_callback signature: status_callback(goal_id, message, current_step, total_steps)
        """
        goal_id = f"goal_{uuid.uuid4().hex[:8]}"
        plan = self.decompose_goal(goal)
        steps = plan.get("steps", [])
        total_steps = len(steps)
        completed_steps = []

        if status_callback:
            status_callback(goal_id, f"Plan created: '{plan.get('goal_title')}' ({total_steps} steps)", 0, total_steps)

        self.memory.save_goal_state(
            goal_id=goal_id,
            goal_title=plan.get("goal_title", goal),
            steps=steps,
            current_step=0,
            status="in_progress",
        )

        final_results = []

        for idx, step in enumerate(steps):
            step_num = idx + 1
            action_name = step.get("action_name", "")
            params = step.get("parameters", {})
            desc = step.get("description", f"Step {step_num}")

            if status_callback:
                status_callback(goal_id, f"Executing Step {step_num}/{total_steps}: {desc}", step_num, total_steps)

            success = False
            result_data = None
            error_str = ""

            try:
                result_data = action_dispatcher(action_name, params)
                success = True
            except Exception as ex:
                error_str = f"{ex}\n{traceback.format_exc()}"
                print(f"[AGIPlanner] Error on Step {step_num} ({action_name}): {ex}")

            if not success:
                # Run self-reflection loop
                reflection = self.reflect_and_adjust(
                    goal=goal,
                    failed_step=step,
                    error_message=error_str,
                    completed_steps=completed_steps,
                )

                if reflection:
                    rec_action = reflection.get("recovery_action", "abort")
                    reason = reflection.get("reason", "")
                    if status_callback:
                        status_callback(goal_id, f"Step {step_num} failed. Strategy: {rec_action} ({reason})", step_num, total_steps)

                    if rec_action == "retry":
                        try:
                            result_data = action_dispatcher(action_name, params)
                            success = True
                        except Exception as ex2:
                            error_str = str(ex2)

                    elif rec_action == "alternate_action" and reflection.get("replacement_step"):
                        alt_step = reflection["replacement_step"]
                        alt_action = alt_step.get("action_name", "")
                        alt_params = alt_step.get("parameters", {})
                        try:
                            result_data = action_dispatcher(alt_action, alt_params)
                            success = True
                        except Exception as ex3:
                            error_str = str(ex3)

            step_record = {
                "step_number": step_num,
                "action_name": action_name,
                "description": desc,
                "success": success,
                "result": str(result_data) if result_data is not None else "",
                "error": error_str if not success else "",
            }
            completed_steps.append(step_record)
            final_results.append(step_record)

            self.memory.save_goal_state(
                goal_id=goal_id,
                goal_title=plan.get("goal_title", goal),
                steps=steps,
                current_step=step_num,
                status="in_progress" if step_num < total_steps else "completed",
            )

        overall_success = all(s["success"] for s in completed_steps)
        final_status = "completed" if overall_success else "partial_success"

        self.memory.save_goal_state(
            goal_id=goal_id,
            goal_title=plan.get("goal_title", goal),
            steps=steps,
            current_step=total_steps,
            status=final_status,
        )

        if status_callback:
            status_msg = "Goal completed successfully!" if overall_success else "Goal finished with some step warnings."
            status_callback(goal_id, status_msg, total_steps, total_steps)

        return {
            "goal_id": goal_id,
            "goal_title": plan.get("goal_title", goal),
            "status": final_status,
            "completed_steps": completed_steps,
        }
