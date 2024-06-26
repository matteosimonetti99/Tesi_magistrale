import sys
from bpmn_python import bpmn_diagram_rep as diagram
import xml.etree.ElementTree as ET
import json
import sys
import os
import diagbpTagGenerator


ET.register_namespace('', 'http://www.omg.org/spec/BPMN/20100524/MODEL')
ET.register_namespace('bpmndi', 'http://www.omg.org/spec/BPMN/20100524/DI')
ET.register_namespace('dc', 'http://www.omg.org/spec/DD/20100524/DC')
ET.register_namespace('di', 'http://www.omg.org/spec/DD/20100524/DI')


tagName="diagbp"
extraPath="../json/extra.json"
diagbpPath="../json/diagbp.json"
bpmnPath="../json/bpmn.json"

json_dir = "../json"  # Relative path to the json directory
# Create the directory if it doesn't exist
if not os.path.exists(json_dir):
    os.makedirs(json_dir)

import sys
from bpmn_python import bpmn_diagram_rep as diagram
import xml.etree.ElementTree as ET
import json
import sys
import os
import diagbpTagGenerator
import time
import subprocess 

ET.register_namespace('', 'http://www.omg.org/spec/BPMN/20100524/MODEL')
ET.register_namespace('bpmndi', 'http://www.omg.org/spec/BPMN/20100524/DI')
ET.register_namespace('dc', 'http://www.omg.org/spec/DD/20100524/DC')
ET.register_namespace('di', 'http://www.omg.org/spec/DD/20100524/DI')

tagName = "diagbp"
extraPath = "../json/extra.json"
diagbpPath = "../json/diagbp.json"
bpmnPath = "../json/bpmn.json"

json_dir = "../json"
if not os.path.exists(json_dir):
    os.makedirs(json_dir)

# Create /app/shared if it doesn't exist
shared_dir = "../shared"
if not os.path.exists(shared_dir):
    os.makedirs(shared_dir)

def process_bpmn(name):
    try:
        tree = ET.parse(name)
        root = tree.getroot()
        diagbp_tag = root.find('.//' + tagName)
    except FileNotFoundError:
        print(f"-----ERROR-----: bpmn file not found: {name}")
        print(f"Detailed Error: {e}") 
        print(f"Current Working Directory: {os.getcwd()}")
    except ET.ParseError:
        print(f"-----ERROR-----: bpmn file bad syntax in bpmnParsing.py")
        sys.exit()
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit()


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
            node_type = node_info.get('type', 'Unknown')
            node_subtype = None
            attached_to_id = None
            if node_type == 'intermediateCatchEvent' or node_type == 'boundaryEvent' or node_type == 'endEvent':
                # Get the specific type of the intermediate catch event
                event_definitions = node_info.get('event_definitions', [])
                for event_definition in event_definitions:
                    node_subtype = event_definition.get('definition_type', 'Unknown')
            if node_type == 'boundaryEvent':
                attached_to_id = node_info.get('attachedToRef')
            node_details[node_id] = {
                'name': node_info.get('node_name', 'Unnamed'),
                'type': node_type,
                'subtype': node_subtype,
                'attached_to': attached_to_id,
            }
            if node_info.get('type', 'Unknown') == 'subProcess':
                # Add subprocess details
                subprocess_details = {}
                for child_node_id in node_info.get('node_ids', []):
                    child_node_info = bpmnGraph.diagram_graph.node[child_node_id]
                    child_node_type = child_node_info.get('type', 'Unknown')
                    child_node_subtype = None
                    if child_node_type == 'intermediateCatchEvent' or child_node_type == 'boundaryEvent' or child_node_type == 'endEvent':
                        # Get the specific type of the intermediate catch event
                        child_event_definitions = child_node_info.get('event_definitions', [])
                        for child_event_definition in child_event_definitions:
                            child_node_subtype = child_event_definition.get('definition_type', 'Unknown')
                    subprocess_details[child_node_id] = {
                        'name': child_node_info.get('node_name', 'Unnamed'),
                        'type': child_node_type,
                        'subtype': child_node_subtype,
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

    stopFlag=False
    # Print the dictionary
    with open(bpmnPath, "w") as outfile:
        json.dump(bpmnDictionary, outfile, indent=4)

    if os.path.exists(extraPath):
        pass
    elif diagbp_tag is not None:
        # Convert to string and remove the <diagbp> and </diagbp> tags
        diagbp_str = ET.tostring(diagbp_tag, encoding='unicode')
        diagbp_str = diagbp_str.replace('<'+tagName+'>', '').replace('</'+tagName+'>', '')
        with open(diagbpPath, "w") as outfile:
            outfile.write(diagbp_str)
    else:
        """
        diagbpTagGenerator.diagbp(diagbpPath, bpmnDictionary)
        with open(diagbpPath, 'r') as f:
            diagbp_text = f.read()
        with open(name, 'r') as file:
            bpmn_content = file.read()
        bpmn_content = bpmn_content.replace('</bpmn:definitions>', f'<diagbp>{diagbp_text}</diagbp>\n</bpmn:definitions>')
        confirm=""
        while confirm=="":
            confirm = input("Do you want to save those simulation parameters into the bpmn file? (Y/N) ")
        if (confirm=="y" or confirm=="Y"):
            with open(name, 'w') as file:
                file.write(bpmn_content)
        """
        stopFlag=True
    if not stopFlag:
        cmd = ["/usr/local/python3.11/bin/python3.11", "/app/3.11/main.py"] 
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, universal_newlines=True, encoding='utf-8')
        print(process.stdout)


if __name__ == "__main__":
    while True: 
        for filename in os.listdir(shared_dir):
            if filename.endswith(".bpmn"):
                full_path = "../shared/"+filename
                process_bpmn(full_path)
                os.remove(full_path)
        time.sleep(1)