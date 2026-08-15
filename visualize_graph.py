from agents.langgraph_orchestrator import build_graph

app = build_graph()
try:
    graph_image = app.get_graph().draw_mermaid_png()
    with open("agents/pipeline_graph.png", "wb") as f:
        f.write(graph_image)
    print("Graph saved to agents/pipeline_graph.png")
except Exception as e:
    print(f"PNG export failed: {e}")
    print("Saving as Mermaid text instead...")
    mermaid = app.get_graph().draw_mermaid()
    with open("agents/pipeline_graph.md", "w") as f:
        f.write(mermaid)
    print("Graph saved to agents/pipeline_graph.md")