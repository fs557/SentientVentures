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

export function FounderProjectsCard({ evaluation }: { evaluation: CompanyEvaluation }) {
  const [founders, setFounders] = useState<Person[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const home = evaluation.categories.home;
  const foundersText = home?.items.find((item) => item.id === "home.founders")?.assessment ?? "";

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
          .then((results) => {
            // Find an exact or very close case-insensitive match
            const lowerFullName = fullName.toLowerCase();
            return results.filter(
              (p) =>
                p.name.toLowerCase().includes(lowerFullName) ||
                lowerFullName.includes(p.name.toLowerCase())
            );
          })
          .catch((err) => {
            if ((err as DOMException).name !== "AbortError") {
              throw err;
            }
            return [];
          })
      )
    )
      .then((resultsArray) => {
        const flattened = resultsArray.flat();
        // Remove duplicates by ID
        const unique = flattened.reduce<Person[]>((acc, current) => {
          if (!acc.some((item) => item.id === current.id)) {
            acc.push(current);
          }
          return acc;
        }, []);
        setFounders(unique);
        setLoading(false);
      })
      .catch((err) => {
        setError("Could not search founders directory.");
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
              {person.name}
            </h4>
            <dl className="summary-grid dl" style={{ gridTemplateColumns: "1fr", gap: "0.4rem", marginBottom: "0.75rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--sv-muted)", fontSize: "0.82rem" }}>University</span>
                <strong style={{ fontSize: "0.82rem", color: "var(--sv-ink)" }}>{person.university || "Not specified"}</strong>
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
