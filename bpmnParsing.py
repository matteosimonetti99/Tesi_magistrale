from bpmn_python import BpmnParser

def parse_bpmn(filepath):
  """
  Parses a BPMN file and returns a nested dictionary representing the process.

  Args:
      filepath: Path to the BPMN file.

  Returns:
      A nested dictionary representing the BPMN process.
  """
  # Load the BPMN diagram
  diagram = BpmnParser.from_xml_file(filepath)

  # Initialize the result dictionary
  process_data = {}

  # Function to recursively parse elements and their attributes
  def parse_element(element, parent_id=None):
    element_data = {
      'name': element.name,
      'type': element.__class__.__name__,
    }

    # Extract element specific attributes
    if element.type == 'Task':
      element_data['duration'] = element.duration

    elif element.type in ['ExclusiveGateway', 'InclusiveGateway']:
      element_data['conditions'] = {}
      for condition in element.outgoing:
        element_data['conditions'][condition.condition_expression] = condition.target_ref

    # Add next elements for tasks and gateways
    if element.type in ['Task', 'Gateway']:
      next_elements = []
      for outgoing in element.outgoing:
        next_elements.append(outgoing.target_ref)
      element_data['next'] = next_elements

    # Recursively parse child elements
    for child in element.children:
      child_id = child.id
      element_data[child_id] = parse_element(child, child_id)

    # Update parent data with this element data
    if parent_id:
      process_data[parent_id][child_id] = element_data
    else:
      process_data[element.id] = element_data

    return element_data

  # Start parsing from the start event
  start_event = diagram.find_element_by_type('StartEvent')[0]
  parse_element(start_event)

  return process_data

# Example usage
filepath = "your_bpmn_file.bpmn"
process_data = parse_bpmn(filepath)

# Access data structure:
# process_data contains the nested dictionary representing the BPMN process
# Each entry represents an element (activity or gateway) with its details
# You can traverse the structure to access specific information
