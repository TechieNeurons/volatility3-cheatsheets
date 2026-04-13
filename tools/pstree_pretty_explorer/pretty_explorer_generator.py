import os
import sys
import json

def parse_pretty_pstree(file_path):
    rows = []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if '|' not in line:
                    continue
                
                parts = [p.strip() for p in line.split('|')]
                # Parts[0] is the tree indentation (* |)
                indent_part = parts[0]
                depth = indent_part.count('*')
                
                # Check if this is a data row (PID should be a number)
                if len(parts) >= 14 and parts[1].isdigit():
                    rows.append({
                        'pid': parts[1],
                        'ppid': parts[2],
                        'name': parts[3].replace('*', ''),
                        'offset': parts[4],
                        'threads': parts[5],
                        'handles': parts[6],
                        'session': parts[7],
                        'wow64': parts[8],
                        'create': parts[9],
                        'exit': parts[10],
                        'audit': parts[11],
                        'cmd': parts[12],
                        'path': parts[13],
                        'depth': depth
                    })
    except Exception as e:
        print(f"[-] Parsing Error: {e}")
    
    print(f"[+] Successfully parsed {len(rows)} processes.")
    return rows

def generate_html(rows, output_file):
    json_data = json.dumps(rows)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Volatility 3 Pretty Explorer</title>
        <style>
            :root {{ --bg: #1e1e1e; --panel: #252526; --text: #d4d4d4; --blue: #569cd6; --border: #444; --mal: #ff6b6b; }}
            body {{ font-family: 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); margin: 0; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }}
            
            .controls {{ background: var(--panel); padding: 10px 20px; border-bottom: 1px solid var(--border); display: flex; gap: 20px; align-items: center; flex-shrink: 0; }}
            .input-group {{ display: flex; flex-direction: column; gap: 2px; }}
            .input-group label {{ font-size: 9px; text-transform: uppercase; color: #888; letter-spacing: 1px; font-weight: bold; }}
            input {{ background: #111; border: 1px solid var(--border); color: #fff; padding: 6px 12px; border-radius: 3px; font-size: 13px; outline: none; }}
            input:focus {{ border-color: var(--blue); }}
            
            .table-container {{ flex-grow: 1; overflow: auto; }}
            table {{ width: 100%; border-collapse: collapse; table-layout: fixed; min-width: 2500px; }}
            
            thead th {{ background: #333; color: #fff; padding: 10px; border: 1px solid var(--border); font-size: 11px; text-align: left; 
                         position: sticky; top: 0; z-index: 100; cursor: pointer; }}
            thead th:hover {{ background: #444; }}

            td {{ padding: 4px 10px; border: 1px solid #333; font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
            tr:hover {{ background: #2a2d2e; }}
            tr.hidden {{ display: none !important; }}
            
            .tree-node {{ display: flex; align-items: center; cursor: pointer; }}
            .toggle-icon {{ margin-right: 8px; color: var(--blue); font-family: monospace; width: 12px; font-weight: bold; text-align: center; }}
            .suspicious {{ color: var(--mal); font-weight: bold; }}
            code {{ color: #ce9178; font-family: 'Consolas', monospace; font-size: 10px; }}
        </style>
    </head>
    <body>
        <div class="controls">
            <div style="font-weight: bold; color: var(--blue); font-size: 16px; margin-right:10px;">V3 PSTREE PRETTY-EXPLORER</div>
            <div class="input-group">
                <label>Inclusion (Search Name/PID)</label>
                <input type="text" id="search" style="width: 280px;" placeholder="Keep match + parents...">
            </div>
            <div class="input-group">
                <label>Exclusion (Prune by Cmd)</label>
                <input type="text" id="exclude" style="width: 280px;" placeholder="Hide if Cmd contains...">
            </div>
        </div>

        <div class="table-container">
            <table id="procTable">
                <thead>
                    <tr>
                        <th onclick="applySort('name')" style="width: 300px;">ImageFileName</th>
                        <th onclick="applySort('pid')" style="width: 70px;">PID</th>
                        <th onclick="applySort('ppid')" style="width: 70px;">PPID</th>
                        <th onclick="applySort('offset')" style="width: 140px;">Offset(V)</th>
                        <th onclick="applySort('threads')" style="width: 60px;">Threads</th>
                        <th onclick="applySort('handles')" style="width: 60px;">Handles</th>
                        <th onclick="applySort('session')" style="width: 60px;">SessId</th>
                        <th onclick="applySort('wow64')" style="width: 60px;">Wow64</th>
                        <th onclick="applySort('create')" style="width: 180px;">CreateTime</th>
                        <th onclick="applySort('exit')" style="width: 180px;">ExitTime</th>
                        <th onclick="applySort('audit')" style="width: 120px;">Audit</th>
                        <th onclick="applySort('cmd')" style="width: 400px;">Cmd</th>
                        <th>Path</th>
                    </tr>
                </thead>
                <tbody id="tbody"></tbody>
            </table>
        </div>

        <script>
            const fullData = {json_data};
            let workingData = [...fullData];
            const tbody = document.getElementById('tbody');
            const searchBox = document.getElementById('search');
            const excludeBox = document.getElementById('exclude');
            const collapsed = new Set();

            function render() {{
                tbody.innerHTML = '';
                const includeVal = searchBox.value.toLowerCase();
                const excludeVal = excludeBox.value.toLowerCase();

                const matches = new Set();
                const ancestors = new Set();

                // 1. Core Logic: Inclusion + Exclusion
                fullData.forEach(p => {{
                    const inStr = (p.name + p.pid).toLowerCase();
                    const cmdStr = p.cmd.toLowerCase();
                    
                    // A node is valid if:
                    // - It matches inclusion (or inclusion is empty)
                    // - AND it DOES NOT match exclusion (if exclusion is not empty)
                    const isIncluded = includeVal === "" || inStr.includes(includeVal);
                    const isExcluded = excludeVal !== "" && cmdStr.includes(excludeVal);

                    if (isIncluded && !isExcluded) {{
                        matches.add(p.pid);
                        // Trace parents for inclusion context
                        let curr = p;
                        while(curr) {{
                            let parent = fullData.find(x => x.pid === curr.ppid);
                            if(parent) {{
                                ancestors.add(parent.pid);
                                curr = parent;
                            }} else curr = null;
                        }}
                    }}
                }});

                // 2. Map tree structure
                const tree = {{}};
                workingData.forEach(p => {{
                    if (!tree[p.ppid]) tree[p.ppid] = [];
                    tree[p.ppid].push(p);
                }});

                // 3. Recursive Build
                const allPids = new Set(workingData.map(x => x.pid));
                const roots = workingData.filter(p => p.ppid === "0" || !allPids.has(p.ppid));
                roots.forEach(r => buildRow(r, 0, tree, includeVal, matches, ancestors));
            }}

            function buildRow(p, depth, tree, isSearching, matches, ancestors) {{
                // Logic: Only show if it's a direct match OR a parent of a match
                if (isSearching && !matches.has(p.pid) && !ancestors.has(p.pid)) return;
                
                // Extra check for exclusion: If we are not searching, we still obey the exclusion filter strictly
                if (!isSearching && !matches.has(p.pid)) return;

                const children = tree[p.pid] || [];
                const hasChildren = children.length > 0;
                const tr = document.createElement('tr');
                tr.id = 'tr-' + p.pid;
                
                if (isNodeHidden(p.ppid)) tr.classList.add('hidden');

                const isMal = p.name.toLowerCase().includes('legit') || p.name.toLowerCase().includes('powershell') || p.name.toLowerCase().includes('not_a_virus');
                const isCollapsed = collapsed.has(p.pid);

                tr.innerHTML = `
                    <td style="padding-left: ${{depth * 18 + 10}}px">
                        <div class="tree-node" onclick="toggle('${{p.pid}}')">
                            <span class="toggle-icon">${{hasChildren ? (isCollapsed ? '▶' : '▼') : '○'}}</span>
                            <span class="${{isMal ? 'suspicious' : ''}}">${{p.name}}</span>
                        </div>
                    </td>
                    <td>${{p.pid}}</td><td>${{p.ppid}}</td>
                    <td><code>${{p.offset}}</code></td><td>${{p.threads}}</td>
                    <td>${{p.handles}}</td><td>${{p.session}}</td><td>${{p.wow64}}</td>
                    <td>${{p.create}}</td><td>${{p.exit}}</td><td>${{p.audit}}</td>
                    <td title="${{p.cmd}}">${{p.cmd}}</td><td title="${{p.path}}">${{p.path}}</td>
                `;
                tbody.appendChild(tr);
                children.forEach(c => buildRow(c, depth + 1, tree, isSearching, matches, ancestors));
            }}

            function isNodeHidden(ppid) {{
                if (ppid === "0") return false;
                if (collapsed.has(ppid)) return true;
                const p = fullData.find(x => x.pid === ppid);
                return p ? isNodeHidden(p.ppid) : false;
            }}

            function toggle(pid) {{
                if (collapsed.has(pid)) collapsed.delete(pid);
                else collapsed.add(pid);
                render();
            }}

            function applySort(key) {{
                workingData.sort((a, b) => {{
                    let vA = a[key].toLowerCase();
                    let vB = b[key].toLowerCase();
                    if(!isNaN(vA) && !isNaN(vB)) {{ vA = parseInt(vA); vB = parseInt(vB); }}
                    return vA > vB ? 1 : -1;
                }});
                render();
            }}

            searchBox.addEventListener('input', render);
            excludeBox.addEventListener('input', render);
            render();
        </script>
    </body>
    </html>
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

if __name__ == "__main__":
    infile = sys.argv[1] if len(sys.argv) > 1 else "pstree.txt"
    data = parse_pretty_pstree(infile)
    if data:
        generate_html(data, "pretty_pstree_explorer.html")
        print(f"[+] Done: Open pretty_pstree_explorer.html")
    else:
        print("[-] No data parsed.")
