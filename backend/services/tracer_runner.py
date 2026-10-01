import sys
import json
import io
import traceback
import resource
import builtins
import types

def limit_resources():
    """Restrict memory and CPU time to prevent malicious code from crashing the system."""
    try:
        # Limit CPU time to 2 seconds
        resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
        # Limit virtual memory to 128 MB
        resource.setrlimit(resource.RLIMIT_AS, (128 * 1024 * 1024, 128 * 1024 * 1024))
    except Exception:
        pass

def run_trace(code_str: str, input_data: str = None):
    limit_resources()
    
    steps = []
    output_buffer = io.StringIO()
    
    # Store original stdout and inputs
    original_stdout = sys.stdout
    original_stdin = sys.stdin
    sys.stdout = output_buffer
    
    if input_data is not None:
        sys.stdin = io.StringIO(input_data)
        
    code_lines = code_str.splitlines()

    def _truncate_val(v, max_len=100):
        try:
            s = repr(v)
            if len(s) > max_len:
                return s[:max_len] + "..."
            return s
        except Exception:
            return "<unrepresentable>"

    def trace_lines(frame, event, arg):
        if event == 'line':
            # Only trace code from our `<string>` execution
            if frame.f_code.co_filename != '<string>':
                return trace_lines
                
            lineno = frame.f_lineno
            if 1 <= lineno <= len(code_lines):
                executed_code = code_lines[lineno - 1].strip()
            else:
                executed_code = ""
                
            # Grab local variables
            # filter out builtins and special vars
            locals_dict = {k: _truncate_val(v) for k, v in frame.f_locals.items() if not k.startswith('__') and not isinstance(v, (types.ModuleType, types.FunctionType, types.BuiltinFunctionType, types.BuiltinMethodType))}
            
            # Read whatever was outputted since the last step
            sys.stdout.seek(0)
            out_val = sys.stdout.read()
            # Clear buffer
            sys.stdout.truncate(0)
            sys.stdout.seek(0)
            
            steps.append({
                "line_number": lineno,
                "executed_code": executed_code,
                "variables": locals_dict,
                "output": out_val if out_val else None
            })
            
        return trace_lines

    # Compile the code
    try:
        compiled_code = compile(code_str, '<string>', 'exec')
    except SyntaxError as e:
        sys.stdout = original_stdout
        return {"success": False, "error": f"SyntaxError: {e.msg} at line {e.lineno}", "steps": []}
    except Exception as e:
        sys.stdout = original_stdout
        return {"success": False, "error": str(e), "steps": []}

    error_msg = None
    success = True
    
    # Secure builtins
    safe_builtins = {}
    allowed_builtins = ['print', 'input', 'range', 'len', 'int', 'float', 'str', 'bool', 'list', 'dict', 'set', 'tuple', 'sum', 'min', 'max', 'abs', 'round', 'enumerate', 'zip', 'map', 'filter', 'isinstance', 'issubclass', 'type', 'ValueError', 'TypeError', 'IndexError', 'KeyError', 'Exception']
    for k in allowed_builtins:
        if hasattr(builtins, k):
            safe_builtins[k] = getattr(builtins, k)
    
    # Run the code
    try:
        sys.settrace(trace_lines)
        global_env = {"__name__": "__main__", "__builtins__": safe_builtins}
        exec(compiled_code, global_env)
    except Exception as e:
        success = False
        error_msg = traceback.format_exc().strip().split('\n')[-1] # Get last line of traceback
    finally:
        sys.settrace(None)
        
        # Capture any remaining output
        sys.stdout.seek(0)
        remaining_out = sys.stdout.read()
        if remaining_out and steps:
            if steps[-1]["output"]:
                steps[-1]["output"] += remaining_out
            else:
                steps[-1]["output"] = remaining_out
        elif remaining_out:
             steps.append({
                "line_number": -1,
                "executed_code": "",
                "variables": {},
                "output": remaining_out
            })
        
        sys.stdout = original_stdout
        sys.stdin = original_stdin
        
    return {
        "success": success,
        "error": error_msg,
        "steps": steps
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--code-file", required=True)
    parser.add_argument("--input-file", required=False)
    parser.add_argument("--out-file", required=True)
    args = parser.parse_args()
    
    with open(args.code_file, "r") as f:
        code_str = f.read()
        
    input_str = None
    if args.input_file:
        with open(args.input_file, "r") as f:
            input_str = f.read()
            
    result = run_trace(code_str, input_str)
    
    with open(args.out_file, "w") as f:
        json.dump(result, f)
