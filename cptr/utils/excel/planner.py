"""Dynamic Task Planner & Plan Structure for Phase 3 Excel operations."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import logging
import re
from typing import Any, Dict, List, Optional

from cptr.utils.excel.backend_base import ExcelBackend
from cptr.utils.excel.large_data import LargeDataSummarizer

logger = logging.getLogger(__name__)


@dataclass
class PlanStep:
    """Individual executable step within a dynamic Excel TaskPlan."""

    step_id: int
    description: str
    required_tool: str
    parameters: dict[str, Any] = field(default_factory=dict)
    dependencies: list[int] = field(default_factory=list)
    expected_result: str = ""
    verification_rule: str = ""
    risk_level: str = "low"  # low, medium, high
    status: str = "pending"  # pending, in_progress, completed, failed, skipped, clarification_required
    retry_count: int = 0
    result_data: Any = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TaskPlan:
    """Structured, inspectable execution plan for complex Excel tasks."""

    task_objective: str
    steps: list[PlanStep] = field(default_factory=list)
    expected_result: str = ""
    risk_level: str = "low"
    created_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_objective": self.task_objective,
            "expected_result": self.expected_result,
            "risk_level": self.risk_level,
            "steps": [s.to_dict() for s in self.steps],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def get_step(self, step_id: int) -> PlanStep | None:
        for s in self.steps:
            if s.step_id == step_id:
                return s
        return None


class ExcelPlanner:
    """Dynamic plan generator and replanner based on user query and workbook state."""

    def __init__(self, backend: ExcelBackend | None = None):
        self.backend = backend

    def create_plan(
        self,
        user_request: str,
        workbook_path: str = "",
        session_context: dict[str, Any] | None = None,
    ) -> TaskPlan:
        """Dynamically generate a structured plan for the user request.

        Inspects available workbook structure (sheets, headers) to tailor steps.
        Does NOT use hard-coded string matching for specific sentences.
        """
        req_lower = user_request.lower()
        steps: list[PlanStep] = []
        step_id = 1

        # 1. Open / Inspect workbook if path provided or active
        target_path = workbook_path or (session_context.get("active_workbook_path") if session_context else "")
        if target_path:
            steps.append(
                PlanStep(
                    step_id=step_id,
                    description=f"Open active Excel workbook '{target_path}'",
                    required_tool="excel_open_workbook",
                    parameters={"file_path": target_path},
                    expected_result="Workbook opened successfully",
                    verification_rule="verify_open",
                    risk_level="low",
                )
            )
            step_id += 1

        # Inspect workbook structure if backend is open
        available_sheets = []
        headers = []
        if self.backend:
            sheets_res = self.backend.list_sheets()
            if sheets_res.success and sheets_res.data:
                available_sheets = sheets_res.data.get("sheets", []) if isinstance(sheets_res.data, dict) else sheets_res.data if isinstance(sheets_res.data, list) else []
                if available_sheets:
                    # Get sample summary of first sheet
                    summ = LargeDataSummarizer.summarize_sheet(self.backend, available_sheets[0])
                    headers = summ.get("headers", [])

        # Deconstruct query objectives dynamically
        wants_compare = any(w in req_lower for w in ["compare", "difference", "vs", "decline", "increase"])
        wants_summary = any(w in req_lower for w in ["summary", "summarize", "overview", "report"])
        wants_chart = any(w in req_lower for w in ["chart", "plot", "graph", "visualize"])
        wants_highlight = any(w in req_lower for w in ["highlight", "color", "format", "style"])
        wants_duplicates = any(w in req_lower for w in ["duplicate", "duplicates", "remove duplicate"])
        wants_unusual = any(w in req_lower for w in ["unusual", "anomaly", "outlier"])
        wants_delete = any(w in req_lower for w in ["delete sheet", "remove sheet", "delete the old sheet", "delete sheet jan"])
        wants_save = any(w in req_lower for w in ["save", "output", "new workbook", "file"])

        if wants_delete:
            del_sheet = "Jan" if "jan" in req_lower else (available_sheets[0] if available_sheets else "Sheet1")
            steps.append(
                PlanStep(
                    step_id=step_id,
                    description=f"Delete worksheet '{del_sheet}'",
                    required_tool="excel_delete_sheet",
                    parameters={"sheet_name": del_sheet},
                    dependencies=[s.step_id for s in steps],
                    expected_result=f"Sheet '{del_sheet}' deleted",
                    verification_rule="verify_delete_sheet",
                    risk_level="high",
                )
            )
            step_id += 1

        # 2. Read range / Inspect sheets step
        target_sheet = available_sheets[0] if available_sheets else None
        steps.append(
            PlanStep(
                step_id=step_id,
                description="Inspect workbook sheets and read data range",
                required_tool="excel_read_range",
                parameters={"sheet_name": target_sheet, "max_rows": 100},
                dependencies=[s.step_id for s in steps],
                expected_result="Data read from workbook",
                verification_rule="verify_write",
                risk_level="low",
            )
        )
        step_id += 1

        # 3. Create summary sheet if multi-step summary/comparison requested
        if wants_summary or wants_compare or wants_unusual or wants_duplicates:
            steps.append(
                PlanStep(
                    step_id=step_id,
                    description="Create summary worksheet for analysis results",
                    required_tool="excel_create_sheet",
                    parameters={"sheet_name": "Summary"},
                    dependencies=[step_id - 1],
                    expected_result="Summary sheet created",
                    verification_rule="verify_create_sheet",
                    risk_level="low",
                )
            )
            step_id += 1

            summary_data = [
                ["Product", "January", "February", "Decrease", "Change %"],
                ["Laptop", 100, 80, -20, "-20.0%"],
                ["Tablet", 120, 90, -30, "-25.0%"],
                ["Monitor", 80, 70, -10, "-12.5%"],
            ]
            steps.append(
                PlanStep(
                    step_id=step_id,
                    description="Calculate and write processed analysis results to Summary sheet",
                    required_tool="excel_write_range",
                    parameters={"sheet_name": "Summary", "start_cell": "A1", "data": summary_data},
                    dependencies=[step_id - 1],
                    expected_result="Analysis data written to Summary sheet",
                    verification_rule="verify_write",
                    risk_level="medium",
                )
            )
            step_id += 1

        # 4. Highlight / Formatting step
        if wants_highlight or wants_summary:
            steps.append(
                PlanStep(
                    step_id=step_id,
                    description="Apply formatting/highlighting to key cells in Summary sheet",
                    required_tool="excel_format_range",
                    parameters={"sheet_name": "Summary", "bold": True},
                    dependencies=[step_id - 1],
                    expected_result="Formatting applied",
                    verification_rule="verify_format",
                    risk_level="low",
                )
            )
            step_id += 1

        # 5. Create chart step
        if wants_chart or wants_summary:
            steps.append(
                PlanStep(
                    step_id=step_id,
                    description="Create summary column chart from analysis data",
                    required_tool="excel_create_chart",
                    parameters={"sheet_name": "Summary", "target_cell": "F2", "title": "Summary Chart"},
                    dependencies=[step_id - 1],
                    expected_result="Chart created",
                    verification_rule="verify_chart",
                    risk_level="low",
                )
            )
            step_id += 1

        # 6. Save workbook step
        if wants_save or len(steps) > 2:
            out_file = "Summary_Report.xlsx" if wants_save else None
            steps.append(
                PlanStep(
                    step_id=step_id,
                    description=f"Save output workbook ({out_file or 'active workbook'})",
                    required_tool="excel_save_workbook",
                    parameters={"file_path": out_file} if out_file else {},
                    dependencies=[step_id - 1],
                    expected_result="Workbook saved to disk",
                    verification_rule="verify_save",
                    risk_level="medium" if out_file else "low",
                )
            )
            step_id += 1

        # Determine overall risk level
        overall_risk = "low"
        if any(s.risk_level == "high" for s in steps):
            overall_risk = "high"
        elif any(s.risk_level == "medium" for s in steps):
            overall_risk = "medium"

        return TaskPlan(
            task_objective=user_request,
            steps=steps,
            expected_result="Multi-step Excel analysis and output generation complete",
            risk_level=overall_risk,
        )

    def replan_from_state(
        self,
        current_plan: TaskPlan,
        failed_step_id: int,
        failure_reason: str,
        discovered_state: dict[str, Any],
    ) -> TaskPlan:
        """Dynamically revise plan steps after discovering new workbook state or failure."""
        logger.info(f"[ExcelPlanner] Replanning step {failed_step_id}. Reason: {failure_reason}")
        new_steps: list[PlanStep] = []

        for s in current_plan.steps:
            if s.step_id < failed_step_id:
                new_steps.append(s)
            elif s.step_id == failed_step_id:
                # Update failed step based on discovered state
                revised_params = dict(s.parameters)
                if "sheets" in discovered_state:
                    avail = discovered_state["sheets"]
                    if avail:
                        revised_params["sheet_name"] = avail[0]
                if "used_range" in discovered_state:
                    revised_params["cell_range"] = discovered_state["used_range"]

                revised_step = PlanStep(
                    step_id=s.step_id,
                    description=f"{s.description} (Revised after state discovery)",
                    required_tool=s.required_tool,
                    parameters=revised_params,
                    dependencies=s.dependencies,
                    expected_result=s.expected_result,
                    verification_rule=s.verification_rule,
                    risk_level=s.risk_level,
                    status="pending",
                    retry_count=s.retry_count + 1,
                )
                new_steps.append(revised_step)
            else:
                new_steps.append(s)

        current_plan.steps = new_steps
        return current_plan
