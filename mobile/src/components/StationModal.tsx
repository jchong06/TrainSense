import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Modal,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { apiService, Arrival, Route, Stop } from "../services/api";
import RouteSymbol from "./RouteSymbol";

interface StationModalProps {
  visible: boolean;
  station: Stop | null;
  onClose: () => void;
}

interface ArrivalGroup {
  route: Route;
  direction: string;
  arrivals: Arrival[];
}

const MTA_ROUTE_ORDER = [
  "1",
  "2",
  "3",
  "4",
  "5",
  "6",
  "7",
  "A",
  "C",
  "E",
  "B",
  "D",
  "F",
  "M",
  "N",
  "Q",
  "R",
  "W",
  "L",
  "G",
  "J",
  "Z",
  "S",
];

function sortRoutes(routes: Route[]) {
  return [...routes].sort((a, b) => {
    const aName = a.short_name || a.id;
    const bName = b.short_name || b.id;
    const aIdx = MTA_ROUTE_ORDER.indexOf(aName);
    const bIdx = MTA_ROUTE_ORDER.indexOf(bName);
    if (aIdx === -1 && bIdx === -1) return aName.localeCompare(bName);
    if (aIdx === -1) return 1;
    if (bIdx === -1) return -1;
    return aIdx - bIdx;
  });
}

export const StationModal: React.FC<StationModalProps> = ({
  visible,
  station,
  onClose,
}) => {
  const [arrivals, setArrivals] = useState<Arrival[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastStationId, setLastStationId] = useState<string | null>(null);

  const fetchArrivals = async (isRefresh = false) => {
    if (!station) return;

    // Don't fetch if we already have data for this station and it's not a refresh
    if (!isRefresh && lastStationId === station.id && arrivals.length > 0) {
      return;
    }

    try {
      setLoading(!isRefresh);
      setError(null);

      const response = await apiService.getRealtimeUpdates(station.id);

      if (response.success && response.data) {
        setArrivals(response.data.arrivals || []);
        setLastStationId(station.id);
      } else {
        setError(response.error || "Failed to fetch arrivals");
      }
    } catch (err) {
      setError("Network error. Please try again.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (visible && station) {
      fetchArrivals();
    }
  }, [visible, station]);

  const onRefresh = () => {
    setRefreshing(true);
    fetchArrivals(true);
  };

  const groupArrivalsByRoute = (arrivals: Arrival[]): ArrivalGroup[] => {
    const groups: { [key: string]: ArrivalGroup } = {};

    // Deduplicate arrivals first
    const uniqueArrivals = arrivals.filter(
      (arrival, index, self) =>
        index ===
        self.findIndex(
          (a) =>
            a.route === arrival.route &&
            a.direction === arrival.direction &&
            a.minutes === arrival.minutes
        )
    );

    uniqueArrivals.forEach((arrival) => {
      const routeId = arrival.route;
      const direction = arrival.direction;
      const groupKey = `${routeId}-${direction}`;
      
      if (!groups[groupKey]) {
        // Find the actual route data from station routes
        const actualRoute = station?.routes?.find((r) => r.id === routeId);
        groups[groupKey] = {
          route: actualRoute || {
            id: routeId,
            short_name: routeId,
            long_name: `${routeId} Train`,
            route_color: "000000",
            text_color: "FFFFFF",
          },
          direction: direction,
          arrivals: [],
        };
      }
      groups[groupKey].arrivals.push(arrival);
    });

    return Object.values(groups).sort((a, b) => {
      // First sort by route name
      const routeComparison = a.route.short_name.localeCompare(b.route.short_name);
      if (routeComparison !== 0) return routeComparison;
      // Then sort by direction (Northbound first, then Southbound, etc.)
      return a.direction.localeCompare(b.direction);
    });
  };

  const formatArrivalTime = (minutes: number): string => {
    if (minutes <= 0) return "Due";
    if (minutes === 1) return "1 min";
    return `${minutes} min`;
  };

  const getStatusColor = (status: string): string => {
    // Minimal black/white scheme - use grays
    switch (status.toLowerCase()) {
      case "arriving":
        return "#1a1a1a";
      case "approaching":
        return "#3a3a3a";
      case "on time":
        return "#1a1a1a";
      default:
        return "#666666";
    }
  };

  const getStatusBgColor = (status: string): string => {
    // Light gray backgrounds for minimal look
    switch (status.toLowerCase()) {
      case "arriving":
        return "#E5E5E5";
      case "approaching":
        return "#E5E5E5";
      case "on time":
        return "#E5E5E5";
      default:
        return "#E5E5E5";
    }
  };

  const arrivalGroups = groupArrivalsByRoute(arrivals);

  if (!station) return null;

  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={onClose}
    >
      <View style={styles.container}>
        <ScrollView
          style={styles.scrollView}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
          }
        >
          {/* Header Card - Minimalistic */}
          <View style={styles.headerCard}>
            <View style={styles.headerTop}>
              <View style={styles.stationHeader}>
                <Text style={styles.stationName}>{station.name}</Text>
                {station.routes && sortRoutes(station.routes).length > 0 && (
                  <View style={styles.routeSymbols}>
                    {sortRoutes(station.routes).map((route) => (
                      <RouteSymbol
                        key={route.id}
                        routeId={route.short_name}
                        size={24}
                      />
                    ))}
                  </View>
                )}
              </View>
              <TouchableOpacity onPress={onClose} style={styles.closeButton}>
                <Text style={styles.closeButtonText}>✕</Text>
              </TouchableOpacity>
            </View>
          </View>

          {/* Arrivals Section - Minimalistic Card Style */}
          <View style={styles.arrivalsCard}>
            <View style={styles.arrivalsHeader}>
              <Text style={styles.arrivalsTitle}>Real-Time Arrivals</Text>
              <TouchableOpacity onPress={onRefresh} style={styles.refreshButton}>
                <Text style={styles.refreshButtonText}>↻</Text>
              </TouchableOpacity>
            </View>

            {loading && !refreshing && (
              <View style={styles.loadingContainer}>
                <ActivityIndicator size="large" color="#1a1a1a" />
                <Text style={styles.loadingText}>Loading arrivals...</Text>
              </View>
            )}

            {error && (
              <View style={styles.errorContainer}>
                <Text style={styles.errorText}>{error}</Text>
                <TouchableOpacity onPress={onRefresh} style={styles.retryButton}>
                  <Text style={styles.retryButtonText}>Retry</Text>
                </TouchableOpacity>
              </View>
            )}

            {!loading && !error && arrivalGroups.length === 0 && (
              <View style={styles.noArrivalsContainer}>
                <Text style={styles.noArrivalsText}>
                  No arrivals scheduled at this time
                </Text>
              </View>
            )}

            {!loading && !error && arrivalGroups.length > 0 && (
              <View style={styles.arrivalsList}>
                {arrivalGroups.map((group) => (
                  <View key={`${group.route.id}-${group.direction}`} style={styles.routeGroup}>
                    <View style={styles.routeHeader}>
                      <RouteSymbol routeId={group.route.short_name} size={22} />
                      <Text style={styles.directionHeader}>{group.direction}</Text>
                    </View>

                    <View style={styles.arrivalsContainer}>
                      {group.arrivals
                        .sort((a, b) => a.minutes - b.minutes)
                        .slice(0, 4)
                        .map((arrival, index) => (
                          <View key={index} style={styles.arrivalItem}>
                            <Text style={styles.arrivalMinutes}>
                              {formatArrivalTime(arrival.minutes)}
                            </Text>
                            <View style={[styles.statusBadge, { backgroundColor: getStatusBgColor(arrival.status) }]}>
                              <Text style={[styles.arrivalStatus, { color: getStatusColor(arrival.status) }]}>
                                {arrival.status}
                              </Text>
                            </View>
                          </View>
                        ))}
                    </View>
                  </View>
                ))}
              </View>
            )}
          </View>
        </ScrollView>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#f5f5f5",
  },
  scrollView: {
    flex: 1,
  },
  headerCard: {
    marginHorizontal: 18,
    marginTop: 20,
    marginBottom: 12,
    backgroundColor: "#FFFFFF",
    borderRadius: 14,
    padding: 18,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 4,
  },
  headerTop: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
  },
  stationHeader: {
    flex: 1,
    marginRight: 12,
  },
  stationName: {
    fontSize: 22,
    fontWeight: "bold",
    color: "#1a1a1a",
    marginBottom: 10,
    letterSpacing: 0.2,
  },
  routeSymbols: {
    flexDirection: "row",
    alignItems: "center",
    flexWrap: "wrap",
    gap: 6,
  },
  closeButton: {
    width: 30,
    height: 30,
    borderRadius: 15,
    backgroundColor: "#F5F5F5",
    justifyContent: "center",
    alignItems: "center",
  },
  closeButtonText: {
    fontSize: 16,
    color: "#1a1a1a",
    fontWeight: "600",
  },
  arrivalsCard: {
    marginHorizontal: 18,
    marginBottom: 20,
    backgroundColor: "#FFFFFF",
    borderRadius: 14,
    padding: 18,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 4,
  },
  arrivalsHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 14,
  },
  arrivalsTitle: {
    fontSize: 18,
    fontWeight: "bold",
    color: "#1a1a1a",
    letterSpacing: 0.3,
  },
  refreshButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: "#1a1a1a",
    justifyContent: "center",
    alignItems: "center",
  },
  refreshButtonText: {
    fontSize: 14,
    color: "#FFFFFF",
    fontWeight: "600",
  },
  loadingContainer: {
    justifyContent: "center",
    alignItems: "center",
    padding: 40,
  },
  loadingText: {
    marginTop: 16,
    fontSize: 15,
    color: "#666666",
    fontWeight: "500",
  },
  errorContainer: {
    justifyContent: "center",
    alignItems: "center",
    padding: 40,
  },
  errorText: {
    fontSize: 15,
    color: "#1a1a1a",
    textAlign: "center",
    marginBottom: 20,
    fontWeight: "500",
  },
  retryButton: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    backgroundColor: "#1a1a1a",
    borderRadius: 10,
  },
  retryButtonText: {
    color: "#FFFFFF",
    fontSize: 15,
    fontWeight: "600",
  },
  noArrivalsContainer: {
    justifyContent: "center",
    alignItems: "center",
    padding: 40,
  },
  noArrivalsText: {
    fontSize: 15,
    color: "#666666",
    textAlign: "center",
    fontWeight: "500",
  },
  arrivalsList: {
    gap: 14,
  },
  routeGroup: {
    marginBottom: 14,
  },
  routeHeader: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 8,
  },
  directionHeader: {
    fontSize: 15,
    fontWeight: "600",
    color: "#1a1a1a",
    marginLeft: 8,
  },
  arrivalsContainer: {
    backgroundColor: "#F5F5F5",
    borderRadius: 10,
    padding: 10,
  },
  arrivalItem: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: "rgba(0, 0, 0, 0.08)",
  },
  arrivalMinutes: {
    fontSize: 16,
    fontWeight: "bold",
    color: "#1a1a1a",
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    backgroundColor: "#E5E5E5",
  },
  arrivalStatus: {
    fontSize: 11,
    fontWeight: "600",
    color: "#666666",
  },
});
