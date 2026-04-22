from typing import List, TypedDict

from langgraph.graph import StateGraph

class AgentState(TypedDict):
	values: List[int]
	name: str
	operator: str
	result: str

def perform_math_function(state: AgentState) -> AgentState:
	"""This function performs mathematical operations from an integer array depending on the operator provided. 
	If operator is '*' it's multiplication if operator is '+' it's addition"""
	valid_operands = ["+", "*"]

	if len(state["values"]) <= 0 or state["name"] is None:
		raise ValueError("Provide the necessary fields!")
	
	if state["operator"] not in valid_operands:
		raise ValueError("Operator is invalid")
	

	if state["operator"] == "*":
		res = state["values"][0]
		for val in state["values"]:
			res *= val
		state["result"] = f"{state['name']} your operator was {state['operator']} your result is {res}"
	elif state["operator"] == "+":
		state["result"] = f"{state['name']} your operator was {state['operator']} your result is {sum(state['values'])}"
	
	
	return state
graph = StateGraph(AgentState)
graph.add_node("processor", perform_math_function)
graph.set_entry_point("processor")
graph.set_finish_point("processor")

app = graph.compile()
answers = app.invoke({"values": [1,2,3,4], "name":"carlos", "operator": "*"})
print(answers["result"])