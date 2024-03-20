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


    def run_node(self, node_id, subprocess_node=None):
        if subprocess_node is None:
            node = self.process_details['node_details'][node_id]
        else:
            node = self.process_details['node_details'][subprocess_node]['subprocess_details'][node_id]

        print(f"Running node: {node_id} ({node['name']}), type: {node['type']}, pool: {self.name}. time: {self.env.now}")

        if node['type'] == 'startEvent':
            yield self.env.timeout(1)
            next_node_id = node['next'][0]
            yield from self.run_node(next_node_id, subprocess_node)
        elif node['type'] == 'task':
            yield self.env.timeout(1) # replace with your task duration
            next_node_id = node['next'][0]
            yield from self.run_node(next_node_id, subprocess_node)
        elif node['type'] == 'exclusiveGateway':
            # XOR logic
            next_node_id = random.choice(node['next'])
            yield from self.run_node(next_node_id, subprocess_node)
        elif node['type'] == 'parallelGateway':
            # AND logic: run all paths concurrently and wait for all to finish, process is created for each path to ensure parallelism
            events = [self.env.process(self.run_node(next_node_id, subprocess_node)) for next_node_id in node['next']]
            yield self.env.all_of(events)

        elif node['type'] == 'parallelGateway_close':
            return
            #yield from self.run_node(next_node_after_parallel, subprocess_node)

        elif node['type'] == 'subProcess':
            start_node_id = next(sub_node_id for sub_node_id, sub_node in node['subprocess_details'].items() if sub_node['type'] == 'startEvent')
            yield from self.run_node(start_node_id, subprocess_node=node_id)
            next_node_id = node['next'][0]
            # After the subprocess is executed, continue with the node next to the subprocess
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

