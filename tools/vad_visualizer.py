import pandas as pd
import networkx as nx
import plotly.graph_objects as go
import re
import argparse
import sys

def parse_args():
    parser = argparse.ArgumentParser(description="VAD Tree Visualizer for Volatility 3")
    parser.add_argument("--vadwalk", help="Path to vadwalk.txt")
    parser.add_argument("--vadinfo", help="Path to vadinfo.txt")
    parser.add_argument("--output", default="vad_tree.html", help="Output HTML file")
    return parser.parse_args()

def normalize_off(offset_str):
    """Normalize hex offsets to match even if prefixes (like ffff) differ."""
    if not offset_str or offset_str == '0x0': return '0x0'
    clean = offset_str.lower().replace('0x', '')
    return clean[-12:] # Match the last 12 hex chars

def parse_vadwalk(path):
    data = []
    # Regex to capture: PID, Process, Offset, Parent, Left, Right, Start, End, Tag
    pattern = re.compile(r'(\d+)\s+(\S+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(\S+)')
    try:
        with open(path, 'r') as f:
            for line in f:
                match = pattern.search(line)
                if match:
                    items = list(match.groups())
                    # Normalize pointers for dictionary lookup
                    items[2] = normalize_off(items[2]) # Current Offset
                    items[3] = normalize_off(items[3]) # Parent
                    items[4] = normalize_off(items[4]) # Left
                    items[5] = normalize_off(items[5]) # Right
                    data.append(items)
        return pd.DataFrame(data, columns=['PID', 'Process', 'Offset', 'Parent', 'Left', 'Right', 'Start', 'End', 'Tag'])
    except Exception as e:
        print(f"[-] Error reading vadwalk: {e}")
        return pd.DataFrame()

def parse_vadinfo(path):
    info_dict = {}
    try:
        with open(path, 'r') as f:
            lines = f.readlines()
            
        for line in lines:
            parts = line.split()
            # Volatility 3 vadinfo lines typically start with PID
            if len(parts) >= 11 and parts[0].isdigit():
                offset = normalize_off(parts[2])
                protection = parts[6]
                # The file path is usually in the second to last column
                file_path = parts[10] if len(parts) > 10 else "N/A"
                
                info_dict[offset] = {
                    "Protection": protection,
                    "File": file_path
                }
        return info_dict
    except Exception as e:
        print(f"[-] Error reading vadinfo: {e}")
        return {}

def main():
    args = parse_args()
    df_walk = parse_vadwalk(args.vadwalk) if args.vadwalk else pd.DataFrame()
    info_dict = parse_vadinfo(args.vadinfo) if args.vadinfo else {}

    if df_walk.empty:
        print("[-] Error: No valid data found in vadwalk. Check file format.")
        return

    G = nx.DiGraph()
    
    # First pass: Add all nodes with their attributes
    for _, row in df_walk.iterrows():
        off_norm = row['Offset']
        details = info_dict.get(off_norm, {"Protection": "Unknown", "File": "N/A"})
        
        color = "#ADD8E6" 
        if "EXECUTE_READWRITE" in details['Protection']: color = "#FF4136" 
        elif "EXECUTE" in details['Protection']: color = "#FF851B" 
        elif "VadS" in row['Tag']: color = "#2ECC40" 

        label = (f"Offset: 0x{off_norm}<br>"
                 f"Range: {row['Start']}-{row['End']}<br>"
                 f"Tag: {row['Tag']}<br>"
                 f"Perms: {details['Protection']}<br>"
                 f"File: {details['File']}")
        
        G.add_node(off_norm, label=label, color=color)

    # Second pass: Only add edges if the destination node exists
    for _, row in df_walk.iterrows():
        off_norm = row['Offset']
        for side in ['Left', 'Right']:
            target = row[side]
            if target != '0' and G.has_node(target):
                G.add_edge(off_norm, target)

    if G.number_of_nodes() == 0:
        print("[-] No nodes to plot.")
        return

    # Layout logic
    try:
        from networkx.drawing.nx_agraph import graphviz_layout
        pos = graphviz_layout(G, prog='dot')
    except:
        pos = nx.spring_layout(G)

    # Plotly Rendering with safe attribute access
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    node_x, node_y, node_text, node_color = [], [], [], []
    for node in G.nodes():
        # Ensure we only plot nodes that have the expected attributes
        if 'label' in G.nodes[node]:
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_text.append(G.nodes[node]['label'])
            node_color.append(G.nodes[node]['color'])

    fig = go.Figure(data=[
        go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color='#888'), hoverinfo='none', mode='lines'),
        go.Scatter(x=node_x, y=node_y, mode='markers', hoverinfo='text', text=node_text,
                   marker=dict(size=15, color=node_color, line=dict(width=1, color='black')))
    ], layout=go.Layout(title="Windows VAD Tree - Interactive Malware Analysis", hovermode='closest'))
    
    fig.write_html(args.output)
    print(f"[+] Success: {args.output} generated.")

if __name__ == "__main__":
    main()
