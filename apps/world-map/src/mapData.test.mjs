import assert from "node:assert/strict";
import test from "node:test";
import { escapeHtml, groupFoundersByLocation, locationPopup } from "./mapData.ts";

test("groups founders at the same coordinates and sorts them by score", () => {
  const locations = groupFoundersByLocation([
    { id: "1", name: "First", city: "Berlin", country: "Germany", lat: 52.52, lng: 13.405, score: 40 },
    { id: "2", name: "Second", city: "Berlin", country: "Germany", lat: 52.52, lng: 13.405, score: 80 },
    { id: "3", name: "Invalid", city: "Nowhere", country: "", lat: Number.NaN, lng: 0, score: 90 }
  ]);

  assert.equal(locations.length, 1);
  assert.equal(locations[0].founders.length, 2);
  assert.equal(locations[0].averageScore, 60);
  assert.deepEqual(locations[0].founders.map(({ id }) => id), ["2", "1"]);
});

test("escapes popup values and safely encodes profile identifiers", () => {
  assert.equal(escapeHtml(`<script>alert("x")</script>`), "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;");

  const [location] = groupFoundersByLocation([
    {
      id: `person&mode=admin`,
      name: `<img src=x onerror=alert(1)>`,
      city: `<Berlin>`,
      country: `Germany & Austria`,
      lat: 52.52,
      lng: 13.405,
      score: 75
    }
  ]);
  const popup = locationPopup(location);

  assert.doesNotMatch(popup, /<img src=x/);
  assert.match(popup, /&lt;Berlin&gt;, Germany &amp; Austria/);
  assert.match(popup, /founder=person%26mode%3Dadmin/);
});
