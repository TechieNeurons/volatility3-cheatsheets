const width = window.innerWidth;
const height = window.innerHeight;

// for the search
const searchInput = document.getElementById('plugin-search');
const osSelector = document.getElementById('os-selector');
const resultsContainer = document.getElementById('search-results');

// for the themes
const themeToggle = document.getElementById('theme-toggle');
const currentTheme = localStorage.getItem('theme');

if (currentTheme) {
    document.documentElement.setAttribute('data-theme', currentTheme);
}

themeToggle.addEventListener('click', () => {
    let theme = document.documentElement.getAttribute('data-theme');
    
    if (theme === 'light') {
        document.documentElement.setAttribute('data-theme', 'dark');
        localStorage.setItem('theme', 'dark');
    } else {
        document.documentElement.setAttribute('data-theme', 'light');
        localStorage.setItem('theme', 'light');
    }
});

const svg = d3.select("#tree-display")
    .attr("width", width)
    .attr("height", height)
    .call(d3.zoom().on("zoom", (event) => {
        svgGroup.attr("transform", event.transform);
    }))
    .append("g");

// find center of screen
const centerX = width / 2;
const centerY = height / 2;

// center tree
const svgGroup = svg.append("g").attr("transform", `translate(${centerX - 100}, ${centerY})`);
const treeLayout = d3.tree().nodeSize([60, 300]);

// FETCH THE EXTERNAL JSON FILE
d3.json("data.json").then(data => {
    let root = d3.hierarchy(data);
    root.x0 = height / 2;
    root.y0 = 0;

    // Collapse all except top level
    if (root.children) {
        root.children.forEach(collapse);
    }

    update(root);

    function collapse(d) {
        if (d.children) {
            d._children = d.children;
            d._children.forEach(collapse);
            d.children = null;
        }
    }

    function update(source) {
        const nodes = treeLayout(root).descendants();
        const links = nodes.slice(1);

        nodes.forEach(d => { d.y = d.depth * 300; });

        const node = svgGroup.selectAll('g.node')
            .data(nodes, d => d.data.name);

        const nodeEnter = node.enter().append('g')
            .attr('class', 'node')
            .attr("transform", d => `translate(${source.y0},${source.x0})`)
            .on('click', (event, d) => {
                if (d.depth === 0) return; // can't click on root "volatility 3"

                // activate the click on folder
                if (d.children || d._children) {
                    d.children = d.children ? null : d._children;
                    update(d);
                    centerNode(d);
                } else {
                    if (d.data.help || d.data.terminal_help) {
                        showInfo(d.data);
                        centerNode(d);
                    }
                }
            });

        nodeEnter.append('circle').attr('r', 8);

        nodeEnter.append('text')
            .attr("dy", ".35em")
            .attr("x", d => d.children || d._children ? -20 : 20)
            .attr("text-anchor", d => d.children || d._children ? "end" : "start")
            .text(d => d.data.name);

        const nodeUpdate = nodeEnter.merge(node);
        nodeUpdate.transition().duration(500)
            .attr("transform", d => `translate(${d.y},${d.x})`);

        nodeUpdate.select('circle')
            .attr('r', 8)
            .style("fill", d => {
                if (d.depth ===0) return "#ffffff";
                return d._children ? "#ff0000" : "#cc0000";})
            .style("stroke", "#ffffff")
            .style("stroke-width", "2px");

        node.exit().transition().duration(500)
            .attr("transform", d => `translate(${source.y},${source.x})`).remove();

        const link = svgGroup.selectAll('path.link').data(links, d => d.data.name);
        const linkEnter = link.enter().insert('path', "g")
            .attr("class", "link")
            .attr('d', d => {
                const o = {x: source.x0, y: source.y0};
                return diagonal(o, o);
            });

        link.merge(linkEnter).transition().duration(500)
            .attr('d', d => diagonal(d, d.parent));

        link.exit().remove();
        nodes.forEach(d => { d.x0 = d.x; d.y0 = d.y; });
    }

// IMPROVED SEARCH LOGIC
    searchInput.addEventListener('input', function() {
        const query = this.value.toLowerCase();
        const selectedOS = osSelector.value;
        resultsContainer.innerHTML = '';
        
        if (query.length < 2) {
            resultsContainer.style.display = 'none';
            return;
        }

        const osData = data.children.find(d => d.name === selectedOS);
        if (!osData) return;

        const matches = [];

        // We track the 'path' as we dig through the categories
        function findPlugins(node, path = []) {
            let currentPath = [...path, node.name];
            
            // Check if it's a leaf node
            if (node.help || node.terminal_help) { 
                if (node.name.toLowerCase().includes(query)) {
                    matches.push({
                        data: node,
                        path: currentPath // Store the breadcrumb path
                    });
                }
            }
            if (node.children) node.children.forEach(c => findPlugins(c, currentPath));
            if (node._children) node._children.forEach(c => findPlugins(c, currentPath));
        }

        findPlugins(osData, [selectedOS]);

        if (matches.length > 0) {
            resultsContainer.style.display = 'block';
            matches.forEach(match => {
                const div = document.createElement('div');
                div.className = 'search-item';
                
                // Show the category path above the plugin name
                const categoryPath = match.path.slice(1, -1).join(' > ');
                div.innerHTML = `
                    <small style="color: #888; display: block; font-size: 10px;">${categoryPath}</small>
                    <span style="color: #00ff41;">${match.data.name}</span>
                `;
                
                div.onclick = () => {
                    expandAndCenter(match.path); // Use our new helper function
                    resultsContainer.style.display = 'none';
                    searchInput.value = '';
                };
                resultsContainer.appendChild(div);
            });
        } else {
            resultsContainer.style.display = 'none';
        }
    });

    // Close search if clicking outside
    document.addEventListener('click', (e) => {
        if (!document.getElementById('search-container').contains(e.target)) {
            resultsContainer.style.display = 'none';
        }
    });

    function diagonal(s, d) {
        return `M ${s.y} ${s.x} C ${(s.y + d.y) / 2} ${s.x}, ${(s.y + d.y) / 2} ${d.x}, ${d.y} ${d.x}`;
    }

    function showInfo(data) {
        const box = document.getElementById('info-box');
        const descContainer = document.getElementById('plugin-desc-container');

        box.style.display = 'flex';
        document.getElementById('plugin-name').innerText = data.name;

        // 2. Handle Multi-line Description
        descContainer.innerHTML = ''; // Clear old text
        if (Array.isArray(data.help)) {
            // If it's an array, create a <p> for each string
            data.help.forEach(line => {
                const p = document.createElement('p');
                p.innerText = line;
                descContainer.appendChild(p);
            });
        } else {
            // Fallback for single strings
            const p = document.createElement('p');
            p.innerText = data.help || "No description available.";
            descContainer.appendChild(p);
        }

        // 3. Set Terminal Help text
        document.getElementById('plugin-terminal').innerText = data.terminal_help || "No terminal help found.";

        box.style.display = 'flex';
    }

    function centerNode(source) {
        // Select the actual SVG element by its ID
        const baseSvg = d3.select("#tree-display");
        const t = d3.zoomTransform(baseSvg.node());

        // Calculate centering coordinates
        // window.innerWidth / 3 keeps the node slightly left of center 
        // so the info-box doesn't cover it.
        let x = -source.y * t.k + (window.innerWidth / 3); 
        let y = -source.x * t.k + (window.innerHeight / 2);

        // Call transition directly on the baseSvg selection
        baseSvg.transition()
            .duration(750)
            .call(d3.zoom().transform, d3.zoomIdentity.translate(x, y).scale(t.k));
    }

    function expandAndCenter(pathArray) {
        let currentNode = root;

        // We skip the first element ("windows") because 'root' is already there
        for (let i = 1; i < pathArray.length; i++) {
            const targetName = pathArray[i];
            const children = currentNode.children ? currentNode.children : currentNode._children;
            
            if (children) {
                const nextNode = children.find(c => c.data.name === targetName);
                if (nextNode) {
                    // If this folder is collapsed, expand it
                    if (nextNode._children) {
                        nextNode.children = nextNode._children;
                        nextNode._children = null;
                    }
                    currentNode = nextNode;
                }
            }
        }

        // 1. Re-draw the tree with the newly expanded folders
        update(currentNode);

        // 2. Wait a split second for D3 to calculate positions, then move camera
        setTimeout(() => {
            showInfo(currentNode.data);
            centerNode(currentNode);
        }, 200);
    }
});