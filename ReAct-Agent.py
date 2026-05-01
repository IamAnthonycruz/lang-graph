from typing import Annotated, Sequence, TypedDict

from langgraph.graph import END, StateGraph, add_messages
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage
from langchain_core.messages import ToolMessage
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import ToolNode

class AgentState(TypedDict):
	messages: Annotated[Sequence[BaseMessage], add_messages]

@tool
def add(a:int, b:int):
	"""This is an addition function that adds 2 numbers together"""
	return a + b;

tools = [add]

models = ChatOpenAI(model="gpt-4o").bind_tools(tools)

def model_call(state: AgentState) -> AgentState:
	system_prompt = SystemMessage(content="You are my AI assistant, please answer my query to the best of your ability.")
	response = model.invoke([system_prompt] + state["messages"])
	return {"messages": [response]}
	

def should_continue(state:AgentState):
	messages = state["messages"]
	last_messages = messages[-1]

	if not last_messages.tool_calls:
		return "end"
	else:
		return "continue"

graph = StateGraph(AgentState)
graph.add_node("our_agent", model_call)

tool_node = ToolNode(tools=tools)
graph.set_entry_point("our_agent")

graph.add_conditional_edges(
	"our_agent",
	should_continue,
	{
		"continue": "tools",
		"end": END
	}
)

graph.add_edge("tools", "our_agent")

app = graph.compile()
