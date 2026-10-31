"""Execution trace schemas and structured result models."""

from pydantic import BaseModel, Field, model_validator
from typing import Any


class TraceRequest(BaseModel):
    code: str
    language: str = "python"
    input_data: str | None = None
    generate_flowchart: bool = False


class TraceStep(BaseModel):
    """Structured execution step capturing runtime state at a single instruction or frame event."""

    execution_step: int = 1
    line_number: int
    event_type: str = "line"  # "call", "line", "return", "exception"
    function_name: str = "<module>"
    local_variables: dict[str, str] = Field(default_factory=dict)
    changed_variables: dict[str, str] = Field(default_factory=dict)
    stdout: str | None = None
    exception: str | None = None
    timestamp: float = 0.0
    call_depth: int = 0
    executed_code: str = ""

    # Backward compatibility aliases for existing UI and tests
    variables: dict[str, str] = Field(default_factory=dict)
    output: str | None = None

    @model_validator(mode="before")
    @classmethod
    def sync_legacy_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Ensure local_variables and variables stay in sync
            if "variables" in data and "local_variables" not in data:
                data["local_variables"] = data["variables"]
            elif "local_variables" in data and "variables" not in data:
                data["variables"] = data["local_variables"]

            # Ensure stdout and output stay in sync
            if "output" in data and "stdout" not in data:
                data["stdout"] = data["output"]
            elif "stdout" in data and "output" not in data:
                data["output"] = data["stdout"]
        return data


class ExecutionResult(BaseModel):
    """Deterministic result object emitted by the tracer runner and service."""

    success: bool
    language: str = "python"
    steps: list[TraceStep] = Field(default_factory=list)
    output: str = ""
    error: str | None = None
    final_state: dict[str, str] = Field(default_factory=dict)
    execution_time: float = 0.0
    flowchart: str | None = None


# Alias TraceResponse to ExecutionResult for backward compatibility across endpoints and tests
TraceResponse = ExecutionResult
