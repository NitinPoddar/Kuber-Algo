# -*- coding: utf-8 -*-
"""
Created on Mon Aug 11 00:17:45 2025

@author: Home
"""

# core/services/variables/runtime.py
from __future__ import annotations
from typing import Any, Dict, Optional
from core.models import Variable, Condition, AlgorithmLogic
from core.services.sandbox_exec import execute_user_code

# simple in-memory cache (dev); swap for django cache if you want
_VAR_CODE_CACHE: dict[str, str] = {}

def get_var_code(name: str) -> Optional[str]:
    if name in _VAR_CODE_CACHE:
        return _VAR_CODE_CACHE[name]
    try:
        v = Variable.objects.get(name=name)
        _VAR_CODE_CACHE[name] = v.function_code or ""
        return _VAR_CODE_CACHE[name]
    except Variable.DoesNotExist:
        return None

def eval_variable(name: str, params: Dict[str, Any], inputs: Dict[str, Any], env: Dict[str, Any]) -> Any:
    code = get_var_code(name)
    if not code:
        raise RuntimeError(f"Variable '{name}' not found or has no code.")
    # Each variable is expected to define run(inputs, env) or set `result`
    # Provide params inside inputs["params"], so user code can read it:
    v_inputs = dict(inputs)
    v_inputs = {**v_inputs, "params": params or {}}
    return execute_user_code(code, v_inputs, env)

def eval_node(node: Condition, inputs: Dict[str, Any], env: Dict[str, Any]) -> bool:
    # 1) LHS value
    lhs = eval_variable(node.lhs_variable, node.lhs_parameters or {}, inputs, env)

    # 2) RHS value
    if node.rhs_type == "value":
        rhs = node.rhs_value
        # try numeric cast
        try:
            if isinstance(rhs, str) and rhs.replace('.','',1).isdigit():
                rhs = float(rhs) if '.' in rhs else int(rhs)
        except Exception:
            pass
    else:
        rhs = eval_variable(node.rhs_variable, node.rhs_parameters or {}, inputs, env)

    # 3) Compare
    op = node.operator
    ops = {
        ">":  lambda a,b: a > b,
        "<":  lambda a,b: a < b,
        ">=": lambda a,b: a >= b,
        "<=": lambda a,b: a <= b,
        "==": lambda a,b: a == b,
        "!=": lambda a,b: a != b,
    }
    res = ops[op](lhs, rhs)

    # 4) Combine with children (if any)
    children = list(node.children.all())
    if not children:
        return res

    # Fold children with connector (AND/OR) starting from current res
    if node.connector == "AND":
        for ch in children:
            res = res and eval_node(ch, inputs, env)
            if not res: break
    else:
        for ch in children:
            res = res or eval_node(ch, inputs, env)
            if res: break
    return res

def eval_leg_conditions(leg: AlgorithmLogic, when_inputs: Dict[str, Any], env: Dict[str, Any]) -> Dict[str, bool]:
    """Return dict like {'entry': True/False, 'exit': True/False} for a leg."""
    entries = Condition.objects.filter(algo_logic=leg, condition_type="entry", nested_condition__isnull=True)
    exits   = Condition.objects.filter(algo_logic=leg, condition_type="exit",  nested_condition__isnull=True)
    entry_ok = all(eval_node(n, when_inputs, env) for n in entries) if entries else True
    exit_ok  = any(eval_node(n, when_inputs, env) for n in exits)   if exits else False
    return {"entry": entry_ok, "exit": exit_ok}
