import os
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from functools import partial

# Load environment variables
load_dotenv()

from nodes.routes import (
    collect_name_router,
    university_chat_router,
    goodbye_router
)
from models.userstate import State
from nodes.node_functions import (
    collect_name,
    university_chat,
    goodbye
)

# Set up project name
os.environ["LANGCHAIN_PROJECT"] = "UNIVERSITY_ASSISTANT"

# NO LLM NEEDED - Using RAG only
llm = None  # We don't need this

# Create the simplified university assistant workflow
workflow = StateGraph(State)

# Add nodes for university assistant (pass None for llm)
workflow.add_node("collect_name", partial(collect_name, llm))
workflow.add_node("university_chat", partial(university_chat, llm))
workflow.add_node("goodbye", partial(goodbye, llm))

# Set entry point
workflow.set_entry_point("collect_name")

# Add edges for simple conversation flow
workflow.add_edge(START, "collect_name")
workflow.add_conditional_edges("collect_name", collect_name_router, ["collect_name", "university_chat"])
workflow.add_conditional_edges("university_chat", university_chat_router, ["university_chat", "goodbye"])
workflow.add_edge("goodbye", END)

# Compile the workflow
compiled_workflow = workflow.compile()

# Generate workflow visualization
try:
    compiled_workflow.get_graph().draw_png("university_workflow_graph.png")
    print("Workflow graph saved as 'university_workflow_graph.png'")
except Exception as e:
    print(f"Could not generate workflow graph: {e}")

# Initialize state for university assistant
def create_initial_state():
    """Create initial state for university assistant."""
    return State(
        name=None,
        history=[],
        retry_count=0,
        current_node="collect_name",
        next_question=None,
        session_id=None,
        last_query=None,
        conversation_ended=False
    )

def run_workflow(state):
    """Run the university assistant workflow."""
    return compiled_workflow.invoke(state)

# Test the workflow if run directly
if __name__ == "__main__":
    print("🎓 University Assistant Workflow Initialized")
    print("Available nodes:", ["collect_name", "university_chat", "goodbye"])
    print("Using RAG endpoint:", os.getenv("UNIVERSITY_RAG_ENDPOINT", "Not configured"))