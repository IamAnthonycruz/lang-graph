from typing import TypedDict

from langgraph.graph import StateGraph


class AgentState(TypedDict):
	name: str

def compliment_node(state: AgentState):
	"""This function creates a compliment"""
	state["name"] = f"{state["name"]} you're doing an amazing job learning LangGraph!"
	return state
graph = StateGraph(AgentState)
graph.add_node("complimenter", compliment_node)
graph.set_entry_point("complimenter")
graph.set_finish_point("complimenter")
app = graph.compile()
result = app.invoke({"name": "Carlos"})
print(result["name"])