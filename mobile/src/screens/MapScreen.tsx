import { Ionicons } from "@expo/vector-icons";
import Mapbox, {
  Camera,
  CircleLayer,
  LineLayer,
  MapView,
  ShapeSource
} from "@rnmapbox/maps";
import Constants from "expo-constants";
import * as Location from "expo-location";
import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  Dimensions,
  Platform,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { StationModal } from "../components/StationModal";
import { Stop } from "../services/api";

const { width, height } = Dimensions.get("window");

// Initialize Mapbox with token from environment
const mapboxToken = Constants.expoConfig?.extra?.mapboxAccessToken;
if (mapboxToken) {
  Mapbox.setAccessToken(mapboxToken);
} else {
  console.warn("Mapbox access token not found. Add MAPBOX_ACCESS_TOKEN to your .env file");
}

// Manhattan center location (Times Square area)
const MANHATTAN_CENTER = {
  latitude: 40.758,
  longitude: -73.9855,
};

// Import local subway lines and stops data
import subwayLinesData from '../assets/subway-lines.json';
import subwayStopsData from '../assets/subway-stops.json';

// Fallback URL - NY State Open Data
// const NYC_SUBWAY_LINES_URL = "https://data.ny.gov/api/geospatial/vtcn-vhd8?method=export&format=GeoJSON";

// Color map based on route symbol (like the CodePen)
const COLOR_MAP: { [key: string]: string } = {
  A: "#0039A6",
  B: "#FF6319",
  G: "#6CBE45",
  J: "#996633",
  L: "#A7A9AC",
  N: "#FCCC0A",
  S: "#808183",
  "1": "#EE352E",
  "4": "#00933C",
  "7": "#B933AD"
};

// Get color from route name (e.g., "A-C-E" -> "A" -> blue)
const getLineColor = (name: string): string => {
  if (!name) return "#999999";
  const firstRoute = name.split("-")[0];
  // Check direct match first
  if (COLOR_MAP[firstRoute]) return COLOR_MAP[firstRoute];
  // Check if it's a number route
  if (["1", "2", "3"].includes(firstRoute)) return COLOR_MAP["1"];
  if (["4", "5", "6"].includes(firstRoute)) return COLOR_MAP["4"];
  if (["7"].includes(firstRoute)) return COLOR_MAP["7"];
  if (["A", "C", "E"].includes(firstRoute)) return COLOR_MAP["A"];
  if (["B", "D", "F", "M"].includes(firstRoute)) return COLOR_MAP["B"];
  if (["N", "Q", "R", "W"].includes(firstRoute)) return COLOR_MAP["N"];
  if (["J", "Z"].includes(firstRoute)) return COLOR_MAP["J"];
  return "#999999";
};

interface TrunkSegment {
  color: string;
  route: string;
  polyline: { latitude: number; longitude: number }[];
}

const MapScreen = () => {
  const [zoomLevel, setZoomLevel] = useState(12);
  const [selectedStation, setSelectedStation] = useState<Stop | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showStationModal, setShowStationModal] = useState(false);
  const [subwayLinesGeoJSON, setSubwayLinesGeoJSON] = useState<any>(null);
  const [subwayStopsGeoJSON, setSubwayStopsGeoJSON] = useState<any>(null);
  // Start with Manhattan center location
  const [userLocation, setUserLocation] = useState<{ latitude: number; longitude: number } | null>({
    latitude: MANHATTAN_CENTER.latitude,
    longitude: MANHATTAN_CENTER.longitude,
  });

  const cameraRef = useRef<Camera>(null);

  // Get user location
  useEffect(() => {
    (async () => {
      try {
        // Check current permission status first
        let { status } = await Location.getForegroundPermissionsAsync();
        
        // If not granted, request permission
        if (status !== 'granted') {
          const { status: newStatus } = await Location.requestForegroundPermissionsAsync();
          status = newStatus;
        }
        
        if (status !== 'granted') {
          console.log('Location permission denied');
          // For testing: use Manhattan center if permission denied
          // Remove this after testing
          setUserLocation({
            latitude: MANHATTAN_CENTER.latitude,
            longitude: MANHATTAN_CENTER.longitude,
          });
          return;
        }

        // Get current location
        const location = await Location.getCurrentPositionAsync({
          accuracy: Location.Accuracy.Balanced,
        });
        
        const coords = {
          latitude: location.coords.latitude,
          longitude: location.coords.longitude,
        };
        
        console.log('User location obtained:', coords);
        // Keep dot in Manhattan - don't update to actual location
        // The blue dot will always show at Manhattan center
      } catch (error) {
        console.error('Error getting location:', error);
      }
    })();
  }, []);

  // Load subway stops from local JSON file
  useEffect(() => {
    function loadSubwayStops() {
      try {
        const stopsData = subwayStopsData as any;
        if (stopsData && stopsData.features) {
          // Group stops by complex_id to avoid duplicates
          const stopsByComplex: { [key: string]: any } = {};
          
          stopsData.features.forEach((feature: any) => {
            const complexId = feature.properties?.complex_id || feature.properties?.station_id || 'unknown';
            if (!stopsByComplex[complexId]) {
              // Use the first stop of each complex as the representative
              // Store gtfs_stop_id for API calls
              stopsByComplex[complexId] = {
                ...feature,
                properties: {
                  ...feature.properties,
                  id: complexId,
                  name: feature.properties?.stop_name || 'Unknown Station',
                  gtfs_stop_id: feature.properties?.gtfs_stop_id || feature.properties?.id || complexId,
                  // Collect all routes for this complex
                  routes: feature.properties?.daytime_routes || ''
                }
              };
            } else {
              // Merge routes if multiple stops in same complex
              const existingRoutes = stopsByComplex[complexId].properties.daytime_routes || '';
              const newRoutes = feature.properties?.daytime_routes || '';
              const allRoutes = new Set([...existingRoutes.split(' '), ...newRoutes.split(' ')].filter(r => r));
              stopsByComplex[complexId].properties.daytime_routes = Array.from(allRoutes).join(' ');
              // Keep the first gtfs_stop_id (or update if this one is better)
              if (!stopsByComplex[complexId].properties.gtfs_stop_id && feature.properties?.gtfs_stop_id) {
                stopsByComplex[complexId].properties.gtfs_stop_id = feature.properties.gtfs_stop_id;
              }
            }
          });

          // Convert to GeoJSON FeatureCollection
          const processedStops = {
            type: "FeatureCollection" as const,
            features: Object.values(stopsByComplex)
          };

          setSubwayStopsGeoJSON(processedStops);
          console.log("Loaded", processedStops.features.length, "stations from subway-stops.json");
        }
      } catch (e) {
        console.error("Error loading subway stops from JSON:", e);
      }
    }
    loadSubwayStops();
  }, []);

  // Load subway lines from local JSON file
  useEffect(() => {
    function loadSubwayLines() {
      try {
        const data = subwayLinesData as any;
        if (data && data.features) {
          // Add color property to each feature based on its service (route letter/number)
          const coloredFeatures = data.features.map((feature: any) => ({
            ...feature,
            properties: {
              ...feature.properties,
              color: getLineColor(feature.properties?.service || feature.properties?.service_name || "")
            }
          }));
          
          setSubwayLinesGeoJSON({
            type: "FeatureCollection",
            features: coloredFeatures
          });
          console.log("Loaded subway lines from local JSON:", coloredFeatures.length, "segments");
        }
      } catch (e) {
        console.error("Error loading subway lines from local JSON:", e);
        // Fallback to backend if local file fails
        try {
          fetch("http://127.0.0.1:5001/api/trunk-shapes")
            .then(response => response.json())
            .then(data => {
              if (data.success && data.data) {
                // Convert backend format to GeoJSON
                const features = data.data.map((segment: TrunkSegment) => ({
                  type: "Feature",
                  properties: { color: segment.color, name: segment.route },
                  geometry: {
                    type: "LineString",
                    coordinates: segment.polyline.map(p => [p.longitude, p.latitude])
                  }
                }));
                setSubwayLinesGeoJSON({ type: "FeatureCollection", features });
              }
            })
            .catch(e2 => {
              console.log("Could not fetch trunk shapes from backend either");
            });
        } catch (e2) {
          console.log("Could not fetch trunk shapes from backend");
        }
      }
    }
    loadSubwayLines();
  }, []);


  // Get unique colors for line layers
  const uniqueColors = useMemo(() => {
    if (!subwayLinesGeoJSON?.features) return [];
    const colors = new Set<string>();
    subwayLinesGeoJSON.features.forEach((f: any) => {
      if (f.properties?.color) colors.add(f.properties.color);
    });
    return Array.from(colors);
  }, [subwayLinesGeoJSON]);

  // Create user location GeoJSON
  const userLocationGeoJSON = useMemo(() => {
    if (!userLocation) {
      console.log('No user location available');
      return null;
    }
    const geoJSON = {
      type: "FeatureCollection" as const,
      features: [
        {
          type: "Feature" as const,
          geometry: {
            type: "Point" as const,
            coordinates: [userLocation.longitude, userLocation.latitude],
          },
          properties: {},
        },
      ],
    };
    console.log('User location GeoJSON created:', geoJSON);
    return geoJSON;
  }, [userLocation]);

  // Process stops GeoJSON to determine transfer stations
  const processedStopsGeoJSON = useMemo(() => {
    if (!subwayStopsGeoJSON) return null;

    const features = subwayStopsGeoJSON.features.map((feature: any) => {
      const routes = feature.properties?.daytime_routes?.split(' ') || [];
      const routeCount = new Set(routes.filter((r: string) => r && r.trim())).size;
      const isTransfer = routeCount >= 3;

      return {
        ...feature,
        properties: {
          ...feature.properties,
          isTransfer,
          routeCount
        }
      };
    });

    return {
      type: "FeatureCollection" as const,
      features
    };
  }, [subwayStopsGeoJSON]);

  const handleLocationPress = () => {
    cameraRef.current?.setCamera({
      centerCoordinate: [MANHATTAN_CENTER.longitude, MANHATTAN_CENTER.latitude],
      zoomLevel: 13,
      animationDuration: 500,
    });
  };

  const handleZoomIn = () => {
    cameraRef.current?.setCamera({
      zoomLevel: zoomLevel + 1,
      animationDuration: 300,
    });
  };

  const handleZoomOut = () => {
    cameraRef.current?.setCamera({
      zoomLevel: zoomLevel - 1,
      animationDuration: 300,
    });
  };

  const handleCloseModal = () => {
    setShowStationModal(false);
    setSelectedStation(null);
  };

  const onRegionChange = (feature: any) => {
    if (feature?.properties?.zoomLevel) {
      setZoomLevel(feature.properties.zoomLevel);
    }
  };

  return (
    <View style={styles.container}>
      <MapView
        style={styles.map}
        styleURL="mapbox://styles/mapbox/light-v11"
        onRegionDidChange={onRegionChange}
        logoEnabled={false}
        attributionEnabled={false}
        compassEnabled={false}
        scaleBarEnabled={false}
      >
        <Camera
          ref={cameraRef}
          defaultSettings={{
            centerCoordinate: [MANHATTAN_CENTER.longitude, MANHATTAN_CENTER.latitude],
            zoomLevel: 12,
          }}
        />

        {/* Subway Lines - render from NYC Open Data GeoJSON */}
        {subwayLinesGeoJSON && subwayLinesGeoJSON.features.length > 0 && (
          <ShapeSource id="subway-lines" shape={subwayLinesGeoJSON}>
            {uniqueColors.map((color) => (
              <LineLayer
                key={`line-${color}`}
                id={`line-${color}`}
                filter={['==', ['get', 'color'], color]}
                style={{
                  lineColor: color,
                  lineWidth: 3,
                  lineCap: 'round',
                  lineJoin: 'round',
                }}
              />
            ))}
          </ShapeSource>
        )}

        {/* Station Markers - from subway-stops.json (only show when zoomed in) */}
        {processedStopsGeoJSON && processedStopsGeoJSON.features.length > 0 && (
          <ShapeSource 
            id="stations" 
            shape={processedStopsGeoJSON}
            onPress={(e) => {
              const feature = e.features?.[0];
              if (feature && feature.geometry.type === 'Point') {
                const props = feature.properties;
              const coords = feature.geometry.coordinates as [number, number];
              const routes = (props?.daytime_routes || '').split(' ').filter((r: string) => r && r.trim());
              
              // Use gtfs_stop_id for API calls, but prefer the first stop in complex
              const stopId = props?.gtfs_stop_id || props?.id || props?.complex_id || props?.station_id || '';
              
              setSelectedStation({
                id: stopId,
                name: props?.name || props?.stop_name || 'Unknown Station',
                latitude: coords[1],
                longitude: coords[0],
                routes: routes.map((routeId: string) => ({
                  id: routeId,
                  short_name: routeId,
                  long_name: `${routeId} Train`,
                  route_color: getLineColor(routeId),
                  text_color: '#FFFFFF'
                }))
              });
              setShowStationModal(true);
              }
            }}
          >
            {/* All stations - uniform small size, only visible when zoomed in (zoom >= 13) */}
            <CircleLayer
              id="stations-all"
              minZoomLevel={13}
              style={{
                circleRadius: 2,
                circleColor: '#FFFFFF',
                circleStrokeColor: '#1a1a1a',
                circleStrokeWidth: 0.8,
              }}
            />
          </ShapeSource>
        )}
        
        {/* User location - blue circle dot (rendered last so it's on top) */}
        {userLocationGeoJSON && (
          <ShapeSource id="user-location" shape={userLocationGeoJSON}>
            {/* Outer blue circle - pulsing effect */}
            <CircleLayer
              id="user-location-outer"
              style={{
                circleRadius: 12,
                circleColor: '#007AFF',
                circleOpacity: 0.25,
                circleStrokeWidth: 0,
              }}
            />
            {/* Middle blue circle */}
            <CircleLayer
              id="user-location-middle"
              style={{
                circleRadius: 8,
                circleColor: '#007AFF',
                circleOpacity: 0.5,
                circleStrokeWidth: 0,
              }}
            />
            {/* Inner blue circle - solid center */}
            <CircleLayer
              id="user-location-inner"
              style={{
                circleRadius: 6,
                circleColor: '#007AFF',
                circleStrokeColor: '#FFFFFF',
                circleStrokeWidth: 2,
              }}
            />
          </ShapeSource>
        )}
      </MapView>

      {/* Floating Controls */}
      <View style={styles.controlsContainer}>
        <TouchableOpacity
          style={styles.controlButton}
          onPress={handleLocationPress}
          activeOpacity={0.8}
        >
          <Ionicons name="locate" size={22} color="#1a1a1a" />
        </TouchableOpacity>
        
        <View style={styles.zoomControls}>
          <TouchableOpacity
            style={[styles.controlButton, styles.zoomButton]}
            onPress={handleZoomIn}
            activeOpacity={0.8}
          >
            <Ionicons name="add" size={22} color="#1a1a1a" />
          </TouchableOpacity>
          <View style={styles.zoomDivider} />
          <TouchableOpacity
            style={[styles.controlButton, styles.zoomButton]}
            onPress={handleZoomOut}
            activeOpacity={0.8}
          >
            <Ionicons name="remove" size={22} color="#1a1a1a" />
          </TouchableOpacity>
        </View>
      </View>

      {/* Loading Indicator */}
      {isLoading && (
        <View style={styles.loadingContainer}>
          <View style={styles.loadingPill}>
            <Text style={styles.loadingText}>Loading...</Text>
          </View>
        </View>
      )}

      {/* Station Count Badge */}
      {!isLoading && processedStopsGeoJSON && processedStopsGeoJSON.features.length > 0 && (
        <View style={styles.stationBadge}>
          <Text style={styles.stationBadgeText}>{processedStopsGeoJSON.features.length} stations</Text>
        </View>
      )}

      <StationModal
        visible={showStationModal}
        onClose={handleCloseModal}
        station={selectedStation}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#f5f5f5",
  },
  map: {
    flex: 1,
  },

  // Controls
  controlsContainer: {
    position: "absolute",
    right: 16,
    top: Platform.OS === "ios" ? 60 : 40,
    gap: 12,
  },
  controlButton: {
    width: 48,
    height: 48,
    backgroundColor: "#FFFFFF",
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 4,
  },
  zoomControls: {
    backgroundColor: "#FFFFFF",
    borderRadius: 14,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 4,
    overflow: "hidden",
  },
  zoomButton: {
    borderRadius: 0,
    shadowOpacity: 0,
    elevation: 0,
  },
  zoomDivider: {
    height: 1,
    backgroundColor: "rgba(0, 0, 0, 0.08)",
    marginHorizontal: 8,
  },

  // Loading
  loadingContainer: {
    position: "absolute",
    top: Platform.OS === "ios" ? 60 : 40,
    left: 0,
    right: 0,
    alignItems: "center",
  },
  loadingPill: {
    backgroundColor: "rgba(26, 26, 26, 0.9)",
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 20,
  },
  loadingText: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "500",
    letterSpacing: 0.3,
  },

  // Station Badge
  stationBadge: {
    position: "absolute",
    bottom: 110,
    left: 16,
    backgroundColor: "rgba(255, 255, 255, 0.95)",
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 12,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 6,
    elevation: 3,
  },
  stationBadgeText: {
    fontSize: 13,
    fontWeight: "600",
    color: "#3a3a3a",
    letterSpacing: 0.2,
  },
});

export default MapScreen;