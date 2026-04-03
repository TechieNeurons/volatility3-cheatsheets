import pandas as pd
import networkx as nx
import plotly.graph_objects as go
import re

def parse_vadwalk(file_path):
    data = []
    # Regex to capture the columns based on the Volatility 3 output format
    # PID Process Offset Parent Left Right Start End Tag
    pattern = re.compile(r'(\d+)\s+(\S+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(\S+)')
    
    with open(file_path, 'r') as f:
        for line in f:
            match = pattern.search(line)
            if match:
                data.append(match.groups())
    
    df = pd.DataFrame(data, columns=['PID', 'Process', 'Offset', 'Parent', 'Left', 'Right', 'Start', 'End', 'Tag'])
    return df

def create_interactive_tree(df):
    G = nx.DiGraph()
    
    # Add nodes and edges
    for _, row in df.iterrows():
        node_id = row['Offset']
        label = f"Tag: {row['Tag']}<br>Start: {row['Start']}<br>End: {row['End']}"
        G.add_node(node_id, label=label, start=row['Start'], end=row['End'])
        
        # In VAD trees, nodes are linked via Left and Right pointers
        if row['Left'] != '0x0':
            G.add_edge(node_id, row['Left'], side='Left')
        if row['Right'] != '0x0':
            G.add_edge(node_id, row['Right'], side='Right')

    # Calculate tree layout (Reingold-Tilford algorithm)
    # We use Graphviz 'dot' layout if available, otherwise fallback to shell or spectral
    try:
        pos = nx.nx_agraph.graphviz_layout(G, prog='dot')
    except:
        pos = nx.spring_layout(G) # Fallback

    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=1, color='#888'),
        hoverinfo='none',
        mode='lines')

    node_x = []
    node_y = []
    node_text = []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(G.nodes[node]['label'])

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers',
        hoverinfo='text',
        text=node_text,
        marker=dict(
            showscale=False,
            color='skyblue',
            size=20,
            line_width=2))

    fig = go.Figure(data=[edge_trace, node_trace],
                 layout=go.Layout(
                    title='Windows VAD Tree Visualization (PID 6316)',
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=20,l=5,r=5,t=40),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                )
    
    fig.write_html('vad_tree.html')
    print("Success: 'vad_tree.html' has been generated.")

if __name__ == "__main__":
    # Ensure your file is named vadwalk.txt in the same directory
    try:
        vad_df = parse_vadwalk('vadwalk.txt')
        if vad_df.empty:
            print("Error: No data parsed. Check if vadwalk.txt matches the expected format.")
        else:
            create_interactive_tree(vad_df)
    except FileNotFoundError:
        print("Error: vadwalk.txt not found.")