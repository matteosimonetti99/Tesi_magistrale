from bpmn_python import bpmn_diagram_rep as diagram
import xml.etree.ElementTree as ET
import json

baseName="mainMinimalCustomSimPar"
name="../bpmn_input_file_here/"+baseName+".bpmn"

# QBP TAG
tree = ET.parse(name)

# Get the root element of the XML document
root = tree.getroot()

# Find the <qbp> tag
qbp_tag = root.find('.//qbp')

# If the <qbp> tag exists, print its contents
if qbp_tag is not None:
    print(ET.tostring(qbp_tag, encoding='unicode'))
else:
    print("No <qbp> tag found in the BPMN XML file.")



# BPMN STRUCTURE
bpmnGraph = diagram.BpmnDiagramGraph()
bpmnGraph.create_new_diagram_graph(diagram_name="diagram1")

# Load existing BPMN diagram
bpmnGraph.load_diagram_from_xml_file(name)

# Manually construct a dictionary from the bpmnGraph
bpmnDictionary = {
    'diagram_attributes': bpmnGraph.diagram_attributes,
    'plane_attributes': bpmnGraph.plane_attributes,
    'sequence_flows': bpmnGraph.sequence_flows,
    'collaboration': bpmnGraph.collaboration,
}

process_elements = {}
for process_id, process_element in bpmnGraph.process_elements.items():
    node_details = {}
    for node_id in process_element['node_ids']:
        node_info = bpmnGraph.diagram_graph.node[node_id]
        node_details[node_id] = {
            'name': node_info.get('node_name', 'Unnamed'),
            'type': node_info.get('type', 'Unknown'),
        }
        if node_info.get('type', 'Unknown') == 'subProcess':
            # Add subprocess details
            subprocess_details = {}
            for child_node_id in node_info.get('node_ids', []):
                child_node_info = bpmnGraph.diagram_graph.node[child_node_id]
                subprocess_details[child_node_id] = {
                    'name': child_node_info.get('node_name', 'Unnamed'),
                    'type': child_node_info.get('type', 'Unknown'),
                }
            node_details[node_id]['subprocess_details'] = subprocess_details

    process_elements[process_id] = {
        'name': process_element.get('name', 'Unnamed'),
        'isClosed': process_element.get('isClosed', 'false'),
        'isExecutable': process_element.get('isExecutable', 'false'),
        'processType': process_element.get('processType', 'None'),
        'node_ids': process_element.get('node_ids', []),
        'node_details': node_details,
    }
bpmnDictionary['process_elements'] = process_elements


# Print the dictionary
with open("../tempp.json", "w") as outfile:
    json.dump(bpmnDictionary, outfile, indent=4)