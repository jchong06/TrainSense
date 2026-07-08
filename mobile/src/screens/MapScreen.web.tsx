// Web-only Map screen.
//
// @rnmapbox/maps only exports MapView + Camera on web (no ShapeSource / LineLayer /
// CircleLayer), so the native MapScreen (which uses those) crashes on web. Metro resolves
// this ".web.tsx" file in place of MapScreen.tsx for web, and here we drive mapbox-gl
// directly to render the basemap, subway lines, stations, and the user dot.
import { Ionicons } from "@expo/vector-icons";
import Constants from "expo-constants";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import React, { useEffect, useRef, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { StationModal } from "../components/StationModal";
import { Stop } from "../services/api";
import subwayLinesData from "../assets/subway-lines.json";
import subwayStopsData from "../assets/subway-stops.json";

const mapboxToken = Constants.expoConfig?.extra?.mapboxAccessToken;
const hasValidMapboxToken =
  !!mapboxToken && mapboxToken.startsWith("pk.") && !mapboxToken.includes("placeholder");

const MANHATTAN = { lng: -73.9855, lat: 40.758 };

// Color per route symbol (matches the native MapScreen).
const COLOR_MAP: { [key: string]: string } = {
  A: "#0039A6", B: "#FF6319", G: "#6CBE45", J: "#996633", N: "#FCCC0A",
  S: "#808183", "1": "#EE352E", "4": "#00933C", "7": "#B933AD",
};

const getLineColor = (name: string): string => {
  if (!name) return "#999999";
  const r = name.split("-")[0].trim();
  if (COLOR_MAP[r]) return COLOR_MAP[r];
  if (["1", "2", "3"].includes(r)) return COLOR_MAP["1"];
  if (["4", "5", "6"].includes(r)) return COLOR_MAP["4"];
  if (["7"].includes(r)) return COLOR_MAP["7"];
  if (["A", "C", "E"].includes(r)) return COLOR_MAP["A"];
  if (["B", "D", "F", "M"].includes(r)) return COLOR_MAP["B"];
  if (["N", "Q", "R", "W"].includes(r)) return COLOR_MAP["N"];
  if (["J", "Z"].includes(r)) return COLOR_MAP["J"];
  return "#999999";
};

export default function MapScreenWeb() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<any>(null);
  const [selectedStation, setSelectedStation] = useState<Stop | null>(null);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    if (!hasValidMapboxToken || !containerRef.current || mapRef.current) return;

    mapboxgl.accessToken = mapboxToken;
    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: "mapbox://styles/mapbox/light-v11",
      center: [MANHATTAN.lng, MANHATTAN.lat],
      zoom: 12,
      attributionControl: false,
    });
    mapRef.current = map;
    map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), "top-right");

    map.on("load", () => {
      // Subway lines, colored by service.
      const lineFeatures = (subwayLinesData as any).features.map((f: any) => ({
        ...f,
        properties: {
          ...f.properties,
          color: getLineColor(f.properties?.service || f.properties?.service_name || ""),
        },
      }));
      map.addSource("subway-lines", {
        type: "geojson",
        data: { type: "FeatureCollection", features: lineFeatures },
      });
      map.addLayer({
        id: "subway-lines",
        type: "line",
        source: "subway-lines",
        paint: { "line-color": ["get", "color"], "line-width": 3 },
        layout: { "line-cap": "round", "line-join": "round" },
      });

      // Stations.
      map.addSource("stations", { type: "geojson", data: subwayStopsData as any });
      map.addLayer({
        id: "stations",
        type: "circle",
        source: "stations",
        minzoom: 11,
        paint: {
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 11, 2.5, 15, 5],
          "circle-color": "#ffffff",
          "circle-stroke-color": "#1a1a1a",
          "circle-stroke-width": 1.2,
        },
      });

      // User location dot (kept at Manhattan center, matching the native screen).
      map.addSource("user", {
        type: "geojson",
        data: {
          type: "FeatureCollection",
          features: [
            {
              type: "Feature",
              geometry: { type: "Point", coordinates: [MANHATTAN.lng, MANHATTAN.lat] },
              properties: {},
            },
          ],
        },
      });
      map.addLayer({
        id: "user-outer",
        type: "circle",
        source: "user",
        paint: { "circle-radius": 12, "circle-color": "#007AFF", "circle-opacity": 0.25 },
      });
      map.addLayer({
        id: "user-inner",
        type: "circle",
        source: "user",
        paint: {
          "circle-radius": 6,
          "circle-color": "#007AFF",
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 2,
        },
      });

      // Open the station modal on click.
      map.on("click", "stations", (e: any) => {
        const feature = e.features?.[0];
        if (!feature) return;
        const p = feature.properties || {};
        const coords = feature.geometry.coordinates as [number, number];
        const routes = (p.daytime_routes || "")
          .split(" ")
          .filter((r: string) => r && r.trim());
        setSelectedStation({
          id: p.gtfs_stop_id || p.complex_id || p.station_id || "",
          name: p.stop_name || "Unknown Station",
          latitude: coords[1],
          longitude: coords[0],
          routes: routes.map((r: string) => ({
            id: r,
            short_name: r,
            long_name: `${r} Train`,
            route_color: getLineColor(r),
            text_color: "#FFFFFF",
          })),
        });
        setShowModal(true);
      });
      map.on("mouseenter", "stations", () => {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", "stations", () => {
        map.getCanvas().style.cursor = "";
      });
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  if (!hasValidMapboxToken) {
    return (
      <View style={[styles.container, styles.fallback]}>
        <Ionicons name="map-outline" size={64} color="#c4c4c4" />
        <Text style={styles.fallbackTitle}>Map unavailable</Text>
        <Text style={styles.fallbackText}>
          Add a Mapbox access token to mobile/.env as MAPBOX_ACCESS_TOKEN and restart to
          enable the map.
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Raw DOM node for mapbox-gl; fills the relatively-positioned RN View. */}
      <div ref={containerRef} style={{ position: "absolute", inset: 0 }} />
      <StationModal
        visible={showModal}
        onClose={() => {
          setShowModal(false);
          setSelectedStation(null);
        }}
        station={selectedStation}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#eaeaea" },
  fallback: { alignItems: "center", justifyContent: "center", padding: 32 },
  fallbackTitle: { fontSize: 20, fontWeight: "700", color: "#1a1a1a", marginTop: 16 },
  fallbackText: {
    fontSize: 14,
    lineHeight: 20,
    color: "#6a6a6a",
    textAlign: "center",
    marginTop: 8,
    maxWidth: 300,
  },
});
