import networkx as nx
import matplotlib.pyplot as plt


def visualize_workflow(workflow):
    """Visualize the university assistant workflow graph."""
    graph = workflow.get_graph()
    G = nx.DiGraph()
    for node in graph.nodes:
        G.add_node(node)
    for edge in graph.edges:
        G.add_edge(edge[0], edge[1])

    plt.figure(figsize=(12, 8))
    pos = nx.spring_layout(G, k=3, iterations=50)
    
    # Color nodes based on their function
    node_colors = []
    for node in G.nodes():
        if 'collect_name' in node:
            node_colors.append('#4CAF50')  # Green for start
        elif 'university_chat' in node:
            node_colors.append('#2196F3')  # Blue for main chat
        elif 'goodbye' in node:
            node_colors.append('#FF5722')  # Red for end
        else:
            node_colors.append('#FFC107')  # Yellow for others
    
    nx.draw(G, pos, with_labels=True, node_size=3000, node_color=node_colors, 
            font_size=10, font_weight="bold", arrows=True, 
            edge_color='gray', arrowsize=20)
    plt.title("University Assistant Workflow Graph", fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.show()


def generate_mermaid_code(workflow):
    """Generate Mermaid diagram code for university assistant workflow."""
    mermaid_code = workflow.get_graph().draw_mermaid()
    lines = mermaid_code.splitlines()
    filtered_lines = [line for line in lines if 'classDef' not in line]
    filtered_lines = [line for line in filtered_lines if 'linear' not in line]
    mermaid_code = "\n".join(filtered_lines)
    
    # University-themed styling
    mermaid_code += """
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:2px,color:#000
    classDef start fill:#4CAF50,stroke:#2E7D32,stroke-width:3px,color:#fff
    classDef chat fill:#2196F3,stroke:#1565C0,stroke-width:3px,color:#fff
    classDef end fill:#FF5722,stroke:#D84315,stroke-width:3px,color:#fff
    
    class collect_name start
    class university_chat chat
    class goodbye end
    """
    
    return mermaid_code


def save_workflow_diagram(workflow, filename="university_workflow"):
    """Save workflow diagram as PNG and mermaid code."""
    try:
        # Save as PNG
        workflow.get_graph().draw_png(f"{filename}.png")
        print(f"Workflow graph saved as '{filename}.png'")
        
        # Save mermaid code
        mermaid_code = generate_mermaid_code(workflow)
        with open(f"{filename}.mmd", "w") as f:
            f.write(mermaid_code)
        print(f"Mermaid diagram saved as '{filename}.mmd'")
        
    except Exception as e:
        print(f"Could not save workflow diagram: {e}")