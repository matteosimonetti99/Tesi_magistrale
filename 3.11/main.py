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
import threading
import os


#to remove, credo
import random
import time

sys.setrecursionlimit(100000)



#Put resourcesOutputConsole and timetableOutputConsole to true if you want the log in console of resources locked/unlocked and timetable management
debug1=False
debug=False
resourcesOutputConsole=False
timetableOutputConsole=False
costsOutputConsole=True
logSetupTime=True


extraLog={}

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
logs_dir = "../logs"
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)
csv_file = "../logs/log.csv"
fields = ['traceId', 'activity', 'timestamp', 'status', 'nodeType', 'poolName','instanceType']
rows=[]
logging_opt=diagbp['logging_opt']
logging_opt = (logging_opt == 1)

#other glob var
num_instances = sum(int(instance['count']) for instance in diagbp['processInstances'])
print("NUM_INSTANCES: "+ str(num_instances))
instance_types = diagbp['processInstances']
xor_probabilities = {flow['elementId']: float(flow['executionProbability']) for flow in diagbp['sequenceFlows']}
resources = diagbp['resources']
#global_resource global var is in simulate_bpmn function at the end of the code, it is passed to process as globalResources
timetables = diagbp['timetables']
catchEvents = diagbp['catchEvents']

# Generate the delays, calling them delay is kinda wrong because delays is in fact an array of starting times, so like 0, 5, 10...
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
tasks_worklists={element['elementId']: element['worklistId'] for element in diagbp['elements']}

totalCost={} #task_costs are summed here
timeUsedPerResource={} #resources time being used are summed here
worklist_resources={}
class Process:
    executed_nodes = {}  # make executed_nodes a dictionary of sets, once a node is executed in this instance, it is saved here
    startDateTime = diagbp['startDateTime']
    terminateEndEvent={} # dictionary of true or false, to tell if that process has been terminated or not
    subprocessTerminate={} #this is used for subprocesses for terminate end events
    def __init__(self, env, name, process_details, num, start_delay=0, instance_type="default"):
        self.env = env
        self.name = name
        self.process_details = process_details
        self.stack=[] #used to save parallel gateways closing pair
        self.stackInclusive=[] #used to save inclusive gateways closing pair
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
        worklist_resources[self.num]={}
        Process.terminateEndEvent[self.num] = False
        Process.subprocessTerminate[self.num] = {}
        totalCost[self.num]=0.0
        #resources is a dict with name as key and a tuple made of simpy resource, cost and timetable.
        Process.executed_nodes[self.num] = set() 
        for resource_name, resource_info in global_resources.items():
            timeUsedPerResource[resource_name]=0.0
        
    def update_resources(self,resource_obj, mode, resource_name, node_id): #this function handles setup time for resources
        #resource_tuple is: simpyRes, cost, timetableName, lastInstanceType, setupTime, maxUsage, actualUsage, lock
        #mode can either be, increment, instanceTypeChange. First mode means that same instanceType has arrived, counter of usages needs to incremented; second mode is
        #for when the instance that comes has a different type than what the resource was previously used for, so it needs some time to prepare.
        usury=False
        instanceCambio=False
        #find the tuple where the resource obj is the one we want to update, tuple structure is in the first comment of function
        for tuple_ in global_resources[resource_name]:
            if tuple_[0] is resource_obj:
                resource_tuple=tuple_
        #if this resource doesn't involve setup times
        if not resource_tuple[4]["type"]:
            return

        if mode=="increment":
            #if usage limit reached put usage to 0 and flag usury, otherwise just increment by 1
            if int(resource_tuple[6].level) + 1 >= int(resource_tuple[5]):
                resource_tuple[6].get(int(resource_tuple[5])-1)
                usury=True
            else:
                resource_tuple[6].put(1)

        elif mode=="instanceTypeChange":
            instanceCambio=True
            #usage to 0
            while resource_tuple[6].level > 0:
                yield resource_tuple[6].get(1)
        
        logg=""
        if usury==True:
            logg="worn"
        elif instanceCambio==True:
            logg="instanceTypeChange"

        setup_time = timeCalculator.convert_to_seconds(resource_tuple[4])
        # Update currentUsages
        for i, res_tuple in enumerate(global_resources[resource_name]):
            if res_tuple[0] is resource_tuple[0]:
                self.xeslog(node_id,"startSetupTime",logg) if usury or instanceCambio else None
                print(f"Cambio usury {resource_tuple[0]} {self.env.now}") if logSetupTime and usury else None
                print(f"Cambio instance_type {resource_tuple[0]} {self.env.now}") if logSetupTime and instanceCambio else None
                if instanceCambio or usury:
                    yield self.env.timeout(setup_time)
                    print(f"Fine cambio {resource_tuple[0]} {self.env.now}")
                self.xeslog(node_id,"endSetupTime",logg) if usury or instanceCambio else None
                #update resource by locking resource first
                with res_tuple[7]:
                    global_resources[resource_name][i] = (
                        res_tuple[0],  # simpy resource
                        res_tuple[1],  # cost
                        res_tuple[2],  # timetable
                        self.instance_type,  # lastInstanceType
                        res_tuple[4],  # setupTime
                        int(res_tuple[5]),  # maxUsages
                        res_tuple[6],
                        res_tuple[7]  
                    )                                                    
                break


    
    def is_in_timetable(self, timetable_name): #this func is used when gathering resources for a task, to check if a res is in shift
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
            if timetableOutputConsole:
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
        if nodeType=="parallelGateway":
            nodeType="parallelGatewayOpen"
        start_time = datetime.strptime(Process.startDateTime, "%Y-%m-%dT%H:%M:%S")
        current_time = start_time + timedelta(seconds=self.env.now)
        if logging_opt or status=="complete":
            rows.append([self.num, node_id, current_time, status, nodeType,self.name,self.instance_type],)

    def printState(self, node, node_id, inSubProcess):
        node_copy = node.copy() #to avoid changing data in node due to the first if
        if node_copy['subtype'] is not None:
            node_copy['type']=node_copy['type']+"/"+node_copy['subtype']
        if node_copy['type'] == 'subProcess':
            print(f"#{self.num}|{self.name}: {node_id} (subprocess {node_copy['name']} just started), instance_type:{self.instance_type}. time: {self.env.now}.")
        elif inSubProcess == True:
            print(f"#{self.num}|{self.name} (inside subprocess): {node_id} ({node_copy['name']}), type: {node_copy['type']}, instance_type:{self.instance_type}. time: {self.env.now}.")
        else:
            print(f"#{self.num}|{self.name}: {node_id} ({node_copy['name']}), type: {node_copy['type']}, instance_type:{self.instance_type}. time: {self.env.now}.")

    def run(self):
        yield self.env.timeout(self.start_delay) #delay start because of arrival rate.
        start_node_id = next((node_id for node_id, node in self.process_details['node_details'].items() if node['type'] == 'startEvent'), None) #find first start event
        if start_node_id is None:
            return
        yield from self.run_node(start_node_id)

        #This zone is executed after instance is over, since run_node recursively visits all nodes:
        for element_id, duration_threshold in self.durationThresholds.items():
            if self.durationThresholds[element_id] is not None and self.durationThresholds[element_id] < 0.0:
                abss=abs(self.durationThresholds[element_id])
                print(f"-------------------\n{element_id} has exceded his duration threshold by {abss}\n-------------------")
                extraLog[f"{element_id} has exceded his DURATION threshold in instance {self.num} by:"]= abss
        for element_id, cost_threshold in self.costThresholds.items():
            if self.costThresholds[element_id] is not None and self.costThresholds[element_id] < 0.0:
                abss=abs(self.costThresholds[element_id])
                print(f"-------------------\n{element_id} has exceded his cost threshold by {abss}\n-------------------")
                extraLog[f"{element_id} has exceded his COST threshold in instance {self.num} by:"]= abss


    def run_node(self, node_id, subprocess_node=None):
        #if we are in a subprocess then the data is saved in a different section of bpmn.json (that has been saved to process_details)
        if subprocess_node is None:
            node = self.process_details['node_details'][node_id]
            printFlag=False
        else:
            node = self.process_details['node_details'][subprocess_node]['subprocess_details'][node_id]
            printFlag=True

        #if this instance met a terminate end event anywhere, stop execution
        if Process.terminateEndEvent[self.num]==True:
            return
    
        if node['type'] == 'startEvent':
            if node['subtype']=="timerEventDefinition":
                waitTime = catchEvents[node_id]
                waitTimeSeconds=timeCalculator.convert_to_seconds(waitTime)
                self.xeslog(node_id,"start",fullType)
                yield self.env.timeout(waitTimeSeconds)
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
                    if any(prev_node in Process.executed_nodes[self.num] for prev_node in error_node['previous']): #if some msg arrived to it
                        self.subprocessExternalException[subprocess_node]=True
                    has_exception_been_handled = idd in Process.executed_nodes[self.num]
                    if self.subprocessExternalException[subprocess_node]==True and not has_exception_been_handled:
                        yield from self.run_node(idd, None)
                        return
                    elif self.subprocessExternalException[subprocess_node]==True and has_exception_been_handled:
                        return
                if Process.subprocessTerminate[self.num][subprocess_node]==True: 
                    return 

            #wait for previous messages to be delivered (message pointing to this task)
            if len(node['previous'])>0:
                while not all(prev_node in Process.executed_nodes[self.num] for prev_node in node['previous']):
                    yield self.env.timeout(1)
            self.xeslog(node_id,"start",node['type'])
            taskTime=timeCalculator.convert_to_seconds(task_durations[node_id]) # task duration is used here, it is passed before to a converter that transforms the type/mean/arg1/arg2 to a value in seconds, this value the task duration is always different in each instance
            if self.durationThresholds[node_id] is not None:
                self.durationThresholds[node_id] -= taskTime
                #print(self.durationThresholds)


            #RESOURCES zone
            taskNeededResources = task_resources[node_id]
            worklist_id = tasks_worklists[node_id]
            if taskNeededResources: #if the task needs some resources
                grouped_resources = {}
                for res in taskNeededResources:
                    if res['groupId'] not in grouped_resources:
                        grouped_resources[res['groupId']] = []
                    grouped_resources[res['groupId']].append((res['resourceName'], int(res['amountNeeded'])))
                waited={}                                    
                while True: #iterate till some resources can be allocated
                    resources_allocated = False
                    i = 0
                    for group_id, resources in grouped_resources.items(): # Check each group of resources
                        timetablebreakFlag=False
                        i += 1
                        # Check if there are enough resources and within timetable for this group
                        requests = []
                        for resource_name, amount_needed in resources:
                            if worklist_id and worklist_id in worklist_resources[self.num]: #if this task has a worklist_id, then the set of resources is a subset of the full resources and it is taken from worklist_resources
                                available_resources = []
                                resources_in_timetable = []
                                if resource_name in worklist_resources[self.num][worklist_id]:  # Check if the resource exists for this worklist_id
                                    for resource_tuple in global_resources[resource_name]:
                                        if self.is_in_timetable(resource_tuple[2]) and resource_tuple[0].count < resource_tuple[0].capacity:
                                            available_resources.append(resource_tuple)
                                        if self.is_in_timetable(resource_tuple[2]):
                                            resources_in_timetable.append(resource_tuple)
                                            
                                timetablebreakFlag=True #this avoids a false print of timetable error later
                                
                            else:
                                available_resources = [res for res in global_resources[resource_name] if self.is_in_timetable(res[2]) and res[0].count < res[0].capacity]
                                resources_in_timetable = [res for res in global_resources[resource_name] if self.is_in_timetable(res[2])]
                            print(f"PREEEEE avail: {len(available_resources)} needed:{amount_needed} ") if debug else None
                            if len(available_resources) < amount_needed:
                                if resourcesOutputConsole:
                                    if len(resources_in_timetable) == 0 and timetablebreakFlag==False:
                                        print(node_id + f"|group n.{i}| TIMETABLE-BREAK | {resource_name}: No resources available within timetable #{self.num}")
                                    else:
                                        print(node_id + f"|group n.{i}| BREAK | {resource_name}: {len(available_resources)}/{len(global_resources[resource_name])} resources available, {amount_needed} needed #{self.num}")
                                for name, req, costPerHour, resourceSimpy,_ in requests:
                                    req.resource.release(req)
                                    req.cancel() # cancel the requests that were accumulated till now since this group is ko
                                break  # Move to the next group if not enough resources
                            else:
                                #print(node_id + f"|group n.{i}| OK | {resource_name}: {len(available_resources)}/{len(global_resources[resource_name])} resources available, {amount_needed} needed")
                                appended=0
                                to_request = []  # New data structure to store resources to request later, needed due to possible setup_times

                                #resource_tuple is: simpyRes, cost, timetableName, lastInstanceType, setupTime, maxUsage, actualUsage, lock
                                for resource_tuple in available_resources:  
                                    #debug zone
                                    print(f"to_req: {to_request}") if debug else None
                                    print(f"waited:{waited}") if debug else None                                 
                                    if debug1 and not resource_tuple[4]=="" and resource_tuple[4]["type"]:
                                        print(f"({resource_tuple[0]}, {resource_tuple[1]}, {resource_tuple[2]}, {resource_tuple[3]}, {resource_tuple[4]}, {resource_tuple[5]}, {resource_tuple[6].level}, {resource_tuple[7]})")
                                    elif debug1:
                                        print(f"({resource_tuple[0]}, {resource_tuple[1]}, {resource_tuple[2]}, {resource_tuple[3]}")

                                    if appended == amount_needed:
                                        break
                                    # Checks if there is no setupTime or there is setupTime but no lastInstance, or there is lastInstance but it is our current instanceType
                                    if (not resource_tuple[4]['type'] or not resource_tuple[3] or resource_tuple[3]==self.instance_type):
                                        modified_tuple = resource_tuple + ("increment",)
                                        to_request.append(modified_tuple)                                         
                                        appended += 1

                                    #case where different lastInstanceType so i wait 1 second to give opportunity to other instances of same type to use resource, if there are any.
                                    elif resource_tuple[3] and (resource_tuple[0] not in waited or waited[resource_tuple[0]]==False):
                                        waited[resource_tuple[0]]=True
                                        yield self.env.timeout(1)

                                    # Check if resource is with different lastInstanceType, so needs setupTime (after having waited)
                                    elif resource_tuple[3] and waited[resource_tuple[0]]==True: 
                                        modified_tuple = resource_tuple + ("instanceTypeChange",)
                                        to_request.append(modified_tuple)  
                                        appended+=1
                                        
                                    else:
                                        waited[resource_tuple[0]]=False

                                if appended == amount_needed:
                                    for resource_tuple in to_request:
                                        req = resource_tuple[0].request()
                                        requests.append((resource_name, req, resource_tuple[1], resource_tuple[0],resource_tuple[8])) #[8] is the "mode" for update_resources funct, it was appended to the tuple in previous elif

                        # If all resources in the group can be allocated
                        print(f"requests: {len(requests)}") if debug else None
                        print(f"amount sum: {sum(amount for _, amount in resources)}") if debug else None

                        if len(requests) == sum(amount for _, amount in resources):
                            resources_allocated = True
                            waited={}                            
                            # Store acquired resources in instance-specific worklist_resources if worklist_id is not empty
                            if worklist_id:
                                if worklist_id not in worklist_resources[self.num]:
                                    worklist_resources[self.num][worklist_id] = {}  
                                for resource_name, req, cost_per_hour, resourceSimpy,_ in requests:
                                    if resource_name not in worklist_resources[self.num][worklist_id]:
                                        worklist_resources[self.num][worklist_id][resource_name] = []
                                    # Find the matching resource tuple in global_resources
                                    res_tuple = next(res for res in global_resources[resource_name] if res[0] is req.resource)
                                    _, cost_per_hour, timetable_name, last_instance, setup_time, max_usages, current_usages,lock = res_tuple
                                    # Append to worklist_resources with all elements (IMPORTANT: actually the tuple is USELESS (except for the resource), only the resource will be used in the rest of the code, the other info will be taken from global_resources using the res as id)
                                    worklist_resources[self.num][worklist_id][resource_name].append(
                                        (req.resource, cost_per_hour, timetable_name, last_instance, setup_time, max_usages, current_usages,lock)
                                    )

                            for resource_name, req, cost_per_hour, resourceSimpy,mode in requests:  # Extract elements from the tuple
                                #update global_resources 2 cases: 1) self.instance.type is different and then throw setupTime 2) same instanceType, check usage
                                #mode can either be, increment, instanceTypeChange
                                yield from self.update_resources(req.resource, mode,resource_name, node_id)
                                yield req

                                if resourcesOutputConsole:
                                    print(f"{node_id}|Resource locked: {resource_name} ({req.resource}), Time: {self.env.now} #{self.num}")                          
                            break  # Break the loop as resources are allocated
                        else:
                            for _,req,_,_,_ in requests:
                                if req.triggered:
                                    req.cancel()
                                    req.resource.release(req)

                    if not resources_allocated:
                        yield self.env.timeout(1)  # If no group can be allocated, wait for a timeout
                    else:
                        break  # Break the while loop as resources are allocated
            #END resources


            self.xeslog(node_id,"assign",node['type'])
            yield self.env.timeout(taskTime)
            
            #EXCEPTIONS check, the check was already done before but it might have happened some stuff during the timeout:
            #check if terminate end events happened
            if Process.terminateEndEvent[self.num]==True:
                return
            #check if external exceptions happened (if in a subprocess), if yes handle it or just return
            if subprocess_node is not None:
                idd,error_node = next(((idd,node) for idd, node in self.process_details['node_details'].items() if node['type'] == 'boundaryEvent' and node['subtype'] == 'messageEventDefinition' and node['attached_to'] == subprocess_node), (None, None))
                if idd is not None: #if there is a boundary event of type msg
                    if any(prev_node in Process.executed_nodes[self.num] for prev_node in error_node['previous']): #if some msg arrived to it
                        self.subprocessExternalException[subprocess_node]=True
                    has_exception_been_handled = idd in Process.executed_nodes[self.num]
                    if self.subprocessExternalException[subprocess_node]==True and not has_exception_been_handled:
                        yield from self.run_node(idd, None)
                        return
                    elif self.subprocessExternalException[subprocess_node]==True and has_exception_been_handled:
                        return
                if Process.subprocessTerminate[self.num][subprocess_node]==True: 
                    return 

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
                for name, req, costPerHour,_, _ in requests:
                    timeUsedPerResource[name]+=float(taskTime)
                    if req.triggered:
                        req.cancel()
                        req.resource.release(req)
                    if resourcesOutputConsole:
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
            # Check if node_probabilities is empty, if yes then the xor has only one next elem. else if there is a forced target use it, else pick it at random.
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
            # AND logic: run all paths concurrently and wait for all to finish
            events = []
            for next_node_id in node['next']:
                process = self.env.process(self.run_node(next_node_id, subprocess_node)) # a process is created for each path to ensure parallelism
                events.append(process)
            self.xeslog(node_id,"complete",node['type'])
            self.printState(node,node_id,printFlag)
            yield self.env.all_of(events)
            # When all_of is done, proceed with the node after the close
            if self.stack:  # checks if the list is not empty
                parallel_close_id,next_node_after_parallel = self.stack.pop()
                self.xeslog(parallel_close_id,"complete",node['type'])
                yield from self.run_node(next_node_after_parallel, subprocess_node)
                # print for parallel close                      
                if not printFlag:
                    print(f"#{self.num}|{self.name}: {parallel_close_id}, Parallel gateway closed. instance_type:{self.instance_type}. time: {self.env.now}.")
                else:
                    print(f"#{self.num}|{self.name}| (inside subprocess): {parallel_close_id}, Parallel gateway closed. instance_type:{self.instance_type}. time: {self.env.now}.")

        elif node['type'] == 'parallelGateway_close':
            if (node_id, node['next'][0]) not in self.stack:
                self.stack.append((node_id, node['next'][0]))
            #print(self.stack)
            return

        elif node['type'] == 'inclusiveGateway':
            flows_from_inclusive = [(flow_id, flow) for flow_id, flow in bpmn['sequence_flows'].items() if flow['sourceRef'] == node_id]
            paths_to_take = []
            for flow_id, flow in flows_from_inclusive:
                type_matched = False
                diagbp_flow = next((item for item in diagbp['sequenceFlows'] if item['elementId'] == flow_id), None)
                if diagbp_flow is not None:
                    if 'types' in diagbp_flow:
                        for type_dict in diagbp_flow['types']:
                            if type_dict['type'] == self.instance_type:
                                paths_to_take.append(flow['targetRef'])
                                type_matched = True  # Mark that a type matched
                                break 
                    # If the type didn't match, use probability 
                    if not type_matched: 
                        probability = float(diagbp_flow['executionProbability'])
                        if np.random.rand() <= probability: 
                            paths_to_take.append(flow['targetRef'])
            events = []
            for next_node_id in paths_to_take:
                process = self.env.process(self.run_node(next_node_id, subprocess_node))
                events.append(process)           
            self.xeslog(node_id,"complete",node['type'])
            self.printState(node,node_id,printFlag)
            yield self.env.all_of(events)

            if self.stackInclusive: 
                inclusive_close_id,next_node_after_inclusive = self.stackInclusive.pop()
                self.xeslog(inclusive_close_id,"complete",node['type'])
                yield from self.run_node(next_node_after_inclusive, subprocess_node)

            if not printFlag:
                print(f"#{self.num}|{self.name}: {inclusive_close_id}, Inclusive gateway closed. instance_type:{self.instance_type}. time: {self.env.now}.")
            else:
                print(f"#{self.num}|{self.name}| (inside subprocess): {inclusive_close_id}, Inclusive gateway closed. instance_type:{self.instance_type}. time: {self.env.now}.")
            
            

        elif node['type'] == 'inclusiveGateway_close':
            if (node_id, node['next'][0]) not in self.stackInclusive:
                self.stackInclusive.append((node_id, node['next'][0]))
            return
            
        elif node['type'] == 'subProcess':
            #set to false all exceptions at first
            self.subprocessExternalException[node_id]=False
            Process.subprocessTerminate[self.num][node_id]=False
            self.subprocessInternalError[node_id]=False
            
            #wait for msg to arrive, if any
            if len(node['previous'])>0:
                while not all(prev_node in Process.executed_nodes[self.num] for prev_node in node['previous']):
                    yield self.env.timeout(1)

            self.xeslog(node_id,"start",node['type'])
            start_node_id = next(sub_node_id for sub_node_id, sub_node in node['subprocess_details'].items() if sub_node['type'] == 'startEvent')
            self.printState(node,node_id,printFlag)
            yield from self.run_node(start_node_id, node_id)

            Process.executed_nodes[self.num].add(node_id)
            next_node_id = node['next'][0]
            self.xeslog(node_id,"complete",node['type'])

            # After the subprocess is executed, continue with the node next to the subprocess if no error end event
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
            else: #otherwise treats it as a timer event, whatever subtype it is
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
            smallestTimer=None #variable where the timer that has lower time to wait (attached to the eventBasedGateway) gets saved, if any
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
                        nextNodeToVisit=nextNode['next'][0] #sets this as next node to visit, can only be changed by a msg received later
            while (not ready) and (smallestTimer is None or waitedTimeInEventBasedGateway < smallestTimer): #while no msg has been received and the smallest timer is not over yet
                for next_node_id in node['next']:
                    if subprocess_node is None:
                        nextNode = self.process_details['node_details'][next_node_id]
                        printFlag=False
                    else:
                        nextNode = self.process_details['node_details'][subprocess_node]['subprocess_details'][next_node_id]
                        printFlag=True
                    if nextNode['subtype'] == 'messageEventDefinition' and ready==False:
                        ready=any(prev_node in Process.executed_nodes[self.num] for prev_node in nextNode['previous']) #this updates the ready variable to leave the while loop above
                        if ready==True:
                            nextNodeToVisit=nextNode['next'][0]
                            break
                yield self.env.timeout(1)
                waitedTimeInEventBasedGateway+=1

            self.printState(nextNode,next_node_id,printFlag) # print the state of the intermediate catch event (timer or msg, whatever)
            self.xeslog(next_node_id,"complete",node['type'])        
            yield from self.run_node(nextNodeToVisit, subprocess_node) # now it visits the node 2 times forward (2 times after the eventBasedGateway) because the catches have already been handled
            return

        elif node['type'] == 'boundaryEvent': 
            self.printState(node,node_id,printFlag)
            self.xeslog(node_id,"complete",node['type'])
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


def timeout_proc(simpy_resource,env,time):
    req = simpy_resource.request()
    yield req
    yield env.timeout(time)
    req.resource.release(req)
    print(f"Initial setup completed for resource {simpy_resource} at time {env.now}")
    # You can add more actions here if needed, such as updating resource state

#resource_tuple is: simpyRes, cost, timetableName, lastInstanceType, setupTime, maxUsage, actualUsage, lock. Starts with actualUsage=MaxUsage so that it setups on first usage.
global_resources = {}
for res in resources:
    resource_list = []
    for _ in range(int(res['totalAmount'])):
        simpy_resource = simpy.Resource(env, capacity=1)
        if res["maxUsage"]=="":
            lastElement=""
        else:
            lastElement=simpy.Container(env, init=0, capacity=int(res['maxUsage']))
        resource_tuple = (
            simpy_resource, 
            res['costPerHour'], 
            res['timetableName'], 
            "", 
            res['setupTime'], 
            res['maxUsage'], 
            lastElement,
            threading.Lock()
        )
        resource_list.append(resource_tuple)

        # Create and start a timeout event for each individual resource
        if res['setupTime']['type']:
            time=timeCalculator.convert_to_seconds(res['setupTime'])
            env.process(timeout_proc(simpy_resource,env,time))

    global_resources[res['name']] = resource_list

if not resources:
    global_resources = {}


def simulate_bpmn(bpmn_dict):
    instance_index = 0
    instance_count = 0

    for i in range(num_instances):
        instance_type = instance_types[instance_index]['type']

        for participant_id, participant in bpmn_dict['collaboration']['participants'].items():
            process_details = bpmn_dict['process_elements'][participant['processRef']]
            # for each instance a class Process is created:
            Process(env, participant['name'], process_details,i+1, delays[i], instance_type)

        instance_count += 1
        if instance_count >= int(instance_types[instance_index]['count']):
            instance_index += 1
            instance_count = 0
    env.run()






simulate_bpmn(bpmn)

event_data = []
taskCosts={}
resourcesPercentageUsage={}
resourceCosts={}

for key, value in totalCost.items():
    if costsOutputConsole:
        print("Cost of all the tasks in instance n. "+str(key)+": "+str(value))
    taskCosts[key]=value

for name, time in timeUsedPerResource.items():
    total_amount = len(global_resources[name])  # Get the total number of individual resources for this type
    if costsOutputConsole:
        print(f"Percentage of usage of resource '{name}': {((time*100)/env.now)/total_amount:.1f}%")
    resourcesPercentageUsage[name] = f"{((time*100)/env.now)/total_amount:.1f}"


for resource in resources:
    total_amount = float(resource["totalAmount"])
    cost_per_hour = float(resource["costPerHour"])
    time_in_hours = env.now / 3600  # Convert time to hours
    resource_cost = total_amount * cost_per_hour * time_in_hours
    name=resource['name']
    if costsOutputConsole:
        print(f"Cost for resource '{name}': {resource_cost:.1f}")
    resourceCosts[name]=f"{resource_cost:.1f}"


with open(csv_file, 'w') as f:
    writer = csv.writer(f)
    writer.writerow(fields)
    writer.writerows(rows)

dataframe = pd.read_csv(csv_file, sep=',')
dataframe = dataframe.rename(columns={'status': 'lifecycle:transition'})
dataframe = pm4py.format_dataframe(dataframe, case_id='traceId', activity_key='activity', timestamp_key='timestamp')
event_log = pm4py.convert_to_event_log(dataframe)

csv_file_extra = "../logs/logExtra.csv"
combined_dict = {}
for k, v in taskCosts.items():
    combined_dict[f'cost of the tasks of instance ({k})'] = v
for k, v in resourceCosts.items():
    combined_dict[f'Total costs of resource ({k})'] = v
for k, v in resourcesPercentageUsage.items():
    combined_dict[f'total usage of resource ({k}) in percentage'] = v

if bool(extraLog):
    combined_dict.update(extraLog)

all_keys = set(combined_dict.keys())

# Write the combined dictionary to the CSV file
with open('../logs/logExtra.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=all_keys)
    writer.writeheader()
    writer.writerow(combined_dict)


pm4py.write_xes(event_log, '../logs/log.xes')

try:
  os.remove(diagbpPath)
except OSError as e:
  print(f"Error deleting {diagbpPath}: {e}")

try:
  os.remove(bpmnPath)
except OSError as e:
  print(f"Error deleting {bpmnPath}: {e}")