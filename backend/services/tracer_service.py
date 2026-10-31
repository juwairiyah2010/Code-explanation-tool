"""Tracer service managing subprocess execution and trace-derived Mermaid flowcharts."""

import asyncio
import json
import os
import sys
import tempfile
from backend.core.logging import logger
from backend.schemas.trace import TraceRequest, TraceResponse, TraceStep


def generate_mermaid_from_trace(steps: list[TraceStep], max_diagram_steps: int = 25) -> str:
    """Generate Mermaid control-flow diagram directly from structured trace execution steps."""
    if not steps:
        return ""

    lines = ["graph TD", "    Start([Start])"]
    prev_node_id = "Start"

    # Limit nodes to avoid rendering engine overflow on massive loops
    display_steps = steps[:max_diagram_steps]

    for idx, s in enumerate(display_steps):
        node_id = f"Step{idx + 1}"
        clean_code = (s.executed_code or f"Line {s.line_number}").replace('"', "'").replace("\n", " ").strip()
        if len(clean_code) > 40:
            clean_code = clean_code[:37] + "..."

        if s.event_type == "call":
            label = f"Call {s.function_name}() (L{s.line_number})"
            lines.append(f'    {node_id}[["{label}"]]')
        elif s.event_type == "return":
            ret_val = s.changed_variables.get("<return_value>", "")
            label = f"Return {s.function_name}() -> {ret_val}" if ret_val else f"Return {s.function_name}()"
            lines.append(f'    {node_id}[/"{label}"/]')
        elif s.event_type == "exception":
            exc_label = f"Exception: {s.exception or 'Error'} (L{s.line_number})"
            lines.append(f'    {node_id}{{"{exc_label}"}}')
        else:
            label = f"L{s.line_number}: {clean_code}"
            lines.append(f'    {node_id}["{label}"]')

        lines.append(f"    {prev_node_id} --> {node_id}")
        prev_node_id = node_id

    if len(steps) > max_diagram_steps:
        omitted = len(steps) - max_diagram_steps
        more_id = "OmittedSteps"
        lines.append(f'    {more_id}["... {omitted} intermediate execution steps ..."]')
        lines.append(f"    {prev_node_id} --> {more_id}")
        prev_node_id = more_id

    lines.append(f"    {prev_node_id} --> End([End])")
    return "\n".join(lines)


class TracerService:
    """Orchestrates code tracing in an isolated subprocess with resource limits."""

    def __init__(self, timeout_seconds: float = 3.0):
        self.runner_script = os.path.join(os.path.dirname(__file__), "tracer_runner.py")
        self.timeout_seconds = timeout_seconds

    async def trace_code(self, request: TraceRequest) -> TraceResponse:
        """Trace Python execution step-by-step and produce structured execution result."""
        if request.language.lower() != "python":
            return TraceResponse(
                success=False,
                language=request.language,
                error=f"Tracing is currently only supported for Python (requested: {request.language})",
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            code_file = os.path.join(temp_dir, "code.py")
            out_file = os.path.join(temp_dir, "out.json")

            with open(code_file, "w", encoding="utf-8") as f:
                f.write(request.code)

            cmd = [
                sys.executable,
                self.runner_script,
                "--code-file", code_file,
                "--out-file", out_file,
            ]

            if request.input_data:
                input_file = os.path.join(temp_dir, "input.txt")
                with open(input_file, "w", encoding="utf-8") as f:
                    f.write(request.input_data)
                cmd.extend(["--input-file", input_file])

            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(), timeout=self.timeout_seconds
                    )
                except asyncio.TimeoutError:
                    try:
                        process.kill()
                    except ProcessLookupError:
                        pass
                    return TraceResponse(
                        success=False,
                        language="python",
                        error="Execution timed out",
                    )

                if not os.path.exists(out_file):
                    err_text = (
                        stderr.decode(errors="replace")
                        if stderr
                        else stdout.decode(errors="replace")
                    )
                    return TraceResponse(
                        success=False,
                        language="python",
                        error=f"Execution failed to produce a trace: {err_text[-200:].strip()}",
                    )

                with open(out_file, "r", encoding="utf-8") as f:
                    result_json = json.load(f)

                steps = [TraceStep(**s) for s in result_json.get("steps", [])]

                flowchart = None
                if request.generate_flowchart:
                    flowchart = generate_mermaid_from_trace(steps)

                return TraceResponse(
                    success=result_json.get("success", False),
                    language="python",
                    steps=steps,
                    output=result_json.get("output", ""),
                    error=result_json.get("error"),
                    final_state=result_json.get("final_state", {}),
                    execution_time=result_json.get("execution_time", 0.0),
                    flowchart=flowchart,
                )

            except Exception as e:
                logger.error(f"TracerService execution error: {e}")
                return TraceResponse(
                    success=False,
                    language="python",
                    error=f"Internal tracing error: {str(e)}",
                )

    async def trace_if_applicable(
        self, code: str, language: str, input_data: str | None = None
    ) -> TraceResponse | None:
        """Run execution trace only when applicable (Python code). Returns None if not applicable."""
        if language.lower() not in ("python", "py"):
            return None
        req = TraceRequest(code=code, language="python", input_data=input_data)
        return await self.trace_code(req)


TraceService = TracerService

