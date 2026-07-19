import { useEffect, useRef, useState } from "react";
import type { CompanyEvaluation } from "@sv/contracts/generated";

interface Node {
  id: string;
  label: string;
  type: "founder" | "university" | "project" | "hackathon" | "person";
  x: number;
  y: number;
  vx: number;
  vy: number;
}

interface Link {
  source: string;
  target: string;
  relationship: string;
}

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export function FounderNetworkGraph({ 
  evaluation, 
  onSelectPerson 
}: { 
  evaluation: CompanyEvaluation; 
  onSelectPerson?: (id: string) => void; 
}) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [links, setLinks] = useState<Link[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const simulationRef = useRef<number | null>(null);
  const dragNodeRef = useRef<string | null>(null);

  const width = 800;
  const height = 500;

  // 1. Fetch graph data on load
  useEffect(() => {
    setLoading(true);
    setError(null);
    const controller = new AbortController();

    fetch(`${apiBase}/people/network?company_slug=${encodeURIComponent(evaluation.slug)}`, {
      signal: controller.signal,
      headers: { Accept: "application/json" }
    })
      .then((res) => {
        if (!res.ok) throw new Error("Could not load network graph.");
        return res.json();
      })
      .then((data) => {
        // Initialize nodes with random positions near center
        const initializedNodes = (data.nodes || []).map((node: any) => ({
          id: node.id,
          label: node.label || node.id,
          type: node.type || "person",
          x: width / 2 + (Math.random() - 0.5) * 150,
          y: height / 2 + (Math.random() - 0.5) * 150,
          vx: 0,
          vy: 0,
        }));
        setNodes(initializedNodes);
        setLinks(data.links || data.edges || []);
        setLoading(false);
      })
      .catch((err) => {
        if ((err as DOMException).name !== "AbortError") {
          setError("Network graph is currently offline.");
          setLoading(false);
        }
      });

    return () => {
      controller.abort();
    };
  }, [evaluation.slug]);

  // 2. Physics simulation
  useEffect(() => {
    if (nodes.length === 0 || loading) return;

    // Simulation constants
    const repulsionStrength = 800;
    const attractionStrength = 0.04;
    const desiredLength = 180;
    const gravity = 0.004;
    const damping = 0.85;

    const runSimulation = () => {
      setNodes((currentNodes) => {
        const nextNodes = currentNodes.map((n) => ({ ...n }));

        // Repulsion between all nodes
        for (let i = 0; i < nextNodes.length; i++) {
          for (let j = i + 1; j < nextNodes.length; j++) {
            const dx = nextNodes[j].x - nextNodes[i].x;
            const dy = nextNodes[j].y - nextNodes[i].y;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            if (dist < 400) {
              const force = repulsionStrength / (dist * dist);
              const fx = (dx / dist) * force;
              const fy = (dy / dist) * force;
              nextNodes[i].vx -= fx;
              nextNodes[i].vy -= fy;
              nextNodes[j].vx += fx;
              nextNodes[j].vy += fy;
            }
          }
        }

        // Attraction along links
        links.forEach((link) => {
          const sourceNode = nextNodes.find((n) => n.id === link.source);
          const targetNode = nextNodes.find((n) => n.id === link.target);
          if (sourceNode && targetNode) {
            const dx = targetNode.x - sourceNode.x;
            const dy = targetNode.y - sourceNode.y;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            const force = (dist - desiredLength) * attractionStrength;
            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;

            if (sourceNode.id !== dragNodeRef.current) {
              sourceNode.vx += fx;
              sourceNode.vy += fy;
            }
            if (targetNode.id !== dragNodeRef.current) {
              targetNode.vx -= fx;
              targetNode.vy -= fy;
            }
          }
        });

        // Update positions, apply center gravity
        nextNodes.forEach((node) => {
          if (node.id === dragNodeRef.current) return;

          const cx = width / 2;
          const cy = height / 2;
          node.vx += (cx - node.x) * gravity;
          node.vy += (cy - node.y) * gravity;

          node.x += node.vx;
          node.y += node.vy;

          node.vx *= damping;
          node.vy *= damping;

          // Boundary constraints
          node.x = Math.max(30, Math.min(width - 30, node.x));
          node.y = Math.max(30, Math.min(height - 30, node.y));
        });

        return nextNodes;
      });

      simulationRef.current = requestAnimationFrame(runSimulation);
    };

    simulationRef.current = requestAnimationFrame(runSimulation);

    return () => {
      if (simulationRef.current) cancelAnimationFrame(simulationRef.current);
    };
  }, [nodes.length, links, loading]);

  // 3. Node dragging handlers
  const handleMouseDown = (nodeId: string) => (event: React.MouseEvent) => {
    event.preventDefault();
    dragNodeRef.current = nodeId;
  };

  const handleMouseMove = (event: React.MouseEvent) => {
    if (!dragNodeRef.current || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * width;
    const y = ((event.clientY - rect.top) / rect.height) * height;

    setNodes((currentNodes) =>
      currentNodes.map((n) => {
        if (n.id === dragNodeRef.current) {
          return { ...n, x, y, vx: 0, vy: 0 };
        }
        return n;
      })
    );
  };

  const handleMouseUp = () => {
    dragNodeRef.current = null;
  };

  const getNodeColor = (type: Node["type"]) => {
    switch (type) {
      case "founder":
        return "#72d6b4"; // Glowing Mint
      case "university":
        return "#83dcea"; // Cyan
      case "project":
        return "#ffc477"; // Gold
      case "hackathon":
        return "#ffad72"; // Orange
      default:
        return "#a8b8b1"; // Silver
    }
  };

  return (
    <details className="evaluation-card evaluation-card--criterion" open style={{ marginBottom: "1.5rem" }}>
      <summary className="evaluation-card__summary">
        <header>
          <p className="eyebrow">Connection Map</p>
          <h3 id="founder-network-title">Founder Network Graph</h3>
        </header>
        <span className="evaluation-card__indicator" aria-hidden="true" />
      </summary>
      <div className="evaluation-card__content" style={{ paddingTop: "1rem" }}>
        <p style={{ color: "var(--sv-muted)", fontSize: "0.86rem", margin: "0 0 1.25rem 0" }}>
          Visualizing direct 1-hop connections of the founding team via university alumni networks, project collaborations, and hackathons. Click a founder node to view their full profile.
        </p>

        {loading && <p>Generating network graph...</p>}
        {error && <p className="error-text">{error}</p>}

        {!loading && !error && (
          <div style={{ display: "grid", gap: "1rem", gridTemplateColumns: "1fr" }}>
            {/* SVG canvas */}
            <div 
              ref={containerRef}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              style={{ background: "rgba(10, 18, 16, 0.5)", border: "1px solid var(--sv-line)", borderRadius: "10px", overflow: "hidden" }}
            >
              <svg viewBox={`0 0 ${width} ${height}`} width="100%" height="auto" style={{ display: "block" }}>
                {/* Lines (Links) */}
                {links.map((link, idx) => {
                  const sourceNode = nodes.find((n) => n.id === link.source);
                  const targetNode = nodes.find((n) => n.id === link.target);
                  if (!sourceNode || !targetNode) return null;
                  return (
                    <line
                      key={`${link.source}-${link.target}-${idx}`}
                      x1={sourceNode.x}
                      y1={sourceNode.y}
                      x2={targetNode.x}
                      y2={targetNode.y}
                      stroke="rgba(114, 214, 180, 0.18)"
                      strokeWidth="1.5"
                    />
                  );
                })}

                {/* Circles (Nodes) */}
                {nodes.map((node) => (
                  <g 
                    key={node.id} 
                    style={{ cursor: (node.type === "founder" || node.type === "person") ? "pointer" : "grab" }}
                    onClick={() => {
                      if (node.type === "founder" || node.type === "person") {
                        onSelectPerson?.(node.id);
                      }
                    }}
                  >
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r={node.type === "founder" ? 10 : 8}
                    fill={getNodeColor(node.type)}
                    stroke="rgba(9, 17, 15, 0.9)"
                    strokeWidth="2"
                    onMouseDown={handleMouseDown(node.id)}
                    style={{
                      filter: node.type === "founder" ? "drop-shadow(0 0 4px rgba(114, 214, 180, 0.6))" : "none",
                    }}
                  />
                  <text
                    x={node.x}
                    y={node.y - 12}
                    textAnchor="middle"
                    fill="var(--sv-ink)"
                    fontSize="10"
                    fontWeight={node.type === "founder" ? "bold" : "normal"}
                    style={{
                      pointerEvents: "none",
                      textShadow: "0 1px 3px rgba(0,0,0,0.8)",
                    }}
                  >
                    {node.label}
                  </text>
                </g>
              ))}
            </svg>
          </div>

          {/* Legend */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem", fontSize: "0.78rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
              <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: "#72d6b4" }} />
              <span style={{ color: "var(--sv-ink)" }}>Founder</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
              <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: "#83dcea" }} />
              <span style={{ color: "var(--sv-ink)" }}>University</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
              <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: "#ffc477" }} />
              <span style={{ color: "var(--sv-ink)" }}>Project</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
              <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: "#ffad72" }} />
              <span style={{ color: "var(--sv-ink)" }}>Hackathon</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
              <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: "#a8b8b1" }} />
              <span style={{ color: "var(--sv-ink)" }}>Alumni/Teammate</span>
            </div>
          </div>
        </div>
      )}
    </div>
  </details>
  );
}
