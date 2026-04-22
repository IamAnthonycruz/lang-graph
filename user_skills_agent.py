

from typing import List, TypedDict

from langgraph.graph import StateGraph


class AgentState(TypedDict):
	name:str
	age: int
	skills: List[str]
	final:str

def first_node(state: AgentState):
	state['final'] = f'{state['name']} hello there!\n'
	return state

def second_node(state:AgentState):
	state['final'] += f"You are {state['age']}\n"
	return state

def third_node(state:AgentState):
	state['final'] += f'These are your skills: {" ".join(state["skills"])}'
	return state

graph = StateGraph(AgentState)
graph.add_node('first_node', first_node)
graph.add_node('second_node', second_node)
graph.add_node('third_node',third_node)
graph.set_entry_point('first_node')
graph.add_edge('first_node','second_node')
graph.add_edge('second_node','third_node')
graph.set_finish_point('third_node')
app = graph.compile()

answer = app.invoke({'name': "Carlos", 'age': 12, 'skills':['python', 'java']})
print(answer['final'])