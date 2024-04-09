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

#sys.setrecursionlimit(100000)



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




num_instances = sum(int(instance['count']) for instance in diagbp['processInstances'])
print("NUM_INSTANCES: "+ str(num_instances))
instance_types = diagbp['processInstances']
xor_probabilities = {flow['elementId']: float(flow['executionProbability']) for flow in diagbp['sequenceFlows']}

# Generate the delays
delay_between_instances = diagbp['arrivalRateDistribution'] #array contains: type, mean, arg1, arg2
delays = [0]
total_delay = 0
for _ in range(num_instances-1):
    delay = timeCalculator.convert_to_seconds(delay_between_instances)
    total_delay += delay #each delay is therefore equal to itself + the previous delay
    delays.append(total_delay)

task_durations = {element['elementId']: element['durationDistribution'] for element in diagbp['elements']} #array contains: type, mean, arg1, arg2



class Process:
    executed_nodes = {}  # make executed_nodes a dictionary of sets
    #parallelTimes = {}
    #parallelCounter = 0
    def __init__(self, env, name, process_details, num, start_delay=0, instance_type="default"):
        self.env = env
        self.name = name
        self.process_details = process_details
        self.stack=[]
        self.start_delay = start_delay
        self.instance_type = instance_type
        self.num = num
        self.action = env.process(self.run())
        #Process.parallelTimes[self.num]={}
        Process.executed_nodes[self.num] = set()  # Add a new set for this instance

    def printState(self, node, node_id, inSubProcess):
        if node['type'] == 'subProcess':
            print(f"#{self.num}|{self.name}: {node_id} (subprocess {node['name']} just started), instance_type:{self.instance_type}. time: {self.env.now}.")
        elif inSubProcess == True:
            print(f"#{self.num}|{self.name} (inside subProcess): {node_id} ({node['name']}), type: {node['type']}, instance_type:{self.instance_type}. time: {self.env.now}.")
        else:
            print(f"#{self.num}|{self.name}: {node_id} ({node['name']}), type: {node['type']}, instance_type:{self.instance_type}. time: {self.env.now}.")

    def run(self):
        yield self.env.timeout(self.start_delay) #delay start because of arrival rate.
        start_node_id = next((node_id for node_id, node in self.process_details['node_details'].items() if node['type'] == 'startEvent'), None)
        if start_node_id is None:
            return
        yield from self.run_node(start_node_id)


    def run_node(self, node_id, subprocess_node=None):
        if subprocess_node is None:
            node = self.process_details['node_details'][node_id]
            printFlag=False
        else:
            node = self.process_details['node_details'][subprocess_node]['subprocess_details'][node_id]
            printFlag=True

        if node['type'] == 'startEvent':
            next_node_id = node['next'][0]
            if len(node['previous'])>0:
                while not all(prev_node in Process.executed_nodes[self.num] for prev_node in node['previous']):
                    yield self.env.timeout(1)
            self.printState(node,node_id,printFlag)
            yield from self.run_node(next_node_id, subprocess_node)

        elif node['type'] == 'task':
            if len(node['previous'])>0:
                while not all(prev_node in Process.executed_nodes[self.num] for prev_node in node['previous']):
                    yield self.env.timeout(1)
            taskTime=timeCalculator.convert_to_seconds(task_durations[node_id]) # task duration is used here, it is passed before to a converter that transforms the type/mean/arg1/arg2 to a value in seconds, this value the task duration is always different in each instance
            yield self.env.timeout(taskTime) 
            Process.executed_nodes[self.num].add(node_id)
            self.printState(node,node_id,printFlag)
            next_node_id = node['next'][0]
            yield from self.run_node(next_node_id, subprocess_node)

        elif node['type'] == 'exclusiveGateway': #TODO integra instance_type
            # Get the flows from bpmn.json that start from the current XOR
            flows_from_xor = [(flow_id, flow) for flow_id, flow in bpmn['sequence_flows'].items() if flow['sourceRef'] == node_id]
            # Create a dictionary mapping target nodes to their probabilities
            node_probabilities = {}
            for flow_id, flow in flows_from_xor:
                # Find the corresponding flow in diagbp.json
                diagbp_flow = next((item for item in diagbp['sequenceFlows'] if item['elementId'] == flow_id), None)
                if diagbp_flow is not None:
                    node_probabilities[flow['targetRef']] = float(diagbp_flow['executionProbability'])
            # Check if node_probabilities is empty, if yes then the xor has only one next elem.
            if not node_probabilities:
                next_node_id = node['next'][0]
            else:
                next_node_id = np.random.choice(list(node_probabilities.keys()), p=list(node_probabilities.values()))
            self.printState(node,node_id,printFlag)
            yield from self.run_node(next_node_id, subprocess_node)

        elif node['type'] == 'parallelGateway':
            # AND logic: run all paths concurrently and wait for all to finish, process is created for each path to ensure parallelism
            events = []
            for next_node_id in node['next']:
                process = self.env.process(self.run_node(next_node_id, subprocess_node, ASDSA))
                events.append(process)
            self.printState(node,node_id,printFlag)
            yield self.env.all_of(events)
            # When all_of is done, proceed with the node after the close
            next_node_after_parallel = self.stack.pop()
            yield from self.run_node(next_node_after_parallel, subprocess_node)

        elif node['type'] == 'parallelGateway_close':
            self.stack.append(node['next'][0])
            #self.printState(node,node_id,printFlag)
            return
            
        elif node['type'] == 'subProcess':
            if len(node['previous'])>0:
                while not all(prev_node in Process.executed_nodes[self.num] for prev_node in node['previous']):
                    yield self.env.timeout(1)
            start_node_id = next(sub_node_id for sub_node_id, sub_node in node['subprocess_details'].items() if sub_node['type'] == 'startEvent')
            self.printState(node,node_id,printFlag)
            yield from self.run_node(start_node_id, node_id)
            Process.executed_nodes[self.num].add(node_id)
            next_node_id = node['next'][0]
            # After the subprocess is executed, continue with the node next to the subprocess
            yield from self.run_node(next_node_id, None)
        elif node['type'] == 'intermediateThrowEvent':
            next_node_id = node['next'][0]
            Process.executed_nodes[self.num].add(node_id)
            self.printState(node,node_id,printFlag)
            yield from self.run_node(next_node_id, subprocess_node)
            return
        elif node['type'] == 'intermediateCatchEvent':
            if node['subtype'] == 'messageEventDefinition':
                next_node_id = node['next'][0]
                if len(node['previous'])>0: #wait for msg
                    while not all(prev_node in Process.executed_nodes[self.num] for prev_node in node['previous']):
                        yield self.env.timeout(1)
                Process.executed_nodes[self.num].add(node_id)
                self.printState(node,node_id,printFlag)
                yield from self.run_node(next_node_id, subprocess_node)
                return
            else:
                next_node_id = node['next'][0]
                Process.executed_nodes[self.num].add(node_id)
                self.printState(node,node_id,printFlag)
                yield self.env.timeout(1) #TODO: CAMBIARE 1 IN DURATA DA PRENDERE DA PARAM DEL TIMER
                yield from self.run_node(next_node_id, subprocess_node)
                return

        elif node['type'] == 'endEvent':
            self.printState(node,node_id,printFlag)
            return


def simulate_bpmn(bpmn_dict):
    instance_index = 0
    instance_count = 0

    env = simpy.Environment()
    for i in range(num_instances):
        instance_type = instance_types[instance_index]['type']

        for participant_id, participant in bpmn_dict['collaboration']['participants'].items():
            process_details = bpmn_dict['process_elements'][participant['processRef']]
            Process(env, participant['name'], process_details, num=i+1, start_delay=delays[i], instance_type=instance_type)

        instance_count += 1
        if instance_count >= int(instance_types[instance_index]['count']):
            instance_index += 1
            instance_count = 0
    env.run()


simulate_bpmn(bpmn)

