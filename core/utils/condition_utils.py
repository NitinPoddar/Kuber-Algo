from core.models import  Condition

def save_condition_structure(algo_logic, structure, condition_type='entry', parent=None):
    pass
    # same code as above
def serialize_conditions(root_conditions):
    """
    Serialize flat Condition model back into nested structure for UI.
    This assumes `root_conditions` is a queryset of top-level conditions (i.e. where nested_condition is None).
    """
    def recurse(condition):
        return {
            "variable_name": condition.variable_name,
            "operator": condition.operator,
            "value": condition.value,
            "connector": "AND",  # You can extend this later if needed
            "children": [recurse(child) for child in condition.children.all()]
        }

    return [recurse(c) for c in root_conditions]

def build_condition_as_python(condition):
    """
    Build a single condition string like: rsi(period=14) > 30 or supertrend(symbol='NIFTY') <= ema(period=21)
    """
    def format_variable(name, parameters):
        if not parameters:
            return f"{name}()"
        params_str = ", ".join(f"{k}='{v}'" if isinstance(v, str) else f"{k}={v}" for k, v in parameters.items())
        return f"{name}({params_str})"

    lhs = format_variable(condition.lhs_variable, condition.lhs_parameters or {})
    
    if condition.rhs_type == 'value':
        rhs = f"'{condition.rhs_value}'" if isinstance(condition.rhs_value, str) else str(condition.rhs_value)
    elif condition.rhs_type == 'variable':
        rhs = format_variable(condition.rhs_variable, condition.rhs_parameters or {})
    else:
        rhs = "UNKNOWN"

    return f"{lhs} {condition.operator} {rhs}"


def render_condition_as_python(conditions):
    """
    Recursively builds full Python string from nested conditions.
    """
    def recurse(condition):
        base = build_condition_as_python(condition)
        children = condition.children.all()
        if children:
            joined = f" {condition.connector} ".join([recurse(child) for child in children])
            return f"({base} {condition.connector} {joined})"
        else:
            return base

    return " AND ".join([recurse(c) for c in conditions])

