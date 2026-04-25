from typing import TypedDict
from langgraph.graph import StateGraph, START, END


class AgentState(TypedDict):
	number1: int
	operator: str
	number2: int
	finalNumber: int

def adder(state:AgentState) -> AgentState:
	"""This node adds the two numbers"""

	state['finalNumber'] = state['number1'] + state['number2']
	return state

def subtractor(state:AgentState) -> AgentState:
	"""This node subtracts the two numbers"""

	state['finalNumber']= state['number1'] - state['number2']
	return state

def decide_next_node(state:AgentState):
	"""This node will select the next node of the graph"""
	if state['operator'] == "+":
		return "addition_operation"
	elif state['operator'] == "-":
		return "subtraction_operation"

graph = StateGraph(AgentState)
graph.add_node("add_node",adder)
graph.add_node("subtract_node", subtractor)
graph.add_node("router", lambda state:state)
graph.add_node("router_2", lambda state:state)
graph.add_node("add_node_2", adder)
graph.add_node("subtract_node_2", subtractor)


graph.add_edge(START,"router")
graph.add_conditional_edges("router",
							decide_next_node,{
								"addition_operation": "add_node",
								"subtraction_operation": "subtract_node"
							} 
							
							)

graph.add_edge("add_node","router_2")
graph.add_edge("subtract_node","router_2")
graph.add_conditional_edges("router_2",
							decide_next_node, {
								"addition_operation": "add_node_2",
								"subtraction_operation": "subtract_node_2"
							}
							)
graph.add_edge("add_node_2", END)
graph.add_edge("subtract_node_2", END)

app = graph.compile()



