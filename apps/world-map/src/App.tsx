import { useEffect, useRef, useState } from "react";
import logo from "../../../assets/logo/sv_logo_128.png";

interface MapFounder {
  id: string;
  name: string;
  city: string;
  country: string;
  lat: number;
  lng: number;
  score: number;
}

const apiBase = "http://localhost:8000/api/v1";
declare const L: any; // Leaflet global

export function App() {
  const [founders, setFounders] = useState<MapFounder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);

  // Fetch map data on load
  useEffect(() => {
    fetch(`${apiBase}/people/map-data`, { headers: { Accept: "application/json" } })
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load map data.");
        return res.json();
      })
      .then((data: MapFounder[]) => {
        setFounders(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Map data offline");
        setLoading(false);
      });
  }, []);

  // Initialize Map
  useEffect(() => {
    if (loading || error || !mapContainerRef.current) return;

    // Center map around Europe/World
    const map = L.map(mapContainerRef.current).setView([25, 10], 2.5);
    mapInstanceRef.current = map;

    // Load CartoDB Dark Matter tiles (beautiful, sleek, premium dark theme map!)
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
      subdomains: "abcd",
      maxZoom: 20
    }).addTo(map);

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [loading, error]);

  // Add markers
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || founders.length === 0) return;

    founders.forEach((f) => {
      // CircleMarker radius is proportional to score (minimum radius 6)
      const radius = Math.max(6, f.score * 0.22);
      
      // Determine color based on score
      let color = "#ffc477"; // gold
      if (f.score < 40) color = "#ff8585";
      else if (f.score < 60) color = "#ffad72";
      else if (f.score >= 85) color = "#83dcea";
      else if (f.score >= 70) color = "#72d6b4";

      const marker = L.circleMarker([f.lat, f.lng], {
        radius,
        fillColor: color,
        color: "#0a120f",
        weight: 2,
        opacity: 0.9,
        fillOpacity: 0.65
      }).addTo(map);

      // Create a popup linking back to VC Dashboard
      const popupContent = `
        <div style="font-family: system-ui, sans-serif; padding: 0.25rem 0; min-width: 140px;">
          <h3 style="margin: 0 0 0.25rem 0; font-size: 1rem; color: #72d6b4;">${f.name}</h3>
          <p style="margin: 0 0 0.4rem 0; font-size: 0.8rem; color: #a8b8b1;">${f.city}, ${f.country}</p>
          <div style="font-size: 0.8rem; font-weight: bold; margin-bottom: 0.5rem;">
            Score: <span style="color: ${color};">${f.score.toFixed(1)}</span>
          </div>
          <a href="http://localhost:8081/?founder=${f.id}" target="_blank" class="map-popup-btn">
            View Profile
          </a>
        </div>
      `;
      marker.bindPopup(popupContent);
    });
  }, [founders]);

  return (
    <div className="app-shell sv-app-shell" style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <header className="navbar sv-navbar">
        <a href="/" className="brand sv-brand" aria-label="Sentient Ventures dashboard home">
          <img src={logo} alt="Sentient Ventures" />
          <span>Sentient<br />Ventures</span>
        </a>
        <p>Founder geographical distribution map</p>
      </header>

      <div style={{ flex: 1, position: "relative" }}>
        {loading && (
          <div style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            background: "var(--sv-bg)",
            zIndex: 10
          }}>
            <p style={{ color: "var(--sv-muted)" }}>Loading geographical founder map...</p>
          </div>
        )}
        {error && (
          <div style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            background: "var(--sv-bg)",
            zIndex: 10
          }}>
            <p style={{ color: "#ff8585" }}>Error: {error}</p>
          </div>
        )}
        <div ref={mapContainerRef} style={{ width: "100%", height: "100%" }} />
      </div>
    </div>
  );
}
