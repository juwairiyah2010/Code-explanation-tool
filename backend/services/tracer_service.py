import os
import tempfile
import subprocess
import json
import asyncio
from backend.schemas.trace import TraceRequest, TraceResponse, TraceStep
from backend.core.logging import logger

class TracerService:
    def __init__(self):
        self.runner_script = os.path.join(os.path.dirname(__file__), "tracer_runner.py")
        
    async def trace_code(self, request: TraceRequest) -> TraceResponse:
        if request.language.lower() != "python":
            return TraceResponse(
                success=False,
                language=request.language,
                error=f"Tracing is currently only supported for Python (requested: {request.language})",
            )
            
        with tempfile.TemporaryDirectory() as temp_dir:
            code_file = os.path.join(temp_dir, "code.py")
            out_file = os.path.join(temp_dir, "out.json")
            
            with open(code_file, "w") as f:
                f.write(request.code)
                
            cmd = [
                sys.executable if 'sys' in globals() else "python3", 
                self.runner_script,
                "--code-file", code_file,
                "--out-file", out_file
            ]
            
            if request.input_data:
                input_file = os.path.join(temp_dir, "input.txt")
                with open(input_file, "w") as f:
                    f.write(request.input_data)
                cmd.extend(["--input-file", input_file])
                
            try:
                # Use asyncio.create_subprocess_exec to avoid blocking FastAPI
                import sys # needed for sys.executable
                cmd[0] = sys.executable
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                try:
                    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=3.0)
                except asyncio.TimeoutError:
                    process.kill()
                    return TraceResponse(
                        success=False,
                        language="python",
                        error="Execution timed out"
                    )
                    
                if not os.path.exists(out_file):
                    err_text = stderr.decode() if stderr else stdout.decode()
                    return TraceResponse(
                        success=False,
                        language="python",
                        error=f"Execution failed to produce a trace: {err_text[-200:]}"
                    )
                    
                with open(out_file, "r") as f:
                    result_json = json.load(f)
                    
                steps = [TraceStep(**step) for step in result_json.get("steps", [])]
                
                # Optional Mermaid Flowchart generation from AST
                flowchart = None
                if request.generate_flowchart:
                    from backend.services.parsers import get_parser
                    parser = get_parser("python")
                    ast_result = parser.parse(request.code)
                    flowchart = self._generate_flowchart(ast_result)
                    
                return TraceResponse(
                    success=result_json.get("success", False),
                    language="python",
                    steps=steps,
                    error=result_json.get("error"),
                    flowchart=flowchart
                )
                    
            except Exception as e:
                logger.error(f"TracerService error: {str(e)}")
                return TraceResponse(
                    success=False,
                    language="python",
                    error=f"Internal tracing error: {str(e)}"
                )

    def _generate_flowchart(self, ast_result) -> str:
        # Simple mermaid generator from parsed blocks
        lines = ["graph TD"]
        lines.append("    Start([Start])")
        
        blocks = ast_result.blocks
        if not blocks:
            return ""
            
        blocks.sort(key=lambda b: b.line_start)
        
        prev_id = "Start"
        for i, b in enumerate(blocks):
            node_id = f"N{i}"
            title = b.title.replace('"', "'")
            lines.append(f'    {node_id}["{title}"]')
            lines.append(f"    {prev_id} --> {node_id}")
            prev_id = node_id
            
        lines.append(f"    {prev_id} --> End([End])")
        return "\\n".join(lines)
