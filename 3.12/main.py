import parsingAgain
import timeCalculator
import json
import sys
import simpy
import numpy as np
from collections import deque

#to remove, credo
import random
import time



diagbpPath="../json/diagbp.json"
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
    with open(diagbpPath, "r") as file:
        diagbp = json.load(file) #Simulations parameters
except FileNotFoundError:
    print(f"-----ERROR-----: simulation parameters not found")
    sys.exit()
except json.JSONDecodeError:
    print(f"-----ERROR-----: simulation parameters bad syntax")
    sys.exit()
except Exception as e:
    print(f"An error occurred: {e}")
    sys.exit()




num_instances = sum(instance['count'] for instance in diagbp['processInstances'])
instance_types = diagbp['processInstances']
xor_probabilities = {flow['elementId']: float(flow['executionProbability']) for flow in diagbp['sequenceFlows']}

# Generate the delays
delay_between_instances = diagbp['arrivalRateDistribution'] #array contains: type, mean, arg1, arg2
delays = []
total_delay = 0
for _ in range(num_instances):
    delay = timeCalculator.convert_to_seconds(delay_between_instances)
    total_delay += delay #each delay is therefore equal to itself + the previous delay
    delays.append(total_delay)

task_durations = {element['elementId']: element['durationDistribution'] for element in diagbp['elements']} #array contains: type, mean, arg1, arg2



class Process:
    executed_nodes = set()  # Class variable to keep track of executed nodes
    def __init__(self, env, name, process_details, start_delay=0, instance_type="default"):
        self.env = env
        self.name = name
        self.process_details = process_details
        self.stack=[]
        self.start_delay = start_delay
        self.instance_type = instance_type
        self.action = env.process(self.run())

    def printState(self, node, node_id):
        print(f"Running node: {node_id} ({node['name']}), type: {node['type']}, pool: {self.name}. time: {self.env.now}")

    def run(self):
        yield self.env.timeout(self.start_delay) #delay start because of arrival rate.
        start_node_id = next((node_id for node_id, node in self.process_details['node_details'].items() if node['type'] == 'startEvent'), None)
        if start_node_id is None:
            return
        yield from self.run_node(start_node_id)


    def run_node(self, node_id, subprocess_node=None):
        if subprocess_node is None:
            node = self.process_details['node_details'][node_id]
        else:
            node = self.process_details['node_details'][subprocess_node]['subprocess_details'][node_id]

        if node['type'] == 'startEvent':
            yield self.env.timeout(0)
            next_node_id = node['next'][0]
            self.printState(node,node_id)
            yield from self.run_node(next_node_id, subprocess_node)

        elif node['type'] == 'task':
            if len(node['previous'])>0:
                while not all(prev_node in Process.executed_nodes for prev_node in node['previous']):
                    yield self.env.timeout(1)
            taskTime=timeCalculator.convert_to_seconds(task_durations[node_id]) # task duration is used here, it is passed before to a converter that transforms the type/mean/arg1/arg2 to a value in seconds, this value the task duration is always different in each instance
            yield self.env.timeout(taskTime) 
            Process.executed_nodes.add(node_id)
            self.printState(node,node_id)
            next_node_id = node['next'][0]
            yield from self.run_node(next_node_id, subprocess_node)

        elif node['type'] == 'exclusiveGateway': #TODO integra instance_type
            # Get the flows from bpmn.json that start from the current XOR
            flows_from_xor = [flow for flow in bpmn['sequence_flows'].values() if flow['sourceRef'] == node_id]
            # Create a dictionary mapping target nodes to their probabilities
            node_probabilities = {flow['targetRef']: float(diagbp['sequenceFlows'][flow['elementId']]['executionProbability']) for flow in flows_from_xor}
            next_node_id = np.random.choice(list(node_probabilities.keys()), p=list(node_probabilities.values()))
            self.printState(node,node_id)
            yield from self.run_node(next_node_id, subprocess_node)

        elif node['type'] == 'parallelGateway':
            # AND logic: run all paths concurrently and wait for all to finish, process is created for each path to ensure parallelism
            events = [self.env.process(self.run_node(next_node_id, subprocess_node)) for next_node_id in node['next']]
            self.printState(node,node_id)
            yield self.env.all_of(events)
            # When all_of is done, proceed with the node after the close
            next_node_after_parallel = self.stack.pop()
            yield from self.run_node(next_node_after_parallel, subprocess_node)

        elif node['type'] == 'parallelGateway_close':
            self.stack.append(node['next'][0])
            self.printState(node,node_id)
            return
            
        elif node['type'] == 'subProcess':
            start_node_id = next(sub_node_id for sub_node_id, sub_node in node['subprocess_details'].items() if sub_node['type'] == 'startEvent')
            self.printState(node,node_id)
            yield from self.run_node(start_node_id, subprocess_node=node_id)
            next_node_id = node['next'][0]
            # After the subprocess is executed, continue with the node next to the subprocess
            yield from self.run_node(next_node_id)

        elif node['type'] == 'endEvent':
            return


def simulate_bpmn(bpmn_dict):
    instance_index = 0
    instance_count = 0

    env = simpy.Environment()
    for i in range(num_instances):
        instance_type = instance_types[instance_index]['type']

        for participant_id, participant in bpmn_dict['collaboration']['participants'].items():
            process_details = bpmn_dict['process_elements'][participant['processRef']]
            Process(env, participant['name'], process_details, start_delay=delays[i], instance_type=instance_type)

        instance_count += 1
        if instance_count >= instance_types[instance_index]['count']:
            instance_index += 1
            instance_count = 0
    env.run()


simulate_bpmn(bpmn)

