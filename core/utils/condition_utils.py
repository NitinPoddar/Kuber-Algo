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
    def serialize_node(node):
        base = {
            "lhs": {
                "name": node.lhs_variable,
                "parameters": [{"key": k, "value": v} for k, v in node.lhs_parameters.items()]
            },
            "operator": node.operator,
            "rhs": {
                "type": node.rhs_type,
                "value": node.rhs_value if node.rhs_type == "value" else None,
                "name": node.rhs_variable if node.rhs_type == "variable" else None,
                "parameters": [{"key": k, "value": v} for k, v in node.rhs_parameters.items()] if node.rhs_type == "variable" else []
            },
            "connector": node.connector,
            "children": []
        }
        children = node.children.all()
        base["children"] = [serialize_node(child) for child in children]
        return base

    top_level = Condition.objects.filter(algo_logic=logic, condition_type=condition_type, nested_condition__isnull=True)
    return [serialize_node(c) for c in top_level]
