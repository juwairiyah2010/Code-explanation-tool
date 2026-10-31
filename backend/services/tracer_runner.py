"""Isolated Subprocess Execution Tracer using Python's sys.settrace.

NOTE ON SANDBOXING:
This tracer runs code in an isolated subprocess with OS resource limits (CPU and virtual memory)
and a restricted __builtins__ namespace blocking file/system I/O and arbitrary imports.
For hostile, multi-tenant untrusted code, process/container-level isolation (e.g., Docker/gVisor/seccomp)
must be used.
"""

import argparse
import builtins
import io
import json
import resource
import sys
import time
import traceback
import types

MAX_STEPS = 1000
MAX_OUTPUT_CHARS = 16384
MAX_VAR_REPR_LEN = 120


def limit_resources() -> None:
    """Restrict CPU time and virtual memory to prevent runaway resource consumption."""
    try:
        # Limit CPU time to 2 seconds
        resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
    except Exception:
        pass

    try:
        # Limit virtual memory to 128 MB
        resource.setrlimit(resource.RLIMIT_AS, (128 * 1024 * 1024, 128 * 1024 * 1024))
    except Exception:
        pass


def _truncate_val(v: object, max_len: int = MAX_VAR_REPR_LEN) -> str:
    """Format a variable value cleanly, truncating overly long representations."""
    try:
        s = repr(v)
        if len(s) > max_len:
            return s[:max_len] + "..."
        return s
    except Exception:
        return "<unrepresentable>"


def _filter_locals(raw_locals: dict) -> dict[str, str]:
    """Filter out internal variables, functions, and module objects."""
    clean = {}
    for k, v in raw_locals.items():
        if k.startswith("__"):
            continue
        if isinstance(v, (types.ModuleType, types.FunctionType, types.BuiltinFunctionType, types.BuiltinMethodType)):
            continue
        clean[k] = _truncate_val(v)
    return clean


def run_trace(code_str: str, input_data: str | None = None) -> dict:
    """Execute code_str under sys.settrace in an isolated interpreter frame."""
    limit_resources()
    start_time = time.perf_counter()

    steps: list[dict] = []
    output_buffer = io.StringIO()
    total_output_chars = 0

    original_stdout = sys.stdout
    original_stdin = sys.stdin
    sys.stdout = output_buffer

    if input_data is not None:
        sys.stdin = io.StringIO(input_data)

    code_lines = code_str.splitlines()

    # Track frame depths and previous variable snapshots per frame id
    frame_prev_vars: dict[int, dict[str, str]] = {}
    call_depth = 0
    step_count = 0
    hit_step_limit = False

    def get_and_clear_output() -> str | None:
        nonlocal total_output_chars
        sys.stdout.seek(0)
        out_val = sys.stdout.read()
        sys.stdout.truncate(0)
        sys.stdout.seek(0)
        if not out_val:
            return None
        total_output_chars += len(out_val)
        if total_output_chars > MAX_OUTPUT_CHARS:
            return out_val[:500] + "\n[Output truncated: limit exceeded]"
        return out_val

    def trace_dispatcher(frame, event: str, arg: object):
        nonlocal call_depth, step_count, hit_step_limit

        # Only trace code from our '<string>' target execution
        if frame.f_code.co_filename != "<string>":
            return trace_dispatcher

        if step_count >= MAX_STEPS:
            hit_step_limit = True
            return None

        lineno = frame.f_lineno
        executed_code = code_lines[lineno - 1].strip() if 1 <= lineno <= len(code_lines) else ""
        func_name = frame.f_code.co_name
        frame_id = id(frame)

        # 1. Handle Function Call
        if event == "call":
            if func_name != "<module>":
                call_depth += 1
            else:
                call_depth = 0

            step_count += 1
            current_vars = _filter_locals(frame.f_locals)
            frame_prev_vars[frame_id] = dict(current_vars)
            out_val = get_and_clear_output()

            steps.append({
                "execution_step": step_count,
                "line_number": lineno,
                "event_type": "call",
                "function_name": func_name,
                "local_variables": current_vars,
                "changed_variables": dict(current_vars),  # All arguments are new variables in this frame
                "stdout": out_val,
                "exception": None,
                "timestamp": round(time.perf_counter() - start_time, 6),
                "call_depth": call_depth,
                "executed_code": executed_code,
                "variables": current_vars,
                "output": out_val,
            })
            return trace_dispatcher

        # 2. Handle Line Execution
        elif event == "line":
            step_count += 1
            current_vars = _filter_locals(frame.f_locals)
            prev_vars = frame_prev_vars.get(frame_id, {})

            # Calculate variable diff
            changed_vars = {}
            for k, v in current_vars.items():
                if k not in prev_vars or prev_vars[k] != v:
                    changed_vars[k] = v

            frame_prev_vars[frame_id] = dict(current_vars)
            out_val = get_and_clear_output()

            steps.append({
                "execution_step": step_count,
                "line_number": lineno,
                "event_type": "line",
                "function_name": func_name,
                "local_variables": current_vars,
                "changed_variables": changed_vars,
                "stdout": out_val,
                "exception": None,
                "timestamp": round(time.perf_counter() - start_time, 6),
                "call_depth": call_depth,
                "executed_code": executed_code,
                "variables": current_vars,
                "output": out_val,
            })
            return trace_dispatcher

        # 3. Handle Function Return
        elif event == "return":
            step_count += 1
            current_vars = _filter_locals(frame.f_locals)
            prev_vars = frame_prev_vars.get(frame_id, {})

            changed_vars = {}
            for k, v in current_vars.items():
                if k not in prev_vars or prev_vars[k] != v:
                    changed_vars[k] = v

            if func_name != "<module>":
                ret_val_str = _truncate_val(arg)
                changed_vars["<return_value>"] = ret_val_str

            out_val = get_and_clear_output()

            steps.append({
                "execution_step": step_count,
                "line_number": lineno,
                "event_type": "return",
                "function_name": func_name,
                "local_variables": current_vars,
                "changed_variables": changed_vars,
                "stdout": out_val,
                "exception": None,
                "timestamp": round(time.perf_counter() - start_time, 6),
                "call_depth": call_depth,
                "executed_code": executed_code,
                "variables": current_vars,
                "output": out_val,
            })
            frame_prev_vars.pop(frame_id, None)
            if func_name != "<module>":
                call_depth = max(0, call_depth - 1)
            return trace_dispatcher

        # 4. Handle Exception
        elif event == "exception":
            step_count += 1
            exc_type, exc_val, _ = arg if isinstance(arg, tuple) and len(arg) == 3 else (None, None, None)
            exc_desc = f"{exc_type.__name__}: {exc_val}" if exc_type else "Exception"
            current_vars = _filter_locals(frame.f_locals)
            out_val = get_and_clear_output()

            steps.append({
                "execution_step": step_count,
                "line_number": lineno,
                "event_type": "exception",
                "function_name": func_name,
                "local_variables": current_vars,
                "changed_variables": {},
                "stdout": out_val,
                "exception": exc_desc,
                "timestamp": round(time.perf_counter() - start_time, 6),
                "call_depth": call_depth,
                "executed_code": executed_code,
                "variables": current_vars,
                "output": out_val,
            })
            return trace_dispatcher

        return trace_dispatcher

    # AST-level static check to block Python sandbox reflection escapes
    try:
        import ast
        tree = ast.parse(code_str)
        forbidden_attrs = {
            "__subclasses__", "__bases__", "__mro__", "__globals__",
            "__code__", "__closure__", "__func__", "__builtins__",
            "__import__",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in forbidden_attrs:
                sys.stdout = original_stdout
                return {
                    "success": False,
                    "language": "python",
                    "error": f"SecurityError: Access to internal attribute '{node.attr}' is prohibited by execution sandbox.",
                    "steps": [],
                    "output": "",
                    "final_state": {},
                    "execution_time": round(time.perf_counter() - start_time, 4),
                }
    except SyntaxError as e:
        sys.stdout = original_stdout
        return {
            "success": False,
            "language": "python",
            "error": f"SyntaxError: {e.msg} at line {e.lineno}",
            "steps": [],
            "output": "",
            "final_state": {},
            "execution_time": round(time.perf_counter() - start_time, 4),
        }

    # Compile the code
    try:
        compiled_code = compile(code_str, "<string>", "exec")
    except SyntaxError as e:
        sys.stdout = original_stdout
        return {
            "success": False,
            "language": "python",
            "error": f"SyntaxError: {e.msg} at line {e.lineno}",
            "steps": [],
            "output": "",
            "final_state": {},
            "execution_time": round(time.perf_counter() - start_time, 4),
        }
    except Exception as e:
        sys.stdout = original_stdout
        return {
            "success": False,
            "language": "python",
            "error": str(e),
            "steps": [],
            "output": "",
            "final_state": {},
            "execution_time": round(time.perf_counter() - start_time, 4),
        }

    error_msg = None
    success = True

    # Restrict built-ins to safe operations (prevent arbitrary host file system or os calls)
    allowed_builtins = [
        "print", "input", "range", "len", "int", "float", "str", "bool",
        "list", "dict", "set", "tuple", "sum", "min", "max", "abs",
        "round", "enumerate", "zip", "map", "filter", "isinstance",
        "issubclass", "type", "ValueError", "TypeError", "IndexError",
        "KeyError", "ZeroDivisionError", "Exception", "sorted", "reversed",
    ]
    safe_builtins = {k: getattr(builtins, k) for k in allowed_builtins if hasattr(builtins, k)}

    # Execute with active tracer
    try:
        sys.settrace(trace_dispatcher)
        global_env = {"__name__": "__main__", "__builtins__": safe_builtins}
        exec(compiled_code, global_env)
        if hit_step_limit:
            success = False
            error_msg = f"Execution step limit exceeded (maximum {MAX_STEPS} steps). Possible infinite loop."
    except Exception:
        success = False
        error_msg = traceback.format_exc().strip().split("\n")[-1]
    finally:
        sys.settrace(None)

        # Capture any remaining output
        sys.stdout.seek(0)
        remaining_out = sys.stdout.read()
        if remaining_out and steps:
            if steps[-1]["output"]:
                steps[-1]["output"] += remaining_out
                steps[-1]["stdout"] += remaining_out
            else:
                steps[-1]["output"] = remaining_out
                steps[-1]["stdout"] = remaining_out
        elif remaining_out:
            steps.append({
                "execution_step": step_count + 1,
                "line_number": -1,
                "event_type": "output",
                "function_name": "<module>",
                "local_variables": {},
                "changed_variables": {},
                "stdout": remaining_out,
                "exception": None,
                "timestamp": round(time.perf_counter() - start_time, 6),
                "call_depth": 0,
                "executed_code": "",
                "variables": {},
                "output": remaining_out,
            })

        sys.stdout = original_stdout
        sys.stdin = original_stdin

    execution_time = round(time.perf_counter() - start_time, 4)

    # Determine final state from the last valid step's variables
    final_state = {}
    if steps:
        final_state = steps[-1].get("local_variables") or steps[-1].get("variables") or {}

    total_captured_output = "".join([s.get("stdout") or "" for s in steps])

    return {
        "success": success,
        "language": "python",
        "steps": steps,
        "output": total_captured_output,
        "error": error_msg,
        "final_state": final_state,
        "execution_time": execution_time,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Structured Python Execution Tracer")
    parser.add_argument("--code-file", required=True)
    parser.add_argument("--input-file", required=False)
    parser.add_argument("--out-file", required=True)
    args = parser.parse_args()

    with open(args.code_file, "r", encoding="utf-8") as f:
        code_input = f.read()

    input_text = None
    if args.input_file:
        with open(args.input_file, "r", encoding="utf-8") as f:
            input_text = f.read()

    trace_result = run_trace(code_input, input_text)

    with open(args.out_file, "w", encoding="utf-8") as f:
        json.dump(trace_result, f)
