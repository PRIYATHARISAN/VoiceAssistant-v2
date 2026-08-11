"""Phase 3 Reliable Excel Task Execution Engine.

Integrates Planning, Empirical Verification, Conservative Recovery, Replanning,
Backup/Rollback, Safety Controls, and Audit Logging with the authoritative cptr tool architecture.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from cptr.utils.excel.audit_log import ExcelAuditLogger
from cptr.utils.excel.backup import BackupManager
from cptr.utils.excel.backend_base import ExcelBackend, ExcelResult
from cptr.utils.excel.large_data import LargeDataSummarizer
from cptr.utils.excel.planner import ExcelPlanner, PlanStep, TaskPlan
from cptr.utils.excel.recovery import ExcelRecoveryHandler, RecoveryAction
from cptr.utils.excel.safety import SafetyManager
from cptr.utils.excel.session import ExcelSession, get_excel_session
from cptr.utils.excel.verifier import ExcelVerifier, VerificationResult

logger = logging.getLogger(__name__)


class ReliableExcelExecutor:
    """Orchestrates reliable Excel execution without replacing authoritative cptr loop."""

    def __init__(self, context: dict[str, Any] | None = None, max_retries: int = 3):
        self.context: dict[str, Any] = context or {}
        self.max_retries: int = max_retries
        self.session: ExcelSession = get_excel_session(self.context)
        self.audit_logger: ExcelAuditLogger = ExcelAuditLogger(session_id=self.session.session_id)
        self.safety_manager: SafetyManager = SafetyManager()
        self.backup_manager: BackupManager | None = None

    async def execute_task(
        self,
        user_request: str,
        workbook_path: str = "",
        user_confirmed: bool = False,
    ) -> dict[str, Any]:
        """Execute a natural-language Excel request with planning, verification, and recovery."""
        from cptr.utils.tools import execute_tool

        t_start = time.time()
        self.audit_logger.log_request(user_request, workbook_path)

        # 1. Ambiguity & Safety Evaluation
        if self.safety_manager.is_ambiguous_request(user_request) and not user_confirmed:
            msg = (
                f"The request '{user_request}' is ambiguous. I will inspect the workbook first, "
                "but will ask for your confirmation before making any destructive changes."
            )
            self.audit_logger.log_final_result(False, msg, (time.time() - t_start) * 1000)
            return {
                "success": False,
                "status": "ambiguous_request",
                "message": msg,
                "requires_user_clarification": True,
            }

        # 2. Determine target workbook path & Initialize Backend
        target_path = workbook_path or self.session.active_workbook_path
        if target_path:
            self.session.ensure_backend(target_path, workspace=self.context.get("workspace", ""))

        backend = self.session.backend
        if not backend and target_path:
            # Try opening workbook tool
            res_open = await execute_tool("excel_open_workbook", {"file_path": target_path}, __context__=self.context)
            backend = self.session.backend

        # 3. Create Backup / Working Copy before FIRST mutation in multi-step task
        if target_path and os.path.exists(target_path):
            self.backup_manager = BackupManager(target_path, workspace=self.context.get("workspace", ""))
            working_path = self.backup_manager.create_working_copy()
            if working_path != target_path and os.path.exists(working_path):
                self.session.ensure_backend(working_path, workspace=self.context.get("workspace", ""))
                backend = self.session.backend

        # 4. Generate Dynamic Task Plan
        planner = ExcelPlanner(backend=backend)
        plan = planner.create_plan(user_request, workbook_path=self.session.active_workbook_path, session_context=self.context)
        self.audit_logger.log_plan(plan.to_dict())

        # 5. Execute Plan Steps
        verifier = ExcelVerifier(backend=backend) if backend else None
        recovery_handler = ExcelRecoveryHandler(backend=backend, max_retries=self.max_retries) if backend else None

        executed_steps: list[dict[str, Any]] = []

        for step in plan.steps:
            step.status = "in_progress"
            self.audit_logger.log_step_start(step.step_id, step.description, step.required_tool)

            # Check safety confirmation for destructive tools
            if self.safety_manager.requires_user_confirmation(step.required_tool, step.parameters, user_confirmed):
                step.status = "clarification_required"
                msg = f"Destructive operation '{step.required_tool}' requires explicit user confirmation."
                self.audit_logger.log_final_result(False, msg, (time.time() - t_start) * 1000)
                return {
                    "success": False,
                    "status": "confirmation_required",
                    "step_id": step.step_id,
                    "tool": step.required_tool,
                    "message": msg,
                    "requires_confirmation": True,
                }

            # Execute tool with bounded retries
            step_success = False
            tool_res_obj = None

            while step.retry_count <= self.max_retries and not step_success:
                t_tool_0 = time.time()
                tool_output_str = await execute_tool(step.required_tool, step.parameters, __context__=self.context)
                t_tool_ms = (time.time() - t_tool_0) * 1000

                # Parse ExcelResult JSON
                try:
                    res_dict = json.loads(tool_output_str)
                    tool_res_obj = ExcelResult(
                        success=res_dict.get("success", False),
                        operation=res_dict.get("operation", step.required_tool),
                        workbook=res_dict.get("workbook", ""),
                        sheet=res_dict.get("sheet", ""),
                        affected_range=res_dict.get("affected_range", ""),
                        message=res_dict.get("message", ""),
                        data=res_dict.get("data"),
                    )
                except Exception:
                    tool_res_obj = ExcelResult(success=True, operation=step.required_tool, message=tool_output_str)

                self.audit_logger.log_tool_execution(
                    step.step_id,
                    step.required_tool,
                    step.parameters,
                    res_dict if 'res_dict' in locals() else {"output": tool_output_str},
                    t_tool_ms,
                )

                # Empirical Verification
                if backend and verifier:
                    t_v_0 = time.time()
                    v_res = verifier.verify_operation(step.required_tool, step.parameters, tool_res_obj)
                    t_v_ms = (time.time() - t_v_0) * 1000
                    self.audit_logger.log_verification(
                        step.step_id,
                        v_res.check_type,
                        v_res.success,
                        v_res.message,
                        t_v_ms,
                    )

                    if tool_res_obj.success and v_res.success:
                        step_success = True
                        step.status = "completed"
                        step.result_data = v_res.actual or tool_res_obj.data
                        break
                elif tool_res_obj.success:
                    step_success = True
                    step.status = "completed"
                    step.result_data = tool_res_obj.data
                    break

                # Step failed or verification failed -> Attempt Recovery
                step.retry_count += 1
                self.audit_logger.log_retry(step.step_id, step.retry_count, tool_res_obj.message)

                if recovery_handler and step.retry_count <= self.max_retries:
                    rec_action = recovery_handler.recover_tool_failure(
                        step.required_tool,
                        step.parameters,
                        tool_res_obj.message,
                    )
                    self.audit_logger.log_recovery(
                        step.step_id,
                        rec_action.strategy,
                        rec_action.action_description,
                        rec_action.can_recover,
                    )

                    if rec_action.requires_user_clarification:
                        step.status = "clarification_required"
                        return {
                            "success": False,
                            "status": "clarification_required",
                            "step_id": step.step_id,
                            "message": rec_action.clarification_prompt,
                            "requires_user_clarification": True,
                        }

                    if rec_action.can_recover and rec_action.updated_arguments:
                        step.parameters.update(rec_action.updated_arguments)
                        logger.info(f"[ReliableExecutor] Step {step.step_id} recovered with new params: {step.parameters}")
                        continue  # Retry loop with recovered parameters

            if not step_success:
                step.status = "failed"
                # Replanning attempt
                self.audit_logger.log_replan(step.step_id, tool_res_obj.message if tool_res_obj else "Step failed", plan.to_dict())
                plan = planner.replan_from_state(
                    plan,
                    step.step_id,
                    tool_res_obj.message if tool_res_obj else "Failure",
                    {"active_workbook": self.session.active_workbook_path},
                )

                # If replanning failed to recover, abort & rollback
                if self.backup_manager:
                    self.backup_manager.rollback_to_latest_snapshot()

                err_msg = f"Task step {step.step_id} ('{step.description}') failed after {step.retry_count} attempts: {tool_res_obj.message if tool_res_obj else 'Execution failed'}"
                self.audit_logger.log_final_result(False, err_msg, (time.time() - t_start) * 1000)
                return {
                    "success": False,
                    "status": "failed",
                    "step_id": step.step_id,
                    "message": err_msg,
                    "plan": plan.to_dict(),
                    "audit_logs": self.audit_logger.get_logs(),
                }

            executed_steps.append(step.to_dict())

        # 6. Final Workbook Save & Integrity Verification
        final_file = (backend.file_path if (backend and backend.file_path and os.path.exists(backend.file_path)) else self.session.active_workbook_path)
        if self.backup_manager and not (backend and backend.file_path and os.path.exists(backend.file_path) and backend.file_path != self.backup_manager.working_copy_path):
            final_file = self.backup_manager.finalize()

        if backend and verifier and final_file and os.path.exists(final_file):
            final_v = verifier._verify_save({"file_path": final_file}, 0.0)
            self.audit_logger.log_verification(0, "final_save_verify", final_v.success, final_v.message)

        total_ms = (time.time() - t_start) * 1000
        success_msg = f"Successfully executed {len(executed_steps)} steps in {round(total_ms, 2)}ms."
        self.audit_logger.log_final_result(True, success_msg, total_ms)

        return {
            "success": True,
            "status": "completed",
            "message": success_msg,
            "plan": plan.to_dict(),
            "executed_steps": executed_steps,
            "final_file": final_file,
            "total_duration_ms": round(total_ms, 2),
            "audit_logs": self.audit_logger.get_logs(),
        }
