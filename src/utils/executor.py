from nodes import node_functions, routes
import logging
from typing import Tuple, Callable, Optional, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UniversityWorkflowExecutor:
    """Executor for university assistant workflow."""
    
    def __init__(self):
        """Initialize the workflow executor."""
        self.supported_nodes = {
            "collect_name": {
                "function": node_functions.collect_name,
                "router": routes.collect_name_router,
                "description": "Collects user's name for personalized interaction"
            },
            "university_chat": {
                "function": node_functions.university_chat,
                "router": routes.university_chat_router,
                "description": "Handles university-related queries using RAG"
            },
            "goodbye": {
                "function": node_functions.goodbye,
                "router": routes.goodbye_router,
                "description": "Handles conversation ending"
            }
        }
        logger.info(f"Workflow executor initialized with {len(self.supported_nodes)} nodes")

    def get_func_and_router(self, node_name: str) -> Tuple[Optional[Callable], Optional[Callable]]:
        """
        Get function and router for a given node name.
        
        Args:
            node_name (str): Name of the node
            
        Returns:
            Tuple[Optional[Callable], Optional[Callable]]: Function and router for the node
        """
        # Remove '_node' suffix if present for backward compatibility
        clean_node_name = node_name.replace("_node", "")
        
        if clean_node_name in self.supported_nodes:
            node_info = self.supported_nodes[clean_node_name]
            return node_info["function"], node_info["router"]
        
        # Fallback to original method for backward compatibility
        try:
            func = getattr(node_functions, clean_node_name, None)
            router = getattr(routes, f"{clean_node_name}_router", None)
            
            if func:
                logger.info(f"Found function for node: {clean_node_name}")
            if router:
                logger.info(f"Found router for node: {clean_node_name}")
                
            return func, router
            
        except AttributeError as e:
            logger.error(f"Could not find function or router for node '{clean_node_name}': {e}")
            return None, None

    def execute_node(self, node_name: str, llm, state: Dict[str, Any], user_input: str = None) -> Dict[str, Any]:
        """
        Execute a specific node in the university workflow.
        
        Args:
            node_name (str): Name of the node to execute
            llm: Language model instance
            state (Dict[str, Any]): Current conversation state
            user_input (str, optional): User's input
            
        Returns:
            Dict[str, Any]: Updated state after node execution
        """
        logger.info(f"Executing node: {node_name} with input: {user_input is not None}")
        
        # Get function and router for the node
        func, router = self.get_func_and_router(node_name)
        next_node = None

        if func:
            try:
                # Execute the node function
                logger.info(f"Calling function for node: {node_name}")
                state = func(llm, state, user_input)
                
                # Determine next node if user input was provided and router exists
                if user_input and router:
                    logger.info(f"Calling router for node: {node_name}")
                    next_node = router(state)
                    logger.info(f"Router determined next node: {next_node}")
                    
            except Exception as e:
                logger.error(f"Error executing node '{node_name}': {e}")
                # Add error handling to state
                state["error"] = f"Error in {node_name}: {str(e)}"
                state["next_question"] = "I'm sorry, I encountered an error. Please try again."
        else:
            logger.error(f"No function found for node: {node_name}")
            state["error"] = f"Unknown node: {node_name}"
            state["next_question"] = "I'm sorry, I don't understand that request."

        # Update current node in state
        state["current_node"] = next_node if next_node else node_name
        
        logger.info(f"Node execution completed. Next node: {state.get('current_node')}")
        return state

    def validate_state(self, state: Dict[str, Any]) -> bool:
        """
        Validate that the state has required fields.
        
        Args:
            state (Dict[str, Any]): State to validate
            
        Returns:
            bool: True if state is valid
        """
        required_fields = ["current_node", "history", "retry_count"]
        
        for field in required_fields:
            if field not in state:
                logger.warning(f"Missing required field in state: {field}")
                return False
        
        return True

    def get_node_info(self, node_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific node.
        
        Args:
            node_name (str): Name of the node
            
        Returns:
            Optional[Dict[str, Any]]: Node information or None if not found
        """
        clean_node_name = node_name.replace("_node", "")
        return self.supported_nodes.get(clean_node_name)

    def list_available_nodes(self) -> list:
        """
        Get list of all available nodes.
        
        Returns:
            list: List of available node names
        """
        return list(self.supported_nodes.keys())


# Global executor instance for backward compatibility
workflow_executor = UniversityWorkflowExecutor()

def get_func_and_router(node_name: str) -> Tuple[Optional[Callable], Optional[Callable]]:
    """Backward compatibility function."""
    return workflow_executor.get_func_and_router(node_name)

def execute_node(node_name: str, llm, state: Dict[str, Any], user_input: str = None) -> Dict[str, Any]:
    """Backward compatibility function."""
    return workflow_executor.execute_node(node_name, llm, state, user_input)