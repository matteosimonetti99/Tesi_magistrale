import parsingAgain
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
        diagbp = json.load(file)
except FileNotFoundError:
    print(f"-----ERROR-----: simulation parameters not found")
    sys.exit()
except json.JSONDecodeError:
    print(f"-----ERROR-----: simulation parameters bad syntax")
    sys.exit()
except Exception as e:
    print(f"An error occurred: {e}")
    sys.exit()

num_instances = sum(instance['count'] for instance in data['processInstances'])
instance_types = data['processInstances']
delay_between_instances = data['arrivalRateDistribution'] #bisogna accedere a type, mean, arg1, arg2
xor_probabilities = {flow['elementId']: float(flow['executionProbability']) for flow in data['sequenceFlows']}
task_durations = {element['elementId']: element['durationDistribution'] for element in data['elements']} #bisogna accedere a type, mean, arg1, arg2

#qui si chiama la func in timeCalculator, si chiama singolarmente per delay e foreach element in task_durations. Nel secondo si sostituisce il valore per ogni entry del dizionario
#nel primo si crea un array di len=num_instances che contenga i vari delay



class Process:
    executed_nodes = set()  # Class variable to keep track of executed nodes
    def __init__(self, env, name, process_details, start_delay=0, instance_type="default"):
        self.env = env
        self.name = name
        self.process_details = process_details
        self.stack=[]
        self.start_delay = start_delay
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
            yield self.env.timeout(task_durations[node_id]) # task duration is used here
            Process.executed_nodes.add(node_id)
            self.printState(node,node_id)
            next_node_id = node['next'][0]
            yield from self.run_node(next_node_id, subprocess_node)
        elif node['type'] == 'exclusiveGateway':
            # XOR logic
            next_node_id = random.choice(node['next'])
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
    #add diagbp e da lì num_instances, delay_between_instances (gestisci linear e vari altri tipi, per ora è impostato come solo linear), instanceType, prob xor, task times.
    env = simpy.Environment()
    for i in range(num_instances):
        #num_instances è la somma di tutti gli instance type.
        for participant_id, participant in bpmn_dict['collaboration']['participants'].items():
            process_details = bpmn_dict['process_elements'][participant['processRef']]
            Process(env, participant['name'], process_details, start_delay=delay_between_instances[i], instance_type=prendiDaDiagbp)
    env.run()


simulate_bpmn(bpmn)

