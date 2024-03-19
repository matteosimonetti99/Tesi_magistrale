import parsingAgain
import json
import sys
import simpy
from collections import deque

#to remove, credo
import random
import time



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
        start_node_id = next((node_id for node_id, node in self.process_details['node_details'].items() if node['type'] == 'startEvent'), None)
        if start_node_id is None:
            return
        yield from self.run_node(start_node_id)


    def run_node(self, node_id, parallel_counter=0, subprocess_node=None):
        if subprocess_node is None:
            node = self.process_details['node_details'][node_id]
        else:
            node = self.process_details['node_details'][subprocess_node]['subprocess_details'][node_id]

        print(f"Running node: {node_id} ({node['name']}), type: {node['type']}, pool: {self.name}. time: {self.env.now}")

        if node['type'] == 'startEvent':
            yield self.env.timeout(1)
            next_node_id = node['next'][0]
            yield from self.run_node(next_node_id, parallel_counter, subprocess_node)
        elif node['type'] == 'task':
            yield self.env.timeout(1) # replace with your task duration
            next_node_id = node['next'][0]
            yield from self.run_node(next_node_id, parallel_counter, subprocess_node)
        elif node['type'] == 'exclusiveGateway':
            # XOR logic
            next_node_id = random.choice(node['next'])
            yield from self.run_node(next_node_id, parallel_counter, subprocess_node)
        elif node['type'] == 'parallelGateway':
            # AND logic: run all paths concurrently and wait for all to finish, process is created for each path to ensure parallelism
            events = []
            for next_node_id in node['next']:
                queue = deque([next_node_id])
                parallel_counter_path = parallel_counter + 1  # Increment the counter when an opening gateway is encountered
                while queue:
                    current_node_id = queue.popleft()
                    if subprocess_node is None: #check if we are in a subprocess and takes data accordingly
                        current_node = self.process_details['node_details'][current_node_id]
                    else:
                        current_node = self.process_details['node_details'][subprocess_node]['subprocess_details'][current_node_id]

                    if current_node['type'] == 'parallelGateway':
                        parallel_counter_path += 1  # Increment the counter when an opening gateway is encountered
                    elif current_node['type'] == 'parallelGateway_close':
                        parallel_counter_path -= 1
                    if not (current_node['type'] == 'parallelGateway_close' and parallel_counter_path == 0):
                        queue.extend(current_node['next'])
                        print(queue)
                        print(parallel_counter_path)
                    else:
                        next_node_after_parallel = current_node['next'][0]
                    events.append(self.env.process(self.run_node(current_node_id, parallel_counter_path, subprocess_node)))  # parallel counter is passed to keep track of nesting level for what is called next
            yield self.env.all_of(events)
            yield from self.run_node(next_node_after_parallel, parallel_counter, subprocess_node)

        elif node['type'] == 'subProcess':
            start_node_id = next(sub_node_id for sub_node_id, sub_node in node['subprocess_details'].items() if sub_node['type'] == 'startEvent')
            yield from self.run_node(start_node_id, parallel_counter, subprocess_node=node_id)
            next_node_id = node['next'][0]
            # After the subprocess is executed, continue with the node next to the subprocess
            yield from self.run_node(next_node_id, parallel_counter)
        elif node['type'] == 'endEvent':
            return

        """elif node['type'] == 'parallelGateway_close':
            print("parallelGateway_close")
            parallel_counter -= 1 # Decrement the counter when a closing gateway is encountered
            if parallel_counter != 0:
                return"""


def simulate_bpmn(bpmn_dict):
    env = simpy.Environment()
    for participant_id, participant in bpmn_dict['collaboration']['participants'].items():
        process_details = bpmn_dict['process_elements'][participant['processRef']]
        Process(env, participant['name'], process_details)
    env.run()


# replace with your bpmn_dict
simulate_bpmn(bpmn)

