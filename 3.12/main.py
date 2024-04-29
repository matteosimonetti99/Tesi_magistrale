import parsingAgain
import timeCalculator
import json
import sys
import simpy
import numpy as np
from collections import deque
from datetime import datetime, timedelta
from datetime import time as dt_time
import pm4py
import pandas as pd
import csv


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

#csv log
csv_file = "../log.csv"
fields = ['traceId', 'activity', 'timestamp', 'status', 'nodeType', 'poolName','instanceType']
rows=[]
logging_opt=diagbp['logging_opt']
logging_opt = (logging_opt == 1)



#Put those 2 to true to have the log in console of resources locked and unlocked and timetable management
resourceLog=False
logTimetable=False
logCosts=True

#other glob var
num_instances = sum(int(instance['count']) for instance in diagbp['processInstances'])
print("NUM_INSTANCES: "+ str(num_instances))
instance_types = diagbp['processInstances']
xor_probabilities = {flow['elementId']: float(flow['executionProbability']) for flow in diagbp['sequenceFlows']}
resources = diagbp['resources']
#global_resource global var is in simulate_bpmn function at the end of the code, it is passed to process as globalResources
timetables = diagbp['timetables']
catchEvents = diagbp['catchEvents']

# Generate the delays
delay_between_instances = diagbp['arrivalRateDistribution'] #array contains: type, mean, arg1, arg2
delays = [0]
total_delay = 0
for _ in range(num_instances-1):
    delay = timeCalculator.convert_to_seconds(delay_between_instances)
    total_delay += delay #each delay is therefore equal to itself + the previous delay
    delays.append(total_delay)

task_durations = {element['elementId']: element['durationDistribution'] for element in diagbp['elements']} #dict contains: type, mean, arg1, arg2
task_resources = {element['elementId']: element['resourceIds'] for element in diagbp['elements']} #array contains dicts with each: resourceName, amountNeeded, groupId
task_costs = {element['elementId']: element['fixedCost'] for element in diagbp['elements']} #array contains dicts with each: resourceName, amountNeeded, groupId


totalCost={} #task_costs are summed here
timeUsedPerResource={} #resources time being used are summed here
class Process:
    executed_nodes = {}  # make executed_nodes a dictionary of sets
    startDateTime = diagbp['startDateTime']
    terminateEndEvent={} # dictionary of true or false, to tell if that process has been terminated or not
    subprocessTerminate={} #this is used for subprocesses for terminate end events
    def __init__(self, env, name, process_details, num, globalResources, start_delay=0, instance_type="default"):
        self.env = env
        self.name = name
        self.process_details = process_details
        self.stack=[]
        self.start_delay = start_delay
        self.instance_type = instance_type
        self.num = num
        self.action = env.process(self.run())
        self.costThresholds = {element['elementId']: int(element['costThreshold']) if element['costThreshold'] != '' else None for element in diagbp['elements']} 
        self.durationThresholds={element['elementId']: element['durationThreshold'] if element['durationThreshold'] != '' else None for element in diagbp['elements']}
        self.durationThresholdTimeUnits={element['elementId']: element['durationThresholdTimeUnit'] for element in diagbp['elements']}

        for element_id, time_unit in self.durationThresholdTimeUnits.items(): #edit duratioThresholds multiplying by self.durationThresholdTimeUnits
                    threshold = self.durationThresholds.get(element_id)
                    if threshold is not None:
                        if time_unit == 'minutes':
                            self.durationThresholds[element_id] = float(self.durationThresholds[element_id])*60
                        elif time_unit == 'hours':
                            self.durationThresholds[element_id] = float(self.durationThresholds[element_id])*3600
                        elif time_unit == 'days':
                            self.durationThresholds[element_id] = float(self.durationThresholds[element_id])*86400
        self.subprocessInternalError = {} #used in error end event
        self.subprocessExternalException = {}
        Process.terminateEndEvent[self.num] = False
        Process.subprocessTerminate[self.num] = {}
        totalCost[self.num]=0.0
        #resources is a dict with name as key and a tuple made of simpy resource, cost and timetable.
        self.resources = globalResources
        Process.executed_nodes[self.num] = set() 
        for resource_name, resource_info in self.resources.items():
            resource, cost_per_hour, timetable_name = resource_info
            timeUsedPerResource[resource_name]=0.0
            #print(f"Resource Name: {resource_name}, Capacity: {resource.capacity}")
    
    def is_in_timetable(self, timetable_name):
        start_time = Process.startDateTime
        start_time = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S")
        current_time = start_time + timedelta(seconds=self.env.now)
        # Get the timetable from the global timetables variable
        timetable = next(t for t in timetables if t['name'] == timetable_name)

        # Extract the current time's hour and minute
        current_hour_minute_second = dt_time(current_time.hour, current_time.minute, current_time.second)
        
        # Check if the current time falls within any of the rules in the timetable
        for rule in timetable['rules']:
            timeFlag=False
            from_hour, from_minute, from_second = map(int, rule['fromTime'].split(':'))
            to_hour, to_minute, to_second = map(int, rule['toTime'].split(':'))

            from_time = dt_time(from_hour, from_minute, from_second)
            to_time = dt_time(to_hour, to_minute, to_second)
            from_day = rule['fromWeekDay'].upper()
            to_day = rule['toWeekDay'].upper()
            if logTimetable:
                print(str(from_time)+"|"+str(current_hour_minute_second)+"|"+str(to_time)+"|days:|"+str(from_day)+"|"+str(current_time.strftime('%A').upper())+"|"+str(to_day))

            # Checks for both ways, from time bigger or lower than to time
            if from_time > to_time: #ie: 22:00:00 to 04:00:00
                if not (to_time >= current_hour_minute_second or current_hour_minute_second >= from_time):
                    continue  # Skip this rule, as current time is outside the range
                # This variable is true only if current hour minute is less than midnight
                # This is to avoid a case where shift is 22 to 04 and friday to sunday (morning) and sunday 23:00 would be considered ok (which is not), while sunday 01:00 is ok
                timeFlag=True  
            elif not from_time <= current_hour_minute_second <= to_time:
                continue  # Skip this rule, as current time is outside the range

            # Check if current day is within the rule's day range

            days = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']

            # Checks for both ways as before for time
            if (days.index(to_day) < days.index(from_day)) and timeFlag:
                if not (days.index(to_day) > days.index(current_time.strftime('%A').upper()) or days.index(current_time.strftime('%A').upper()) >= days.index(from_day)):
                    continue # Skip this rule, as current day is outside the range
            elif days.index(to_day) < days.index(from_day) and not timeFlag:
                if not (days.index(to_day) >= days.index(current_time.strftime('%A').upper()) or days.index(current_time.strftime('%A').upper()) >= days.index(from_day)):
                    continue  # Skip this rule, as current day is outside the range
            elif (not (days.index(from_day) <= days.index(current_time.strftime('%A').upper()) < days.index(to_day))) and timeFlag:
                continue  # Skip this rule, as current day is outside the range
            elif (not (days.index(from_day) <= days.index(current_time.strftime('%A').upper()) <= days.index(to_day))) and not timeFlag:
                continue  # Skip this rule, as current day is outside the range


            return True

        return False

    def xeslog(self, node_id, status, nodeType):
        start_time = datetime.strptime(Process.startDateTime, "%Y-%m-%dT%H:%M:%S")
        current_time = start_time + timedelta(seconds=self.env.now)
        rows.append([self.num, node_id, current_time, status, nodeType,self.name,self.instance_type],)

    def printState(self, node, node_id, inSubProcess):
        if node['subtype'] is not None:
            node['type']=node['type']+"/"+node['subtype']
        if node['type'] == 'subProcess':
            print(f"#{self.num}|{self.name}: {node_id} (subprocess {node['name']} just started), instance_type:{self.instance_type}. time: {self.env.now}.")
        elif inSubProcess == True:
            print(f"#{self.num}|{self.name} (inside subprocess): {node_id} ({node['name']}), type: {node['type']}, instance_type:{self.instance_type}. time: {self.env.now}.")
        else:
            print(f"#{self.num}|{self.name}: {node_id} ({node['name']}), type: {node['type']}, instance_type:{self.instance_type}. time: {self.env.now}.")

    def run(self):
        yield self.env.timeout(self.start_delay) #delay start because of arrival rate.
        start_node_id = next((node_id for node_id, node in self.process_details['node_details'].items() if node['type'] == 'startEvent'), None)
        if start_node_id is None:
            return
        yield from self.run_node(start_node_id)
        #This zone is executed after all process instance is over:
        for element_id, duration_threshold in self.durationThresholds.items():
            if self.durationThresholds[element_id] is not None and self.durationThresholds[element_id] < 0.0:
                abss=abs(self.durationThresholds[element_id])
                print(f"-------------------\n{element_id} has exceded his duration threshold by {abss}\n-------------------")
        for element_id, cost_threshold in self.costThresholds.items():
            if self.costThresholds[element_id] is not None and self.costThresholds[element_id] < 0.0:
                abss=abs(self.costThresholds[element_id])
                print(f"-------------------\n{element_id} has exceded his cost threshold by {abss}\n-------------------")



    def run_node(self, node_id, subprocess_node=None):
        if subprocess_node is None:
            node = self.process_details['node_details'][node_id]
            printFlag=False
        else:
            node = self.process_details['node_details'][subprocess_node]['subprocess_details'][node_id]
            printFlag=True

        #if this process met a terminate end event anywhere, stop execution
        if Process.terminateEndEvent[self.num]==True:
            return
    
        if node['type'] == 'startEvent':
            next_node_id = node['next'][0]
            if len(node['previous'])>0:
                while not all(prev_node in Process.executed_nodes[self.num] for prev_node in node['previous']):
                    yield self.env.timeout(1)
            self.xeslog(node_id,"complete",node['type'])
            self.printState(node,node_id,printFlag)
            Process.executed_nodes[self.num].add(node_id)
            yield from self.run_node(next_node_id, subprocess_node)


        elif node['type'] == 'task':
            #print(Process.terminateEndEvent[self.num])
            #check if external exceptions happened (if in a subprocess), if yes handle it or just return
            if subprocess_node is not None:
                idd,error_node = next(((idd,node) for idd, node in self.process_details['node_details'].items() if node['type'] == 'boundaryEvent' and node['subtype'] == 'messageEventDefinition' and node['attached_to'] == subprocess_node), (None, None))
                if idd is not None: #if there is a boundary event of type msg
                    #print("handling excp1")
                    if any(prev_node in Process.executed_nodes[self.num] for prev_node in error_node['previous']): #if some msg arrived to it
                        #print("handling excp2")
                        self.subprocessExternalException[subprocess_node]=True
                    has_exception_been_handled = idd in Process.executed_nodes[self.num]
                    if self.subprocessExternalException[subprocess_node]==True and not has_exception_been_handled:
                        #print("handling excp3")
                        yield from self.run_node(idd, None)
                        return
                    elif self.subprocessExternalException[subprocess_node]==True and has_exception_been_handled:
                        return
                if Process.subprocessTerminate[self.num][subprocess_node]==True: 
                    return 

            #check if terminate end events happened
            if Process.terminateEndEvent[self.num]==True:
                return

            #wait for previous messages to be delivered
            if len(node['previous'])>0:
                while not all(prev_node in Process.executed_nodes[self.num] for prev_node in node['previous']):
                    if Process.terminateEndEvent[self.num]==True:
                        return
                    yield self.env.timeout(1)
            self.xeslog(node_id,"start",node['type'])
            taskTime=timeCalculator.convert_to_seconds(task_durations[node_id]) # task duration is used here, it is passed before to a converter that transforms the type/mean/arg1/arg2 to a value in seconds, this value the task duration is always different in each instance
            if self.durationThresholds[node_id] is not None:
                self.durationThresholds[node_id] -= taskTime
                #print(self.durationThresholds)

            #resources zone
            taskNeededResources=task_resources[node_id]
            if taskNeededResources: #if the task needs resources
                grouped_resources = {}
                for res in taskNeededResources:
                    if res['groupId'] not in grouped_resources:
                        grouped_resources[res['groupId']] = []
                    grouped_resources[res['groupId']].append((res['resourceName'], int(res['amountNeeded'])))
                    #print(grouped_resources)              
                # Check each group of resources
                while True:
                    resources_allocated = False
                    i=0
                    numberOfGroupsWithNotEnoughResources=0          
                    for group_id, resources in grouped_resources.items():    
                        i+=1      
                        # Check if there are enough resources to fulfill the request of a group
                        requests = []
                        costsPerHour = []
                        for resource, amount in resources:
                            #capacity indica capacità della risorsa, count quante ne ho allocate. Inoltre controlla se la risorsa è in timetable
                            if not self.is_in_timetable(self.resources[resource][2]) or self.resources[resource][0].capacity-self.resources[resource][0].count < amount:
                                if self.resources[resource][0].capacity < amount:
                                    numberOfGroupsWithNotEnoughResources+=1 #if there are not enough resources then this group will never be able to be allocated
                                if not self.is_in_timetable(self.resources[resource][2]) and resourceLog:
                                    print(node_id + "|group n."+str(i)+"| TIMETABLE-BREAK | "+resource+": "+str(self.resources[resource][0].count)+"/"+str(self.resources[resource][0].capacity)+" amount: "+str(amount))
                                elif resourceLog:
                                    print(node_id + "|group n."+str(i)+"| BREAK | "+resource+": "+str(self.resources[resource][0].count)+"/"+str(self.resources[resource][0].capacity)+" amount: "+str(amount))
                                for name, req, costPerHour in requests:
                                    req.resource.release(req)
                                    req.cancel() # cancel the requests that were accumulated till now since this group is ko
                                break  # If not enough resources, break and check the next group
                            else:
                                for _ in range(amount):
                                    req = self.resources[resource][0].request()  # If enough resources, request resources
                                    costPerHour = self.resources[resource][1]
                                    if resourceLog:
                                        print(node_id + "|group n."+str(i)+"|"+resource+": "+str(self.resources[resource][0].count)+"/"+str(self.resources[resource][0].capacity)+" total amount needed: "+str(amount))
                                    requests.append((resource, req, costPerHour))
                        total_resources_needed = sum(amount for _, amount in resources)
                        if len(requests) == total_resources_needed:  # If all resources in the group can be allocated
                            resources_allocated = True
                            for name, req, costPerHour in requests:
                                yield req
                                if resourceLog:
                                    print (node_id + "|Resource locked: " + name + ", Time: " + str(self.env.now) )  # Print + str(req.amount)
                            break  # Break the loop as resources are allocated
                    if numberOfGroupsWithNotEnoughResources==len(grouped_resources): #if the number of groups that can't be allocated is equal to the number of groups, no group can be allocated
                        raise Exception("Amount of resource needed for task '"+node_id+"' is more than the resource capacity")
                    if not resources_allocated:
                        yield self.env.timeout(1)  # If no group can be allocated, wait for a timeout(1)
                    else:
                        break  # Break the while true as resources are allocated
            self.xeslog(node_id,"assign",node['type'])
            yield self.env.timeout(taskTime)
            self.xeslog(node_id,"complete",node['type'])
            Process.executed_nodes[self.num].add(node_id)
            self.printState(node,node_id,printFlag)
            next_node_id = node['next'][0]
            taskCost=task_costs[node_id]
            if taskCost != '':
                totalCost[self.num] += float(taskCost)
                if self.costThresholds[node_id] is not None:
                    self.costThresholds[node_id]-=float(taskCost)
            
            # Release resources
            if taskNeededResources:
                for name, req, costPerHour in requests:
                    timeUsedPerResource[name]+=float(taskTime)
                    req.resource.release(req)
                    if resourceLog:
                        print(node_id + "|Resource released: " + name  + ", Time: " + str(self.env.now))
            yield from self.run_node(next_node_id, subprocess_node)


        elif node['type'] == 'exclusiveGateway':
            # Get the flows from bpmn.json that start from the current XOR
            flows_from_xor = [(flow_id, flow) for flow_id, flow in bpmn['sequence_flows'].items() if flow['sourceRef'] == node_id]
            # Create a dictionary mapping target nodes to their probabilities
            node_probabilities = {}
            forced_flow_target = None
            for flow_id, flow in flows_from_xor:
                # Find the corresponding flow in diagbp.json
                diagbp_flow = next((item for item in diagbp['sequenceFlows'] if item['elementId'] == flow_id), None)
                if diagbp_flow is not None:
                    node_probabilities[flow['targetRef']] = float(diagbp_flow['executionProbability'])
                    # Check if 'types' field exists and if it matches with self.instance_type (to force the current instance into his xor based on the instance type)
                    if 'types' in diagbp_flow:
                        for type_dict in diagbp_flow['types']:
                            if type_dict['type'] == self.instance_type:
                                forced_flow_target = flow['targetRef']
                                break
                if forced_flow_target is not None:
                    break
            # Check if node_probabilities is empty, if yes then the xor has only one next elem.
            if not node_probabilities:
                next_node_id = node['next'][0]
            elif forced_flow_target is not None:
                next_node_id = forced_flow_target
            else:
                next_node_id = np.random.choice(list(node_probabilities.keys()), p=list(node_probabilities.values()))
            self.xeslog(node_id,"complete",node['type'])
            self.printState(node,node_id,printFlag)
            yield from self.run_node(next_node_id, subprocess_node)


        elif node['type'] == 'parallelGateway':
            # AND logic: run all paths concurrently and wait for all to finish, process is created for each path to ensure parallelism
            events = []
            for next_node_id in node['next']:
                process = self.env.process(self.run_node(next_node_id, subprocess_node))
                events.append(process)
            self.xeslog(node_id,"complete",node['type'])
            self.printState(node,node_id,printFlag)
            yield self.env.all_of(events)
            # When all_of is done, proceed with the node after the close
            # print for parallel close
            if not printFlag:
                print(f"#{self.num}|{self.name}: Parallel gateway closed. instance_type:{self.instance_type}. time: {self.env.now}.")
            else:
                print(f"#{self.num}|{self.name}| (inside subprocess): Parallel gateway closed. instance_type:{self.instance_type}. time: {self.env.now}.")
            

            if self.stack:  # checks if the list is not empty
                parallel_close_id,next_node_after_parallel = self.stack.pop()
                self.xeslog(parallel_close_id,"complete",node['type'])
                yield from self.run_node(next_node_after_parallel, subprocess_node)

        elif node['type'] == 'parallelGateway_close':
            if (node_id, node['next'][0]) not in self.stack:
                self.stack.append((node_id, node['next'][0]))
            print(self.stack)
            return
            
        elif node['type'] == 'subProcess':
            self.subprocessExternalException[node_id]=False
            Process.subprocessTerminate[self.num][node_id]=False
            self.subprocessInternalError[node_id]=False
            if len(node['previous'])>0:
                while not all(prev_node in Process.executed_nodes[self.num] for prev_node in node['previous']):
                    yield self.env.timeout(1)
            self.xeslog(node_id,"start",node['type'])
            start_node_id = next(sub_node_id for sub_node_id, sub_node in node['subprocess_details'].items() if sub_node['type'] == 'startEvent')
            self.printState(node,node_id,printFlag)
            yield from self.run_node(start_node_id, node_id)
            Process.executed_nodes[self.num].add(node_id)
            next_node_id = node['next'][0]
            # After the subprocess is executed, continue with the node next to the subprocess if no error end event
            self.xeslog(node_id,"complete",node['type'])
            if self.subprocessInternalError[node_id]==False and self.subprocessExternalException[node_id]==False and Process.terminateEndEvent[self.num]==False:
                yield from self.run_node(next_node_id, None)
            elif self.subprocessInternalError[node_id]==True: #if internal error happened, deal with it
                error_node = next((idd for idd, node in self.process_details['node_details'].items() if node['type'] == 'boundaryEvent' and node['attached_to'] == node_id), None)
                yield from self.run_node(error_node, None)
            #implicit else: if external exception do nothing since it is handled inside elif node[type]==task

        elif node['type'] == 'intermediateThrowEvent':
            next_node_id = node['next'][0]
            Process.executed_nodes[self.num].add(node_id)
            self.xeslog(node_id,"complete",node['type'])
            self.printState(node,node_id,printFlag)
            yield from self.run_node(next_node_id, subprocess_node)
            return

        elif node['type'] == 'intermediateCatchEvent':
            fullType = node['type'] + '/' + node['subtype'] if node['subtype'] is not None else node['type']
            if node['subtype'] == 'messageEventDefinition': #if it is an intermediate msg catch wait for the msg
                next_node_id = node['next'][0]
                if len(node['previous'])>0: #wait for msg
                    while not all(prev_node in Process.executed_nodes[self.num] for prev_node in node['previous']):
                        yield self.env.timeout(1)
                Process.executed_nodes[self.num].add(node_id)
                self.xeslog(node_id,"complete",fullType)
                self.printState(node,node_id,printFlag)
                yield from self.run_node(next_node_id, subprocess_node)
                return
            else: #otherwise treats it as a timer event, whatever it is
                next_node_id = node['next'][0]
                Process.executed_nodes[self.num].add(node_id)
                waitTime = catchEvents[node_id]
                waitTimeSeconds=timeCalculator.convert_to_seconds(waitTime)
                self.xeslog(node_id,"start",fullType)
                yield self.env.timeout(waitTimeSeconds)
                self.xeslog(node_id,"complete",fullType)
                self.printState(node,node_id,printFlag)
                yield from self.run_node(next_node_id, subprocess_node)
                return
        
        elif node['type'] == 'eventBasedGateway':
            smallestTimer=None
            ready=False
            waitedTimeInEventBasedGateway=0
            Process.executed_nodes[self.num].add(node_id)
            self.xeslog(node_id,"complete",node['type'])
            self.printState(node,node_id,printFlag)    

            for next_node_id in node['next']:
                if subprocess_node is None:
                    nextNode = self.process_details['node_details'][next_node_id]
                    printFlag=False
                else:
                    nextNode = self.process_details['node_details'][subprocess_node]['subprocess_details'][next_node_id]
                    printFlag=True
                if not nextNode['subtype'] == 'messageEventDefinition': #after event based gateway there is for sure intermediate catch events, if not message i save smallest timer
                    timer=timeCalculator.convert_to_seconds(catchEvents[next_node_id])
                    if smallestTimer is None or timer < smallestTimer:
                        smallestTimer = timer
                        nextNodeToVisit=nextNode['next'][0]
            while (not ready) and waitedTimeInEventBasedGateway < smallestTimer: #while no msg has been received and the smallest timer is not over yet
                for next_node_id in node['next']:
                    if subprocess_node is None:
                        nextNode = self.process_details['node_details'][next_node_id]
                        printFlag=False
                    else:
                        nextNode = self.process_details['node_details'][subprocess_node]['subprocess_details'][next_node_id]
                        printFlag=True
                    if nextNode['subtype'] == 'messageEventDefinition' and ready==False:
                        ready=any(prev_node in Process.executed_nodes[self.num] for prev_node in nextNode['previous'])
                        if ready==True:
                            nextNodeToVisit=nextNode['next'][0]
                            break
                yield self.env.timeout(1)
                waitedTimeInEventBasedGateway+=1

            self.printState(nextNode,next_node_id,printFlag) # print the state of the intermediate catch event (timer or msg, whatever)
            yield from self.run_node(nextNodeToVisit, subprocess_node) # now it visits the node 2 times forward because the catches have already been handled
            return

        elif node['type'] == 'boundaryEvent': 
            self.printState(node,node_id,printFlag)
            Process.executed_nodes[self.num].add(node_id)
            next_node_id = node['next'][0]
            yield from self.run_node(next_node_id, subprocess_node)
            return

        elif node['type'] == 'endEvent': 
            fullType = node['type'] + '/' + node['subtype'] if node['subtype'] is not None else node['type']
            Process.executed_nodes[self.num].add(node_id)
            self.xeslog(node_id,"complete",fullType)           
            self.printState(node,node_id,printFlag)
            # Terminate end event
            if node['subtype'] == 'terminateEventDefinition' and subprocess_node is None:
                Process.terminateEndEvent[self.num]=True
            elif node['subtype'] == 'terminateEventDefinition':
                Process.subprocessTerminate[self.num][subprocess_node]=True #it stops the subprocess
            # Error end event (lightning symbol)
            elif node['subtype'] == 'errorEventDefinition' and subprocess_node is not None:
                self.subprocessInternalError[subprocess_node]=True
                return
            # standard end event
            else:
                return

env = simpy.Environment()
def simulate_bpmn(bpmn_dict):
    instance_index = 0
    instance_count = 0

    global_resources = {res['name']: (simpy.Resource(env, capacity=int(res['totalAmount'])), res['costPerHour'], res['timetableName']) for res in resources} if resources else {}
    for i in range(num_instances):
        instance_type = instance_types[instance_index]['type']

        for participant_id, participant in bpmn_dict['collaboration']['participants'].items():
            process_details = bpmn_dict['process_elements'][participant['processRef']]
            # for each instance a class Process is created:
            Process(env, participant['name'], process_details,i+1, global_resources, delays[i], instance_type)

        instance_count += 1
        if instance_count >= int(instance_types[instance_index]['count']):
            instance_index += 1
            instance_count = 0
    env.run()


simulate_bpmn(bpmn)

end_parameters={}
event_data = []
taskCosts={}
resourcesPercentageUsage={}
resourceCosts={}

for key, value in totalCost.items():
    if logCosts:
        print("Cost of all the tasks in instance n. "+str(key)+": "+str(value))
    taskCosts[key]=value
end_parameters["tasksCosts"]=taskCosts

for name, time in timeUsedPerResource.items():
    if logCosts:
        print(f"Percentage of usage of resource '{name}': {time*100/env.now:.1f}%")
    resourcesPercentageUsage[name]=time
end_parameters["resourcesPercentageUsage"]=resourcesPercentageUsage

for resource in resources:
    total_amount = float(resource["totalAmount"])
    cost_per_hour = float(resource["costPerHour"])
    time_in_hours = env.now / 3600  # Convert time to hours
    resource_cost = total_amount * cost_per_hour * time_in_hours
    name=resource['name']
    if logCosts:
        print(f"Cost for resource '{name}': {resource_cost:.1f}")
    resourceCosts[name]=f"{resource_cost:.1f}"
end_parameters["resourceCosts"]=resourceCosts


with open(csv_file, 'w') as f:
    writer = csv.writer(f)
    writer.writerow(fields)
    writer.writerows(rows)

dataframe = pd.read_csv(csv_file, sep=',')
dataframe = dataframe.rename(columns={'status': 'lifecycle:transition'})
dataframe = pm4py.format_dataframe(dataframe, case_id='traceId', activity_key='activity', timestamp_key='timestamp')
event_log = pm4py.convert_to_event_log(dataframe)    
pm4py.write_xes(event_log, '../log.xes')
