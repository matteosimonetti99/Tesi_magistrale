import parsingAgain
import json
import sys
import simpy


simParamPath="../json/simParam.json"
bpmnPath="../json/bpmn.json"

parsingAgain.parse_again()

try:
    with open(bpmnPath, "r") as file:
        bpmn = json.load(file)
except FileNotFoundError:
    print(f"-----ERROR-----: bpmn file not found")
    sys.exit()
except json.JSONDecodeError:
    print(f"-----ERROR-----: bpmn file bad syntax")
    sys.exit()
except Exception as e:
    print(f"An error occurred: {e}")
    sys.exit()

try:
    with open(simParamPath, "r") as file:
        simParam = json.load(file)
except FileNotFoundError:
    print(f"-----ERROR-----: simulation parameters not found")
    sys.exit()
except json.JSONDecodeError:
    print(f"-----ERROR-----: simulation parameters bad syntax")
    sys.exit()
except Exception as e:
    print(f"An error occurred: {e}")
    sys.exit()




class Process:
    def __init__(self, env, name, process_details):
        self.env = env
        self.name = name
        self.process_details = process_details
        self.action = env.process(self.run())

    def run(self):
        # Start from the startEvent
        start_node_id = next(node_id for node_id, node in self.process_details['node_details'].items() if node['type'] == 'startEvent')
        yield from self.run_node(start_node_id)

    def run_node(self, node_id):
        node = self.process_details['node_details'][node_id]
        if node['type'] == 'startEvent':
            yield self.env.timeout(1)
        elif node['type'] == 'task':
            yield self.env.timeout(1)  # replace with your task duration
        elif node['type'] == 'exclusiveGateway':
            # XOR logic: choose one path randomly
            next_node_id = random.choice(node['next'])
            yield from self.run_node(next_node_id)
        elif node['type'] == 'parallelGateway':
            # AND logic: run all paths sequentially
            for next_node_id in node['next']:
                yield from self.run_node(next_node_id)
        elif node['type'] == 'subProcess':
            # Run the subprocess
            for sub_node_id in node['subprocess_details']['node_ids']:
                yield from self.run_node(sub_node_id)
        elif node['type'] == 'endEvent':
            return

        # Run the next nodes
        for next_node_id in node['next']:
            yield from self.run_node(next_node_id)


def simulate_bpmn(bpmn_dict):
    env = simpy.Environment()
    for participant_id, participant in bpmn_dict['collaboration']['participants'].items():
        process_details = bpmn_dict['process_elements'][participant['processRef']]
        Process(env, participant['name'], process_details)
    env.run()

# replace with your bpmn_dict
simulate_bpmn(bpmn_dict)
