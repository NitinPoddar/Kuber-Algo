# -*- coding: utf-8 -*-
"""
Created on Sun Aug 10 13:23:35 2025

@author: Home
"""

# core/services/sandbox_exec.py
from __future__ import annotations
import ast
import json
import multiprocessing as mp
from typing import Any, Dict
# top of file
import platform, os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
import copy


SANDBOX_TIMEOUT_SECONDS = 1.0
SANDBOX_MEMORY_MB = 128

# ---- AST guard: disallow import/exec/eval etc. --------------------------------
FORBIDDEN_NODES = (
    ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal,
    ast.With, ast.AsyncWith,
    ast.Lambda,  # optional: keep code clearer
)

FORBIDDEN_NAMES = {"__import__", "open", "exec", "eval", "compile", "input", "exit", "quit", "help", "dir", "locals", "globals"}

def _validate_ast(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if isinstance(node, FORBIDDEN_NODES):
            raise ValueError(f"Forbidden syntax: {type(node).__name__}")
        # calls to forbidden names
        if isinstance(node, ast.Call):
            # function could be Name or Attribute
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_NAMES:
                raise ValueError(f"Forbidden call: {node.func.id}()")
        # attribute like obj.__dict__
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise ValueError("Forbidden dunder attribute access")

# ---- Safe builtins / global env ------------------------------------------------
SAFE_BUILTINS = {
    "abs": abs, "all": all, "any": any, "bool": bool, "enumerate": enumerate,
    "float": float, "int": int, "len": len, "list": list, "dict": dict,
    "max": max, "min": min, "range": range, "round": round, "set": set,
    "sorted": sorted, "sum": sum, "tuple": tuple, "zip": zip, "str": str, "isinstance": isinstance,
    "hasattr": hasattr,        # if your code uses it
    "getattr": getattr,        # optional
    "callable": callable,      # optional
    "type": type,
    "Exception": Exception,
    "ValueError": ValueError,    
}

ALLOWED_MODULES = {
    "math": __import__("math"),
   "statistics": __import__("statistics"),
   "datetime": __import__("datetime"),
   "zoneinfo": __import__("zoneinfo"),
}

def _env_has_client(env):
    return isinstance(env, dict) and env.get("client") is not None

def _build_transport_env(env: Dict[str, Any]) -> Dict[str, Any]:
    """
    Make a pickle-friendly subset of env for the child process.
    Keep only JSON-like data; drop client/functions/modules.
    """
    return {
        "globals": copy.deepcopy(env.get("globals", {})),
        "broker": copy.deepcopy(env.get("broker", None)),
        "meta":   copy.deepcopy(env.get("meta", {})),
        # intentionally exclude: env["client"], env["helpers"], etc.
    }

def _child_exec(code_str: str, inputs: Dict[str, Any], env: Dict[str, Any], conn):
    """
    Executed in a separate process. Applies rlimits (on POSIX),
    runs user code with very restricted builtins, then returns `result`.
    """
    try:
        # Resource limits (Linux/Unix)
        try:
            import resource
            # CPU seconds (soft, hard)
            resource.setrlimit(resource.RLIMIT_CPU, (1, 1))
            # Address space (bytes)
            mem_bytes = SANDBOX_MEMORY_MB * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        except Exception:
            pass  # not available on Windows; rely on timeout

        # Validate AST
        tree = ast.parse(code_str, filename="<user_code>", mode="exec")
        _validate_ast(tree)
        compiled = compile(tree, "<user_code>", "exec")

        # Build globals and locals
        user_globals = {"__builtins__": SAFE_BUILTINS, "inputs": inputs, "env": env}
        # add whitelisted modules as globals
        user_globals.update(ALLOWED_MODULES)
        user_locals: Dict[str, Any] = {}

        # Execute
        exec(compiled, user_globals, user_locals)

        # Auto-call run(inputs, env) if present
        result = None
        run_fn = user_globals.get("run") or user_locals.get("run")
        if callable(run_fn):
            result = run_fn(inputs, env)

        # If `result` variable is set, prefer that
        if "result" in user_locals:
            result = user_locals["result"]
        elif "result" in user_globals:
            result = user_globals["result"]

        conn.send(("ok", _jsonify(result)))
    except Exception as e:
        conn.send(("err", f"{type(e).__name__}: {e}"))
    finally:
        conn.close()

def _jsonify(obj: Any) -> Any:
    """Try to make results JSON-serializable; fallback to string."""
    try:
        json.dumps(obj)
        return obj
    except Exception:
        try:
            return json.loads(json.dumps(obj, default=str))
        except Exception:
            return str(obj)
def _run_in_thread(code_str, inputs, env):
    """
    In-process execution for Windows dev. No hard CPU/mem limits, but same AST guard.
    """
    try:
        tree = ast.parse(code_str, filename="<user_code>", mode="exec")
        _validate_ast(tree)
        compiled = compile(tree, "<user_code>", "exec")

        user_globals = {"__builtins__": SAFE_BUILTINS, "inputs": inputs, "env": env}
        user_globals.update(ALLOWED_MODULES)
        user_locals = {}
        exec(compiled, user_globals, user_locals)

        result = None
        run_fn = user_globals.get("run") or user_locals.get("run")
        if callable(run_fn):
            result = run_fn(inputs, env)

        if "result" in user_locals:
            result = user_locals["result"]
        elif "result" in user_globals:
            result = user_globals["result"]

        return _jsonify(result)
    except Exception as e:
        raise RuntimeError(f"{type(e).__name__}: {e}")

def execute_user_code(code_str: str, inputs: Dict[str, Any], env: Dict[str, Any],
                      timeout: float = SANDBOX_TIMEOUT_SECONDS,
                      force_thread: bool | None = None) -> Any:
    # Force thread mode on Windows (avoid WinError 6 entirely)
    if force_thread is None:
        force_thread=_env_has_client(env)
        
    if force_thread or platform.system() == "Windows" or os.environ.get("SANDBOX_FORCE_THREAD") == "1":
        with ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(_run_in_thread, code_str, inputs, env)
            try:
                return fut.result(timeout=timeout)
            except FuturesTimeout:
                raise RuntimeError("Timeout: code took too long (thread)")

    # ---- POSIX / multiprocessing path ----
    # 1) Make a pickle-safe env for the child
    transport_env = _build_transport_env(env)

    # 2) Create a unidirectional pipe for results
    parent_conn, child_conn = mp.Pipe(duplex=False)

    # 3) Spawn the child process with 'spawn' context
    ctx = mp.get_context("spawn")
    proc = ctx.Process(
        target=_child_exec,
        args=(code_str, inputs, transport_env, child_conn)
    )
    proc.daemon = True
    proc.start()

    # Parent no longer needs its end of the child pipe
    child_conn.close()

    # 4) Wait with timeout
    proc.join(timeout)
    if proc.is_alive():
        proc.terminate()
        proc.join(0.1)
        raise RuntimeError("Timeout: code took too long")

    # 5) Read child result
    if parent_conn.poll():
        status, payload = parent_conn.recv()
        if status == "ok":
            return payload
        raise RuntimeError(payload)

    raise RuntimeError("No response from sandbox")
