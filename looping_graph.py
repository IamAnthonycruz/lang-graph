from langgraph.graph import StateGraph, END
import random
from typing import Dict, List, TypedDict

class AgentState(TypedDict):
	name: str
	number: List[int]
	counter: int


def greeting(state: AgentState):
	"""Greeting node"""

	state["name"] = f"hi, there {state['name']}"
	state['counter'] = 0

	return state


def random_node(state:AgentState) -> AgentState:
	"""Generate a random number from 0 to 10"""

	state["number"].append(random.randint(0,10))
	state["counter"] += 1

	return state

def should_continue(state:AgentState) -> AgentState:
	"""Function to decide what to do next"""
	if state["counter"] < 5:
		print("ENTERING LOOP")
		return "loop"
	else:
		return "exit"
	
graph = StateGraph(AgentState)

graph.add_node("greeting", greeting)
graph.add_node("random", random_node)
graph.add_edge("greeting", "random")

graph.add_conditional_edges(

	"random",
	should_continue,
	{
		"loop": "random",
		"exit": END
	}
)

graph.set_entry_point("greeting")

app = graph.compile()