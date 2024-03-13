"""create a casymda model from a bpmn file and a template"""
from casymda.bpmn.bpmn_parser import parse_bpmn

name="diagram"
BPMN_PATH = "../"+name+".bpmn"
TEMPLATE_PATH = "bpmn_example_template.py"
JSON_PATH = "_temp_bpmn.json"
MODEL_PATH = "bpmn_example_model.py"


def test_parse_bpmn():
    """parse_bpmn"""
    parse_bpmn(BPMN_PATH, JSON_PATH, TEMPLATE_PATH, MODEL_PATH)


if __name__ == "__main__":
    test_parse_bpmn()