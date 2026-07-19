import { useEffect, useState } from "react";
import type { CompanyEvaluation } from "@sv/contracts/generated";
import { searchPeople, type Person } from "../lib/people";
import { displayText } from "../lib/format";

function extractNames(text: string): string[] {
  if (!text) return [];
  // Clean up common introductory phrases
  let clean = text.replace(/the founding team is/gi, "");
  clean = clean.replace(/the founders are/gi, "");
  clean = clean.replace(/founders are/gi, "");
  clean = clean.replace(/founder is/gi, "");
  clean = clean.replace(/co-founders/gi, "");
  clean = clean.replace(/co-founder/gi, "");
  clean = clean.replace(/founding team/gi, "");

  // Split by "and", "or", "&", or comma
  const parts = clean.split(/\band\b|\b&\b|,|\bor\b/i);
  return parts
    .map((p) => p.trim().replace(/[.,\/#!$%\^&\*;:{}=\-_`~()]/g, ""))
    .filter((p) => p.length >= 2);
}

export function FounderProjectsCard({ 
  evaluation, 
  onSelectPerson 
}: { 
  evaluation: CompanyEvaluation; 
  onSelectPerson?: (id: string) => void; 
}) {
  const [founders, setFounders] = useState<Person[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const home = evaluation.categories.home;
  const foundersText = home?.items.find((item) => item.id === "home.founders")?.assessment ?? "";

  const mgmtCategory = evaluation.categories.management;
  const academicItem = mgmtCategory?.items.find((item) => item.id === "management.academic_background");
  const academicText = [
    academicItem?.assessment,
    ...(academicItem?.positiveArguments || [])
  ].filter(Boolean).join(" ").toLowerCase();

  useEffect(() => {
    const names = extractNames(foundersText);
    if (names.length === 0) {
      setFounders([]);
      return;
    }

    const controller = new AbortController();
    setLoading(true);
    setError(null);

    // Query each name against the people search API
    Promise.all(
      names.map((fullName) =>
        searchPeople(fullName, controller.signal)
          .then((results) => {
            if (results.length > 0) return results;
            // If no results, try searching for the first token (first name)
            const firstToken = fullName.split(/\s+/)[0];
            if (firstToken && firstToken.length >= 2) {
              return searchPeople(firstToken, controller.signal);
            }
            return [];
          })
          .catch((err) => {
            if ((err as DOMException).name !== "AbortError") {
              console.error(`Search failed for ${fullName}:`, err);
            }
            return [];
          })
      )
    )
      .then((resultsArray) => {
        const found = resultsArray.flat().filter(
          (person, idx, self) => self.findIndex((p) => p.id === person.id) === idx
        );
        setFounders(found);
        setLoading(false);
      })
      .catch((err) => {
        setError("Failed to query people directory.");
        setLoading(false);
      });

    return () => {
      controller.abort();
    };
  }, [foundersText]);

  return (
    <details className="evaluation-card evaluation-card--criterion" open style={{ marginBottom: "1.5rem" }}>
      <summary className="evaluation-card__summary">
        <header>
          <p className="eyebrow">Database Integration</p>
          <h3 id="founder-projects-title">Which projects have they done?</h3>
        </header>
        <span className="evaluation-card__indicator" aria-hidden="true" />
      </summary>
      <div className="evaluation-card__content" style={{ paddingTop: "1rem" }}>
        {loading && <p>Searching database for founder profiles...</p>}
        {error && <p className="error-text" role="alert">{error}</p>}
        {!loading && !error && founders.length === 0 && (
          <p style={{ color: "var(--sv-muted)", fontStyle: "italic" }}>
            No matching profiles found in the database for the founder(s) "{displayText(foundersText)}".
          </p>
        )}
        {!loading && !error && founders.map((person) => (
          <div key={person.id} className="founder-db-profile" style={{ marginBottom: "1.5rem", borderBottom: "1px solid var(--sv-line)", paddingBottom: "1.25rem" }}>
            <h4 style={{ margin: "0 0 0.5rem 0", fontSize: "1.1rem", textTransform: "none", color: "var(--sv-ink)", letterSpacing: "normal" }}>
              <button 
                type="button" 
                className="clickable-founder-link" 
                onClick={() => onSelectPerson?.(person.id)}
              >
                {person.name}
              </button>
            </h4>
            {(() => {
              const uni = person.university || "";
              // Check if university matches (is mentioned in) the academic background text
              const isConsistent = !!(uni && uni.toLowerCase() !== "not specified" && academicText.includes(uni.toLowerCase()));

              return (
                <dl className="summary-grid dl" style={{ gridTemplateColumns: "1fr", gap: "0.4rem", marginBottom: "0.75rem" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ color: "var(--sv-muted)", fontSize: "0.82rem" }}>University</span>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <strong style={{ fontSize: "0.82rem", color: "var(--sv-ink)" }}>{person.university || "Not specified"}</strong>
                      {person.university && (
                        <button
                          type="button"
                          disabled={isConsistent}
                          onClick={() => alert(`Verification email inquiry prepared for ${person.name} (${person.university})`)}
                          style={{
                            background: isConsistent ? "rgba(255, 255, 255, 0.05)" : "#ffad72",
                            color: isConsistent ? "var(--sv-muted)" : "#071c15",
                            border: "1px solid " + (isConsistent ? "rgba(255, 255, 255, 0.1)" : "#ff9e59"),
                            padding: "0.25rem 0.6rem",
                            borderRadius: "6px",
                            fontSize: "0.72rem",
                            fontWeight: "bold",
                            cursor: isConsistent ? "not-allowed" : "pointer",
                            transition: "all 0.2s ease",
                            boxShadow: isConsistent ? "none" : "0 2px 8px rgba(255, 173, 114, 0.22)"
                          }}
                          title={isConsistent ? "University verified against evaluation data." : "University mismatch or not found in evaluation data! Click to send inquiry email."}
                        >
                          {isConsistent ? "Verified" : "Send Inquiry"}
                        </button>
                      )}
                    </div>
                  </div>
                  {person.fieldOfStudy && (
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <span style={{ color: "var(--sv-muted)", fontSize: "0.82rem" }}>Field of Study</span>
                      <strong style={{ fontSize: "0.82rem", color: "var(--sv-ink)" }}>{person.fieldOfStudy}</strong>
                    </div>
                  )}
                  {person.city && (
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <span style={{ color: "var(--sv-muted)", fontSize: "0.82rem" }}>Location</span>
                      <strong style={{ fontSize: "0.82rem", color: "var(--sv-ink)" }}>
                        {person.city}
                        {person.country ? `, ${person.country}` : ""}
                      </strong>
                    </div>
                  )}
                </dl>
              );
            })()}
            <h5 style={{ margin: "0.75rem 0 0.4rem 0", fontSize: "0.85rem", color: "var(--sv-green-deep)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Projects
            </h5>
            {(() => {
              const groupedProjects: { [id: string]: { title: string | null; relationships: string[]; completed: boolean } } = {};
              person.projects.forEach((proj) => {
                if (!groupedProjects[proj.id]) {
                  groupedProjects[proj.id] = {
                    title: proj.title,
                    relationships: [proj.relationship],
                    completed: proj.completed,
                  };
                } else {
                  if (!groupedProjects[proj.id].relationships.includes(proj.relationship)) {
                    groupedProjects[proj.id].relationships.push(proj.relationship);
                  }
                  if (proj.completed) {
                    groupedProjects[proj.id].completed = true;
                  }
                }
              });

              const projectList = Object.entries(groupedProjects);

              return (
                <ul style={{ margin: 0, paddingLeft: "1.15rem" }}>
                  {projectList.map(([id, info]) => (
                    <li key={id} style={{ marginBottom: "0.3rem" }}>
                      <strong>{info.title || "Untitled Project"}</strong>
                      <span style={{ color: "var(--sv-muted)", marginLeft: "0.5rem", fontSize: "0.78rem" }}>
                        ({info.relationships.join(", ")}
                        {info.completed ? " · Completed" : ""})
                      </span>
                    </li>
                  ))}
                  {projectList.length === 0 && (
                    <li style={{ color: "var(--sv-muted)", fontStyle: "italic", listStyleType: "none", paddingLeft: 0 }}>
                      No linked projects found.
                    </li>
                  )}
                </ul>
              );
            })()}
          </div>
        ))}
      </div>
    </details>
  );
}
