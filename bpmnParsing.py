import bpmn_python.bpmn_diagram_rep as diagram
import xml.etree.ElementTree as ET

name="ch7_CreditAppSimulation.bpmn"

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
            'name': node_info.get('name', 'Unnamed'),
            'type': node_info.get('type', 'Unknown'),
        }
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
print(bpmnDictionary)


#python 3.6
#TODO: controllare se simpy funziona con python 3.6 altrimenti parser lo si tiene in 3.6 e simpy lo si usa in versione differente tipo dockerizzando o simili.
# Poi aggiungere parsing per tag privato simulaizone
# Fare core simulation con simpy, chiedere info su tag privato per implementare direttamente quella sintassi