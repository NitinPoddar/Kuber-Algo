from core.models import  Condition

def save_condition_structure(algo_logic, structure, condition_type='entry', parent=None):
    pass
    # same code as above
def serialize_conditions1(root_conditions):
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

def serialize_conditions(logic, condition_type):
    def serialize_node(node, is_root=False):
        data = {
            "is_root":  is_root,
            "lhs": {
                "name":       node.lhs_variable,
                "parameters": node.lhs_parameters or {}
            },
            "operator":    node.operator,
            "rhs": {
                "type":       node.rhs_type,
                "value":      node.rhs_value    if node.rhs_type == "value"    else None,
                "name":       node.rhs_variable if node.rhs_type == "variable" else None,
                "parameters": node.rhs_parameters or {}
            },
            "connector":   node.connector,
            "children":    []
        }
        # Recurse into any nested children, marking them non‐root
        for child in node.children.all():
            data["children"].append(serialize_node(child, is_root=False))
        return data

    # Fetch only the top‐level (no parent) conditions
    top_level = Condition.objects.filter(
        algo_logic=logic,
        condition_type=condition_type,
        nested_condition__isnull=True
    )

    # Serialize each, marking it as root
    return [serialize_node(node, is_root=True) for node in top_level]
