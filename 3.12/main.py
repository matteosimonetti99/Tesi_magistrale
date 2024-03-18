import parsingAgain
import json
import sys
import simpy
import random
from collections import deque


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

    def run_node(self, node_id, parallel_counter=0):
    node = self.process_details['node_details'][node_id]

    if node['type'] == 'startEvent':
        yield self.env.timeout(1)
    elif node['type'] == 'task':
        yield self.env.timeout(1)  # replace with your task duration
        next_node_id = node['next'][0]
        yield from self.run_node(next_node_id, parallel_counter)
    elif node['type'] == 'exclusiveGateway':
        # XOR logic: choose one path randomly
        next_node_id = random.choice(node['next'])
        yield from self.run_node(next_node_id, parallel_counter)
    elif node['type'] == 'parallelGateway':
        # AND logic: run all paths concurrently and wait for all to finish, process is created for each path to ensure parallelism
        events = []
        parallel_counter += 1  # Increment the counter when an opening gateway is encountered
        for next_node_id in node['next']:
            queue = deque([next_node_id])  # Only add the next_node_id to the queue
            while queue:
                current_node_id = queue.popleft()
                current_node = self.process_details['node_details'][current_node_id]
                if current_node['type'] == 'parallelGateway':
                    parallel_counter += 1  # Increment the counter when an opening gateway is encountered
                if not (current_node['type'] == 'parallelGateway_close' and parallel_counter == 0):
                    queue.extend(current_node['next'])
                events.append(self.env.process(self.run_node(current_node_id, parallel_counter))) # parallel counter is passed to keep track of nesting level for what is called next
        yield self.env.AllOf(events)
    elif node['type'] == 'parallelGateway_close':
        parallel_counter -= 1  # Decrement the counter when a closing gateway is encountered
        if parallel_counter != 0:
            return
    elif node['type'] == 'subProcess':
        # Run the subprocess
        start_node_id = next(sub_node_id for sub_node_id, sub_node in node['subprocess_details'].items() if sub_node['type'] == 'startEvent')
        yield from self.run_node(start_node_id, parallel_counter)
        # After the subprocess is executed, continue with the node next to the subprocess
        next_node_id = node['next'][0]
        yield from self.run_node(next_node_id, parallel_counter)
    elif node['type'] == 'endEvent':
        return

def simulate_bpmn(bpmn_dict):
    env = simpy.Environment()
    for participant_id, participant in bpmn_dict['collaboration']['participants'].items():
        process_details = bpmn_dict['process_elements'][participant['processRef']]
        Process(env, participant['name'], process_details)
    env.run()


# replace with your bpmn_dict
simulate_bpmn(bpmn)

