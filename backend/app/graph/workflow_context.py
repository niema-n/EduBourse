"""Typed workflow context and conservative continuation policy for J7-03."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

WorkflowAgent = Literal[
    "pedagogie", "formation_elearning", "cisi", "quiz", "championnat",
    "orientation", "support_ecole", "out_of_domain", "fallback",
]
WorkflowStatus = Literal["idle", "waiting_user", "processing", "paused", "completed"]
ExpectedInputKind = Literal["none", "choice", "confirmation", "free_text"]


class ConversationWorkflowContext(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)

    active_agent: WorkflowAgent | None = None
    active_workflow: str | None = None
    workflow_step: str | None = None
    status: WorkflowStatus = "idle"
    expected_input_kind: ExpectedInputKind = "none"
    expected_input_values: list[str] = Field(default_factory=list)
    turn_count: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_context(self) -> "ConversationWorkflowContext":
        if self.status == "idle":
            if any((self.active_agent, self.active_workflow, self.workflow_step)):
                raise ValueError("idle context cannot have an active workflow")
            if self.expected_input_kind != "none" or self.expected_input_values:
                raise ValueError("idle context cannot expect user input")
        if self.expected_input_kind == "choice" and not self.expected_input_values:
            raise ValueError("choice continuation requires expected values")
        if (
            self.expected_input_kind not in {"choice", "confirmation"}
            and self.expected_input_values
        ):
            raise ValueError("expected values are only valid for choice or confirmation input")
        return self


class ContinuationDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    is_continuation: bool
    route: WorkflowAgent | None = None


class WorkflowContextService:
    """Build and resolve context without classifying ordinary user messages."""

    def start_workflow(
        self,
        *,
        active_agent: WorkflowAgent,
        active_workflow: str,
        workflow_step: str,
        expected_input_kind: ExpectedInputKind = "none",
        expected_input_values: tuple[str, ...] | list[str] = (),
    ) -> ConversationWorkflowContext:
        return ConversationWorkflowContext(
            active_agent=active_agent,
            active_workflow=active_workflow,
            workflow_step=workflow_step,
            status="waiting_user",
            expected_input_kind=expected_input_kind,
            expected_input_values=list(expected_input_values),
        )

    def update_workflow(self, context: ConversationWorkflowContext, **updates: object):
        values = context.model_dump()
        values.update(updates)
        return ConversationWorkflowContext.model_validate(values)

    def wait_for_user(
        self,
        context: ConversationWorkflowContext,
        *,
        expected_input_kind: ExpectedInputKind,
        expected_input_values: tuple[str, ...] | list[str] = (),
    ) -> ConversationWorkflowContext:
        return self.update_workflow(
            context,
            status="waiting_user",
            expected_input_kind=expected_input_kind,
            expected_input_values=list(expected_input_values),
        )

    def complete_workflow(
        self, context: ConversationWorkflowContext
    ) -> ConversationWorkflowContext:
        return self.update_workflow(
            context,
            status="completed",
            expected_input_kind="none",
            expected_input_values=[],
        )

    def clear_workflow(self) -> ConversationWorkflowContext:
        return ConversationWorkflowContext()

    def pause_workflow(self, context: ConversationWorkflowContext) -> ConversationWorkflowContext:
        return self.update_workflow(
            context, status="paused", expected_input_kind="none", expected_input_values=[]
        )

    def resolve_continuation(
        self, context: ConversationWorkflowContext | None, user_input: str
    ) -> ContinuationDecision:
        if context is None or context.status != "waiting_user" or context.active_agent is None:
            return ContinuationDecision(is_continuation=False)
        if context.workflow_step == "learning_level":
            from app.learning.level_resolution import extract_level, requests_diagnostic

            if extract_level(user_input, allow_bare=True) or requests_diagnostic(user_input):
                return ContinuationDecision(is_continuation=True, route=context.active_agent)
            return ContinuationDecision(is_continuation=False)
        if context.expected_input_kind not in {"choice", "confirmation"}:
            return ContinuationDecision(is_continuation=False)
        normalized = user_input.strip().casefold()
        expected = {value.strip().casefold() for value in context.expected_input_values}
        if normalized and normalized in expected:
            return ContinuationDecision(is_continuation=True, route=context.active_agent)
        return ContinuationDecision(is_continuation=False)

    def record_continuation(
        self, context: ConversationWorkflowContext
    ) -> ConversationWorkflowContext:
        return self.update_workflow(context, turn_count=context.turn_count + 1)
