import { useEffect, useRef, useState } from "react";
import { 
  fetchPersonProfile, 
  fetchPersonScores, 
  fetchPersonNetwork, 
  type DetailedPerson, 
  type HistoricalScore 
} from "../lib/people";

interface NetworkNode {
  id: string;
  label: string;
  type: "founder" | "university" | "project" | "hackathon" | "person";
  x: number;
  y: number;
  vx: number;
  vy: number;
}

interface NetworkLink {
  source: string;
  target: string;
  relationship?: string;
}

export function PersonProfileModal({ 
  userId, 
  onClose 
}: { 
  userId: string | null; 
  onClose: () => void; 
}) {
  const [profile, setProfile] = useState<DetailedPerson | null>(null);
  const [scores, setScores] = useState<HistoricalScore[]>([]);
  const [nodes, setNodes] = useState<NetworkNode[]>([]);
  const [links, setLinks] = useState<NetworkLink[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const graphContainerRef = useRef<HTMLDivElement>(null);
  const simulationRef = useRef<number | null>(null);
  const dragNodeRef = useRef<string | null>(null);

  const graphWidth = 720;
  const graphHeight = 320;

  // 1. Fetch all data on userId change
  useEffect(() => {
    if (!userId) return;

    setLoading(true);
    setError(null);
    setProfile(null);
    setScores([]);
    setNodes([]);
    setLinks([]);

    const controller = new AbortController();

    Promise.all([
      fetchPersonProfile(userId, controller.signal),
      fetchPersonScores(userId, controller.signal),
      fetchPersonNetwork(userId, controller.signal)
    ])
      .then(([profileData, scoresData, networkData]) => {
        setProfile(profileData);
        setScores(scoresData);

        // Initialize personal graph nodes with random positions near center
        const initializedNodes = (networkData.nodes || []).map((node: any) => ({
          id: node.id,
          label: node.label || node.id,
          type: node.type || "person",
          x: graphWidth / 2 + (Math.random() - 0.5) * 120,
          y: graphHeight / 2 + (Math.random() - 0.5) * 120,
          vx: 0,
          vy: 0,
        }));

        setNodes(initializedNodes);
        setLinks(networkData.links || []);
        setLoading(false);
      })
      .catch((err) => {
        if ((err as DOMException).name !== "AbortError") {
          setError(err instanceof Error ? err.message : "Failed to load founder profile.");
          setLoading(false);
        }
      });

    return () => {
      controller.abort();
    };
  }, [userId]);

  // 2. Personal Network Graph physics simulation
  useEffect(() => {
    if (nodes.length === 0 || loading) return;

    const repulsionStrength = 300;
    const attractionStrength = 0.05;
    const desiredLength = 110;
    const gravity = 0.01;
    const damping = 0.85;

    const runSimulation = () => {
      setNodes((currentNodes) => {
        const nextNodes = currentNodes.map((n) => ({ ...n }));

        // Repulsion
        for (let i = 0; i < nextNodes.length; i++) {
          for (let j = i + 1; j < nextNodes.length; j++) {
            const dx = nextNodes[j].x - nextNodes[i].x;
            const dy = nextNodes[j].y - nextNodes[i].y;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            if (dist < 250) {
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

        // Attraction
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

          const cx = graphWidth / 2;
          const cy = graphHeight / 2;
          node.vx += (cx - node.x) * gravity;
          node.vy += (cy - node.y) * gravity;

          node.x += node.vx;
          node.y += node.vy;

          node.vx *= damping;
          node.vy *= damping;

          node.x = Math.max(20, Math.min(graphWidth - 20, node.x));
          node.y = Math.max(20, Math.min(graphHeight - 20, node.y));
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

  if (!userId) return null;

  // Drag handlers for graph nodes
  const handleMouseDown = (nodeId: string) => (event: React.MouseEvent) => {
    event.preventDefault();
    dragNodeRef.current = nodeId;
  };

  const handleMouseMove = (event: React.MouseEvent) => {
    if (!dragNodeRef.current || !graphContainerRef.current) return;
    const rect = graphContainerRef.current.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * graphWidth;
    const y = ((event.clientY - rect.top) / rect.height) * graphHeight;

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

  const getNodeColor = (type: NetworkNode["type"]) => {
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

  // Helper for FounderScore color coding
  const getScoreColor = (score: number) => {
    if (score < 40) return "#ff8585";
    if (score < 60) return "#ffad72";
    if (score < 70) return "#f4cf72";
    if (score < 85) return "#72d6b4";
    return "#83dcea";
  };

  // Helper for FounderScore label
  const getScoreLabel = (score: number) => {
    if (score < 40) return "Critical";
    if (score < 60) return "Caution";
    if (score < 70) return "Mixed";
    if (score < 85) return "Strong";
    return "Exceptional";
  };

  // Native SVG Line Chart Math
  const chartWidth = 440;
  const chartHeight = 160;
  const chartPaddingLeft = 40;
  const chartPaddingRight = 20;
  const chartPaddingTop = 20;
  const chartPaddingBottom = 30;

  const pointsCount = scores.length;
  const plotWidth = chartWidth - chartPaddingLeft - chartPaddingRight;
  const plotHeight = chartHeight - chartPaddingTop - chartPaddingBottom;

  const chartPoints = scores.map((pt, idx) => {
    const x = chartPaddingLeft + (pointsCount > 1 ? (idx / (pointsCount - 1)) * plotWidth : plotWidth / 2);
    // Score maps 0 to 100
    const y = chartHeight - chartPaddingBottom - (pt.score / 100) * plotHeight;
    return { x, y, timestamp: pt.timestamp, score: pt.score };
  });

  const pathD = chartPoints.length > 0 
    ? `M ${chartPoints.map((p) => `${p.x} ${p.y}`).join(" L ")}` 
    : "";

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="modal-close" onClick={onClose} aria-label="Close Profile">
          &times;
        </button>

        {loading && (
          <div style={{ padding: "4rem", textAlign: "center" }}>
            <p style={{ color: "var(--sv-muted)" }}>Loading founder profile...</p>
          </div>
        )}

        {error && (
          <div style={{ padding: "4rem", textAlign: "center" }}>
            <p className="error-text">{error}</p>
            <button className="retry-button" onClick={onClose}>Close</button>
          </div>
        )}

        {!loading && !error && profile && (
          <div className="profile-layout">
            {/* Sidebar Biography */}
            <aside className="profile-sidebar">
              <div className="profile-avatar-container">
                <div className="profile-avatar">
                  {profile.avatarUrl ? (
                    <img src={profile.avatarUrl} alt={profile.name} />
                  ) : (
                    <span>{profile.firstName?.[0] || profile.name[0]}</span>
                  )}
                </div>
              </div>

              <h2>{profile.name}</h2>
              <p className="profile-tagline">{profile.tagline || "Founder & Entrepreneur"}</p>

              <hr style={{ border: "none", borderTop: "1px solid var(--sv-line)", margin: "1rem 0" }} />

              <dl className="profile-bio-list">
                {profile.professionalSituation && (
                  <>
                    <dt>Situation</dt>
                    <dd>{profile.professionalSituation}</dd>
                  </>
                )}
                {profile.university && (
                  <>
                    <dt>University</dt>
                    <dd>
                      {profile.university}
                      {profile.academicDegree ? ` (${profile.academicDegree})` : ""}
                      {profile.graduationYear ? ` · Class of ${profile.graduationYear}` : ""}
                    </dd>
                  </>
                )}
                {profile.fieldOfStudy && (
                  <>
                    <dt>Field of Study</dt>
                    <dd>{profile.fieldOfStudy}</dd>
                  </>
                )}
                {(profile.city || profile.country) && (
                  <>
                    <dt>Location</dt>
                    <dd>{[profile.city, profile.country].filter(Boolean).join(", ")}</dd>
                  </>
                )}
                {profile.nationality && (
                  <>
                    <dt>Nationality</dt>
                    <dd>{profile.nationality}</dd>
                  </>
                )}
                {profile.passionHobby && (
                  <>
                    <dt>Interests</dt>
                    <dd>{profile.passionHobby}</dd>
                  </>
                )}
              </dl>

              {/* Links */}
              <div className="profile-links">
                {profile.linkedinUrl && (
                  <a href={profile.linkedinUrl} target="_blank" rel="noopener noreferrer" className="profile-link-btn linkedin">
                    LinkedIn
                  </a>
                )}
                {profile.githubUrl && (
                  <a href={profile.githubUrl} target="_blank" rel="noopener noreferrer" className="profile-link-btn github">
                    GitHub
                  </a>
                )}
              </div>
            </aside>

            {/* Main Content Pane */}
            <main className="profile-main">
              {/* Top Banner Row */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem", marginBottom: "1.5rem" }}>
                <div>
                  <span className="eyebrow">Verified Member</span>
                  <h1 style={{ margin: 0, fontSize: "1.8rem" }}>Founder Profile</h1>
                </div>

                {/* Score Summary Badge */}
                {profile.activeFounderScore !== null && (
                  <div className="founder-score-card">
                    <span style={{ color: "var(--sv-muted)", fontSize: "0.74rem", fontWeight: "bold", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                      Active Founder Score
                    </span>
                    <div style={{ display: "flex", alignItems: "baseline", gap: "0.5rem", marginTop: "0.2rem" }}>
                      <strong style={{ fontSize: "2rem", color: getScoreColor(profile.activeFounderScore) }}>
                        {profile.activeFounderScore.toFixed(1)}
                      </strong>
                      <span 
                        style={{ 
                          fontSize: "0.78rem", 
                          fontWeight: "bold", 
                          background: `${getScoreColor(profile.activeFounderScore)}20`, 
                          color: getScoreColor(profile.activeFounderScore), 
                          padding: "0.15rem 0.4rem", 
                          borderRadius: "4px" 
                        }}
                      >
                        {getScoreLabel(profile.activeFounderScore)}
                      </span>
                    </div>
                  </div>
                )}
              </div>

              {/* Score History Graph & Projects Grid */}
              <div className="profile-grid">
                {/* Score Chart */}
                <section className="profile-card" style={{ gridColumn: chartPoints.length > 0 ? "span 7" : "span 12" }}>
                  <h4 style={{ margin: "0 0 1rem 0", color: "var(--sv-green-deep)", textTransform: "uppercase", fontSize: "0.8rem", letterSpacing: "0.08em" }}>
                    Founder Score Timeline
                  </h4>
                  {chartPoints.length > 0 ? (
                    <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} width="100%" height="auto" style={{ display: "block", overflow: "visible" }}>
                      {/* Grid Lines */}
                      {[0, 25, 50, 75, 100].map((gridVal) => {
                        const y = chartHeight - chartPaddingBottom - (gridVal / 100) * plotHeight;
                        return (
                          <g key={gridVal}>
                            <line 
                              x1={chartPaddingLeft} 
                              y1={y} 
                              x2={chartWidth - chartPaddingRight} 
                              y2={y} 
                              stroke="var(--sv-line)" 
                              strokeDasharray="4 4" 
                            />
                            <text 
                              x={chartPaddingLeft - 8} 
                              y={y + 4} 
                              fill="var(--sv-muted)" 
                              fontSize="9" 
                              textAnchor="end"
                              style={{ fontVariantNumeric: "tabular-nums" }}
                            >
                              {gridVal}
                            </text>
                          </g>
                        );
                      })}

                      {/* Line Path */}
                      <path 
                        d={pathD} 
                        fill="none" 
                        stroke="var(--sv-green)" 
                        strokeWidth="2.5" 
                        strokeLinecap="round" 
                        strokeLinejoin="round" 
                        style={{ filter: "drop-shadow(0 2px 4px rgba(114, 214, 180, 0.25))" }}
                      />

                      {/* Tooltip circles */}
                      {chartPoints.map((pt, idx) => (
                        <g key={idx}>
                          <circle 
                            cx={pt.x} 
                            cy={pt.y} 
                            r="4.5" 
                            fill="#09110f" 
                            stroke="var(--sv-green)" 
                            strokeWidth="2.5" 
                          />
                          <title>{`Date: ${new Date(pt.timestamp).toLocaleDateString(undefined, { year: "numeric", month: "short" })}\nScore: ${pt.score}`}</title>
                          {/* Label for Date at bottom */}
                          <text
                            x={pt.x}
                            y={chartHeight - 8}
                            fill="var(--sv-muted)"
                            fontSize="8"
                            textAnchor="middle"
                          >
                            {new Date(pt.timestamp).toLocaleDateString(undefined, { month: "short", year: "2-digit" })}
                          </text>
                        </g>
                      ))}
                    </svg>
                  ) : (
                    <p style={{ color: "var(--sv-muted)", fontStyle: "italic", margin: 0 }}>No score history available.</p>
                  )}
                </section>

                {/* Projects */}
                <section className="profile-card" style={{ gridColumn: chartPoints.length > 0 ? "span 5" : "span 12" }}>
                  <h4 style={{ margin: "0 0 1rem 0", color: "var(--sv-green-deep)", textTransform: "uppercase", fontSize: "0.8rem", letterSpacing: "0.08em" }}>
                    Contributions
                  </h4>
                  <ul className="profile-projects-list" style={{ margin: 0, padding: 0, listStyle: "none" }}>
                    {profile.projects.map((proj) => (
                      <li key={`${proj.id}-${proj.relationship}`} style={{ marginBottom: "0.6rem" }}>
                        <strong style={{ display: "block", fontSize: "0.9rem", color: "var(--sv-ink)" }}>
                          {proj.title || "Untitled Project"}
                        </strong>
                        <span style={{ color: "var(--sv-muted)", fontSize: "0.76rem" }}>
                          {proj.relationship} {proj.completed ? "· Completed" : ""}
                        </span>
                      </li>
                    ))}
                    {profile.projects.length === 0 && (
                      <p style={{ color: "var(--sv-muted)", fontStyle: "italic", margin: 0 }}>No projects linked.</p>
                    )}
                  </ul>
                </section>
              </div>

              {/* Personal Network Graph */}
              <section className="profile-card" style={{ marginTop: "1rem" }}>
                <h4 style={{ margin: "0 0 0.5rem 0", color: "var(--sv-green-deep)", textTransform: "uppercase", fontSize: "0.8rem", letterSpacing: "0.08em" }}>
                  Personal Connection Network
                </h4>
                <p style={{ color: "var(--sv-muted)", fontSize: "0.8rem", margin: "0 0 1rem 0" }}>
                  Explore connection nodes directly linked to this founder via shared universities, projects, and hackathons.
                </p>

                {nodes.length > 0 ? (
                  <div 
                    ref={graphContainerRef}
                    onMouseMove={handleMouseMove}
                    onMouseUp={handleMouseUp}
                    onMouseLeave={handleMouseUp}
                    style={{ background: "rgba(10, 18, 16, 0.4)", border: "1px solid var(--sv-line)", borderRadius: "10px", overflow: "hidden" }}
                  >
                    <svg viewBox={`0 0 ${graphWidth} ${graphHeight}`} width="100%" height="auto" style={{ display: "block" }}>
                      {/* Links */}
                      {links.map((link, idx) => {
                        const sNode = nodes.find((n) => n.id === link.source);
                        const tNode = nodes.find((n) => n.id === link.target);
                        if (!sNode || !tNode) return null;
                        return (
                          <line 
                            key={`${link.source}-${link.target}-${idx}`}
                            x1={sNode.x}
                            y1={sNode.y}
                            x2={tNode.x}
                            y2={tNode.y}
                            stroke="rgba(114, 214, 180, 0.16)"
                            strokeWidth="1.5"
                          />
                        );
                      })}

                      {/* Nodes */}
                      {nodes.map((node) => (
                        <g key={node.id} style={{ cursor: "grab" }}>
                          <circle 
                            cx={node.x}
                            cy={node.y}
                            r={node.id === userId ? 11 : (node.type === "founder" ? 9 : 7)}
                            fill={getNodeColor(node.type)}
                            stroke="rgba(9, 17, 15, 0.9)"
                            strokeWidth="2"
                            onMouseDown={handleMouseDown(node.id)}
                            style={{
                              filter: node.id === userId ? "drop-shadow(0 0 5px rgba(114, 214, 180, 0.7))" : "none"
                            }}
                          />
                          <text 
                            x={node.x}
                            y={node.y - 12}
                            textAnchor="middle"
                            fill="var(--sv-ink)"
                            fontSize="9"
                            fontWeight={node.id === userId ? "bold" : "normal"}
                            style={{ pointerEvents: "none", textShadow: "0 1px 3px rgba(0,0,0,0.8)" }}
                          >
                            {node.label}
                          </text>
                        </g>
                      ))}
                    </svg>
                  </div>
                ) : (
                  <p style={{ color: "var(--sv-muted)", fontStyle: "italic", margin: 0 }}>No personal network connections.</p>
                )}
              </section>
            </main>
          </div>
        )}
      </div>
    </div>
  );
}
