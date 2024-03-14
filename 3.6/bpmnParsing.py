from bpmn_python import bpmn_diagram_rep as diagram
import xml.etree.ElementTree as ET
import json
import sys
import os

baseName="mainMinimalCustomSimPar"
tagName="simParam"
simParamPath="../json/simParam.json"
bpmnPath="../json/bpmn.json"


if os.path.isfile(simParamPath):
    os.remove(simParamPath)
if os.path.isfile(bpmnPath):
    os.remove(bpmnPath)

if len(sys.argv) > 1 and sys.argv[1].strip():
    baseName=sys.argv[1]

# simParam TAG
name="../bpmn_input_file_here/"+baseName+".bpmn"
try:
    tree = ET.parse(name)
    root = tree.getroot()
    simParam_tag = root.find('.//' + tagName)
except FileNotFoundError:
    print(f"-----ERROR-----: bpmn file not found")
    sys.exit()
except ET.ParseError:
    print(f"-----ERROR-----: bpmn file bad syntax")
    sys.exit()
except Exception as e:
    print(f"An error occurred: {e}")
    sys.exit()

if simParam_tag is not None:
    # Convert to string and remove the <simParam> and </simParam> tags
    simParam_str = ET.tostring(simParam_tag, encoding='unicode')
    simParam_str = simParam_str.replace('<'+tagName+'>', '').replace('</'+tagName+'>', '')
    with open(simParamPath, "w") as outfile:
        outfile.write(simParam_str)


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
with open(bpmnPath, "w") as outfile:
    json.dump(bpmnDictionary, outfile, indent=4)