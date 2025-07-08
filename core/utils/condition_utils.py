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

