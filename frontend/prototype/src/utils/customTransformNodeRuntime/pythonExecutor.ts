export const buildExecutionCode = (): string => {
  return `
import ast
import sys
from io import StringIO
import json
import traceback

# User code is injected via globals
_user_code = __user_code

_result = {
    "output": None,
    "stdout": "",
    "error": None
}

_stdout = StringIO()
_original_stdout = sys.stdout

# -----------------------
# 1. Syntax validation
# -----------------------
try:
    tree = ast.parse(_user_code)
except SyntaxError as e:
    _result["error"] = {
        "type": "SyntaxError",
        "msg": e.msg or str(e),
        "line": e.lineno
    }
else:
    # -----------------------
    # 2. Structural validation
    # -----------------------
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)]

    if len(functions) != 1:
        _result["error"] = {
            "type": "ValidationError",
            "msg": "Exactly one function must be defined.",
            "line": None
        }
    elif len(functions[0].args.args) != 1:
        _result["error"] = {
            "type": "ValidationError",
            "msg": "Function must accept exactly one argument.",
            "line": functions[0].lineno
        }
    else:
        # -----------------------
        # 3. Execution
        # -----------------------
        sys.stdout = _stdout
        try:
            env = {}
            exec(compile(_user_code, "<user>", "exec"), env)

            fn_name = functions[0].name
            fn = env.get(fn_name)

            input_data = json.loads(__input_data)

            result = fn(input_data)

            if not isinstance(result, dict):
                raise TypeError("Function must return a dict.")

            _result["output"] = result

        except Exception as e:
            tb_exc = traceback.TracebackException.from_exception(e)

            user_line = None
            for frame in tb_exc.stack:
                if frame.filename == "<user>":
                    user_line = frame.lineno

            _result["error"] = {
                "type": type(e).__name__,
                "msg": str(e),
                "line": user_line
            }
        finally:
            sys.stdout = _original_stdout
            _result["stdout"] = _stdout.getvalue()

_result
`
}
