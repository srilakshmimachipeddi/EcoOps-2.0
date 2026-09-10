"""
StateGraph implementation compatible with LangGraph StateGraph API.
Supports typed state, nodes, edges, conditional routing, and step observability.
"""

from typing import Dict, Any, Callable, List, Optional, Union, get_type_hints
import copy
import operator

END = "__end__"


class CompiledStateGraph:
    """Compiled state graph capable of invoking inputs through the node pipeline."""

    def __init__(
        self,
        schema: Any,
        nodes: Dict[str, Callable],
        entry_point: Optional[str],
        edges: Dict[str, str],
        conditional_edges: Dict[str, tuple[Callable, Dict[str, str]]],
    ):
        self.schema = schema
        self.nodes = nodes
        self.entry_point = entry_point
        self.edges = edges
        self.conditional_edges = conditional_edges

    def invoke(self, initial_state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute state through graph until END is reached."""
        if not self.entry_point:
            raise ValueError("No entry point set for StateGraph.")

        state = copy.deepcopy(initial_state)

        # Ensure state has all required keys initialized if not present
        if "trace_log" not in state:
            state["trace_log"] = []

        current_node = self.entry_point
        visited_nodes = set()
        max_steps = 50
        step_count = 0

        while current_node != END and step_count < max_steps:
            step_count += 1
            if current_node not in self.nodes:
                raise ValueError(f"Node '{current_node}' not registered in StateGraph.")

            node_func = self.nodes[current_node]
            prev_trace_log = list(state.get("trace_log", []))
            
            # Execute node
            returned_state = node_func(state)
            if returned_state is not None and isinstance(returned_state, dict):
                # Handle Annotated[list, operator.add] for trace_log if newly returned
                new_traces = returned_state.get("trace_log", [])
                if isinstance(new_traces, list) and new_traces != prev_trace_log:
                    # If returned_state returned a new sublist, append or merge
                    if len(new_traces) > len(prev_trace_log):
                        state["trace_log"] = new_traces
                    else:
                        state["trace_log"] = prev_trace_log + [
                            t for t in new_traces if t not in prev_trace_log
                        ]
                
                # Merge rest of keys
                for k, v in returned_state.items():
                    if k != "trace_log":
                        state[k] = v

            # Determine next node
            if current_node in self.conditional_edges:
                router_func, path_map = self.conditional_edges[current_node]
                decision = router_func(state)
                next_node = path_map.get(decision, END)
            elif current_node in self.edges:
                next_node = self.edges[current_node]
            else:
                next_node = END

            current_node = next_node

        return state


class StateGraph:
    """StateGraph definition."""

    def __init__(self, state_schema: Any):
        self.state_schema = state_schema
        self.nodes: Dict[str, Callable] = {}
        self.entry_point: Optional[str] = None
        self.edges: Dict[str, str] = {}
        self.conditional_edges: Dict[str, tuple[Callable, Dict[str, str]]] = {}

    def add_node(self, name: str, func: Callable) -> None:
        self.nodes[name] = func

    def set_entry_point(self, name: str) -> None:
        if name not in self.nodes:
            # Entry point can be registered before or after add_node, but validated later
            pass
        self.entry_point = name

    def add_edge(self, start_key: str, end_key: str) -> None:
        self.edges[start_key] = end_key

    def add_conditional_edges(
        self,
        source: str,
        path: Callable,
        path_map: Dict[str, str],
    ) -> None:
        self.conditional_edges[source] = (path, path_map)

    def compile(self) -> CompiledStateGraph:
        if not self.entry_point:
            raise ValueError("StateGraph must have an entry point set before compile().")
        return CompiledStateGraph(
            schema=self.state_schema,
            nodes=dict(self.nodes),
            entry_point=self.entry_point,
            edges=dict(self.edges),
            conditional_edges=dict(self.conditional_edges),
        )
