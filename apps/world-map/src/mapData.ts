export interface MapFounder {
  id: string;
  name: string;
  city: string;
  country: string;
  lat: number;
  lng: number;
  score: number;
}

export interface FounderLocation {
  key: string;
  lat: number;
  lng: number;
  city: string;
  country: string;
  founders: MapFounder[];
  averageScore: number;
}

function finiteScore(score: number): number {
  return Number.isFinite(score) ? score : 0;
}

export function groupFoundersByLocation(founders: MapFounder[]): FounderLocation[] {
  const locations = new Map<string, FounderLocation>();

  founders.forEach((founder) => {
    if (!Number.isFinite(founder.lat) || !Number.isFinite(founder.lng)) return;

    // Coordinates come from the API's city centroid table. Using them as the
    // key keeps people at the same centroid on a single discoverable marker.
    const key = `${founder.lat}|${founder.lng}`;
    const existing = locations.get(key);

    if (existing) {
      existing.founders.push(founder);
      existing.averageScore =
        existing.founders.reduce((total, person) => total + finiteScore(person.score), 0) /
        existing.founders.length;
      return;
    }

    locations.set(key, {
      key,
      lat: founder.lat,
      lng: founder.lng,
      city: founder.city,
      country: founder.country,
      founders: [founder],
      averageScore: finiteScore(founder.score)
    });
  });

  return Array.from(locations.values()).map((location) => ({
    ...location,
    founders: [...location.founders].sort(
      (left, right) => finiteScore(right.score) - finiteScore(left.score)
    )
  }));
}

export function markerColor(score: number): string {
  if (score < 40) return "#ff8585";
  if (score < 60) return "#ffad72";
  if (score >= 85) return "#83dcea";
  if (score >= 70) return "#72d6b4";
  return "#ffc477";
}

export function markerRadius(location: FounderLocation): number {
  const scoreContribution = Math.max(0, Math.min(100, location.averageScore)) * 0.08;
  const peopleContribution = Math.sqrt(location.founders.length) * 2.5;
  return Math.max(7, Math.min(24, 5 + scoreContribution + peopleContribution));
}

export function escapeHtml(value: unknown): string {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

export function locationLabel(location: FounderLocation): string {
  return [location.city, location.country].filter(Boolean).join(", ") || "Unknown location";
}

export function locationPopup(location: FounderLocation): string {
  const color = markerColor(location.averageScore);
  const peopleLabel = location.founders.length === 1 ? "1 founder" : `${location.founders.length} founders`;
  const founderRows = location.founders
    .map((founder) => {
      const score = finiteScore(founder.score);
      const profileUrl = `http://localhost:8081/?founder=${encodeURIComponent(String(founder.id))}`;

      return `
        <li style="display: flex; gap: 0.75rem; align-items: center; justify-content: space-between; padding: 0.5rem 0; border-top: 1px solid rgba(114, 214, 180, 0.15);">
          <div style="min-width: 0;">
            <div style="font-size: 0.84rem; font-weight: 700; color: #e2f0ec; overflow-wrap: anywhere;">${escapeHtml(founder.name)}</div>
            <div style="font-size: 0.74rem; color: #a8b8b1;">Score <span style="color: ${markerColor(score)}; font-weight: 700;">${score.toFixed(1)}</span></div>
          </div>
          <a href="${escapeHtml(profileUrl)}" target="_blank" rel="noopener noreferrer" class="map-popup-btn" style="flex: 0 0 auto; margin-top: 0;">View</a>
        </li>`;
    })
    .join("");

  return `
    <div style="font-family: system-ui, sans-serif; padding: 0.2rem 0; min-width: 230px; max-width: 320px;">
      <h3 style="margin: 0; font-size: 1rem; color: #72d6b4; overflow-wrap: anywhere;">${escapeHtml(locationLabel(location))}</h3>
      <p style="margin: 0.2rem 0 0.45rem; font-size: 0.76rem; color: #a8b8b1;">${peopleLabel} - Average score <span style="color: ${color}; font-weight: 700;">${location.averageScore.toFixed(1)}</span></p>
      <ul style="list-style: none; margin: 0; padding: 0; max-height: 260px; overflow-y: auto;">${founderRows}</ul>
    </div>`;
}
