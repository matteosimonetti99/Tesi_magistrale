from procsim.properties import Properties
from procsim.simulator import Simulator
import json
from datetime import datetime

diagramPath = "./diagrams/example_diagram.bpmn"
globalProperties = json.load(open('./diagrams/global_properties.json'))
simulationProperties = json.load(open('./diagrams/simulation_properties.json'))

properties = Properties(diagramPath, globalProperties, simulationProperties)

simulator = Simulator(properties)
simulator.run(datetime(2020, 9, 1), endDate = datetime(2020, 10, 31))