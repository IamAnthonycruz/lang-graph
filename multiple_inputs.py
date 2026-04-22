from typing import List, TypedDict

from langgraph.graph import StateGraph


class AgentState(TypedDict):
	values: List[int]
	name: str
	result: str

def process_values(state: AgentState) -> AgentState:
	"""This function handles multiple different inputs"""
	print(state)
	state["result"] = f"Hi there {state["name"]}! Your sum = {sum(state['values'])}"
	print(state)
	return state
graph = StateGraph(AgentState)
graph.add_node("processor", process_values)

graph.set_entry_point("processor")
graph.set_finish_point("processor")

app = graph.compile()
answers = app.invoke({"values": [1,2,3,4], "name":"carlos" })
print(answers["result"])