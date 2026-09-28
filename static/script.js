/**
 * script.js
 * ---------
 * Client-side behavior for the Policy Conflict & Staleness Detector:
 *   - Upload page: shows the list of selected files before submit.
 *   - Dashboard page: renders Chart.js charts and a simple SVG relationship
 *     graph from the JSON data embedded by the Flask template.
 */

document.addEventListener("DOMContentLoaded", function () {
    initFileListPreview();
    initTopicChart();
    initFindingsChart();
    initRelationshipGraph();
});

/* ---------------------------------------------------------------------- */
/* Upload page: file list preview                                          */
/* ---------------------------------------------------------------------- */
function initFileListPreview() {
    const input = document.getElementById("policy_files");
    const listEl = document.getElementById("fileList");
    if (!input || !listEl) return;

    input.addEventListener("change", function () {
        if (!input.files || input.files.length === 0) {
            listEl.innerHTML = "";
            return;
        }
        const names = Array.from(input.files).map((f) => f.name);
        listEl.innerHTML =
            "<strong>" + names.length + " file(s) selected:</strong> " + names.join(", ");
    });
}

/* ---------------------------------------------------------------------- */
/* Dashboard page: charts                                                  */
/* ---------------------------------------------------------------------- */
function readEmbeddedJson(elementId) {
    const el = document.getElementById(elementId);
    if (!el) return null;
    try {
        return JSON.parse(el.textContent);
    } catch (e) {
        console.error("Failed to parse embedded JSON for " + elementId, e);
        return null;
    }
}

function initTopicChart() {
    const canvas = document.getElementById("topicChart");
    const data = readEmbeddedJson("topic-data");
    if (!canvas || !data || typeof Chart === "undefined") return;

    const labels = Object.keys(data);
    const values = Object.values(data);

    const palette = [
        "#1565c0", "#00b894", "#e6a817", "#d64545", "#7c4dff",
        "#00acc1", "#8d6e63", "#5c6bc0", "#26a69a",
    ];

    new Chart(canvas.getContext("2d"), {
        type: "doughnut",
        data: {
            labels: labels,
            datasets: [
                {
                    data: values,
                    backgroundColor: labels.map((_, i) => palette[i % palette.length]),
                    borderWidth: 2,
                    borderColor: "#ffffff",
                },
            ],
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: "right", labels: { boxWidth: 12, font: { size: 11 } } },
            },
        },
    });
}

function initFindingsChart() {
    const canvas = document.getElementById("findingsChart");
    const data = readEmbeddedJson("findings-data");
    if (!canvas || !data || typeof Chart === "undefined") return;

    const labels = Object.keys(data);
    const values = Object.values(data);

    new Chart(canvas.getContext("2d"), {
        type: "bar",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Count",
                    data: values,
                    backgroundColor: ["#d64545", "#e6a817", "#6b7280", "#00b894"],
                    borderRadius: 6,
                },
            ],
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, ticks: { precision: 0 } },
            },
        },
    });
}

/* ---------------------------------------------------------------------- */
/* Dashboard page: lightweight SVG relationship graph (no external libs)   */
/* ---------------------------------------------------------------------- */
function initRelationshipGraph() {
    const container = document.getElementById("graphCanvas");
    const data = readEmbeddedJson("graph-data");
    if (!container || !data) return;

    const nodes = data.nodes || [];
    const edges = data.edges || [];

    if (nodes.length === 0) {
        container.innerHTML = '<p class="text-muted mb-0">No documents to visualize yet.</p>';
        return;
    }

    const width = container.clientWidth || 800;
    const height = 380;
    const radius = Math.min(width, height) / 2 - 90;
    const centerX = width / 2;
    const centerY = height / 2;

    // Position nodes evenly around a circle.
    const positions = {};
    nodes.forEach((node, i) => {
        const angle = (2 * Math.PI * i) / nodes.length - Math.PI / 2;
        positions[node.id] = {
            x: centerX + radius * Math.cos(angle),
            y: centerY + radius * Math.sin(angle),
        };
    });

    const relationClass = {
        conflict: "graph-edge-conflict",
        redundant: "graph-edge-redundant",
        related: "graph-edge-related",
    };

    let svg = `<svg viewBox="0 0 ${width} ${height}" width="100%" height="${height}" xmlns="http://www.w3.org/2000/svg">`;

    edges.forEach((edge) => {
        const a = positions[edge.source];
        const b = positions[edge.target];
        if (!a || !b) return;
        const cls = relationClass[edge.relation] || "graph-edge-related";
        svg += `<line class="${cls}" x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" stroke-width="2"></line>`;
    });

    nodes.forEach((node) => {
        const p = positions[node.id];
        const cls = "graph-node" + (node.is_stale ? " stale" : "");
        svg += `<circle class="${cls}" cx="${p.x}" cy="${p.y}" r="14"></circle>`;
        const labelX = p.x;
        const labelY = p.y + (p.y > centerY ? 28 : -20);
        const shortTitle = node.title.length > 22 ? node.title.slice(0, 20) + "…" : node.title;
        svg += `<text class="graph-label" x="${labelX}" y="${labelY}" text-anchor="middle">${escapeXml(shortTitle)}</text>`;
    });

    svg += "</svg>";

    const legend = `
        <div class="d-flex flex-wrap gap-3 mb-2 small">
            <span><span class="d-inline-block" style="width:14px;height:3px;background:#d64545;"></span> Conflict</span>
            <span><span class="d-inline-block" style="width:14px;height:3px;background:#e6a817;"></span> Redundant</span>
            <span><span class="d-inline-block" style="width:14px;height:3px;background:#9aa5b1;"></span> Related</span>
            <span><span class="d-inline-block rounded-circle" style="width:10px;height:10px;background:#d64545;"></span> Stale Document</span>
            <span><span class="d-inline-block rounded-circle" style="width:10px;height:10px;background:#1565c0;"></span> Current Document</span>
        </div>
    `;

    container.innerHTML = legend + svg;
}

function escapeXml(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&apos;");
}
