import { useEffect, useRef, useState } from "react";
import logo from "../../../assets/logo/sv_logo_128.png";
import {
  escapeHtml,
  groupFoundersByLocation,
  locationLabel,
  locationPopup,
  markerColor,
  markerRadius,
  type MapFounder
} from "./mapData";

const apiBase = "http://localhost:8000/api/v1";
declare const L: any; // Leaflet global

export function App() {
  const [founders, setFounders] = useState<MapFounder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const markerLayerRef = useRef<any>(null);

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

    if (markerLayerRef.current) {
      markerLayerRef.current.remove();
    }

    const markerLayer = L.layerGroup().addTo(map);
    markerLayerRef.current = markerLayer;

    groupFoundersByLocation(founders).forEach((location) => {
      const color = markerColor(location.averageScore);
      const marker = L.circleMarker([location.lat, location.lng], {
        radius: markerRadius(location),
        fillColor: color,
        color: "#0a120f",
        weight: 2,
        opacity: 0.9,
        fillOpacity: 0.65
      }).addTo(markerLayer);

      const countLabel = location.founders.length === 1 ? "1 founder" : `${location.founders.length} founders`;
      marker.bindTooltip(`${escapeHtml(locationLabel(location))} - ${countLabel}`);
      marker.bindPopup(locationPopup(location), { maxWidth: 350 });
    });

    return () => {
      markerLayer.remove();
      if (markerLayerRef.current === markerLayer) markerLayerRef.current = null;
    };
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
