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
import { Ionicons } from "@expo/vector-icons";
import { apiService, Route, Stop } from "../services/api";
import { StationModal } from "./StationModal";
import RouteSymbol from "./RouteSymbol";

interface TrainStopsModalProps {
  visible: boolean;
  route: Route | null;
  onClose: () => void;
}

export const TrainStopsModal: React.FC<TrainStopsModalProps> = ({
  visible,
  route,
  onClose,
}) => {
  const [stops, setStops] = useState<Stop[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastRouteId, setLastRouteId] = useState<string | null>(null);

  // Add functionality to show realtime arrival data for a stop
  const [selectedStop, setSelectedStop] = useState<Stop | null>(null);
  const [showStationModal, setShowStationModal] = useState(false);

  const handleStopPress = async (stop: Stop) => {
    try {
      // Use parent_station if available, otherwise use stop.id
      const stopId = stop.parent_station || stop.id;
      const completeStop: Stop = {
        ...stop,
        id: stopId,
        routes: route ? [route] : []
      };
      setSelectedStop(completeStop);
      setShowStationModal(true);
      console.log("TrainStopsModal: handleStopPress -> completeStop: ", completeStop);
    } catch (error) {
      console.error("Error setting up stop:", error);
      setSelectedStop(stop);
      setShowStationModal(true);
    }
  };

  const fetchStops = async (isRefresh = false) => {
    if (!route) return;

    // Don't fetch if we already have data for this route and it's not a refresh
    if (!isRefresh && lastRouteId === route.id && stops.length > 0) {
      return;
    }

    try {
      setLoading(!isRefresh);
      setError(null);

      const response = await apiService.getRouteStations(route.id);

      if (response.success && response.data) {
        setStops(response.data);
        setLastRouteId(route.id);
      } else {
        setError(response.error || "Failed to fetch stops");
      }
    } catch (err) {
      setError("Network error. Please try again.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (visible && route) {
      fetchStops();
    }
  }, [visible, route]);

  const onRefresh = () => {
    setRefreshing(true);
    fetchStops(true);
  };

  if (!route) return null;

  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={onClose}
    >
      <View style={styles.container}>
        {/* Header */}
        <View style={styles.header}>
          <View style={styles.routeHeader}>
            <RouteSymbol routeId={route.short_name} size={40} />
            <View style={styles.routeInfo}>
              <Text style={styles.routeName}>{route.short_name} Train</Text>
              <Text style={styles.routeDescription}>{route.long_name}</Text>
            </View>
          </View>
          <TouchableOpacity onPress={onClose} style={styles.closeButton}>
            <Text style={styles.closeButtonText}>✕</Text>
          </TouchableOpacity>
        </View>

        {/* Stops Section */}
        <View style={styles.stopsSection}>
          <View style={styles.stopsHeader}>
            <Text style={styles.stopsTitle}>All Stops</Text>
            <TouchableOpacity onPress={onRefresh} style={styles.refreshButton}>
              <Text style={styles.refreshButtonText}>↻</Text>
            </TouchableOpacity>
          </View>

          {loading && !refreshing && (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color="#007AFF" />
              <Text style={styles.loadingText}>Loading stops...</Text>
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

          {!loading && !error && stops.length === 0 && (
            <View style={styles.noStopsContainer}>
              <Ionicons name="train-outline" size={48} color="#B0BEC5" />
              <Text style={styles.noStopsText}>
                No stops found for this route
              </Text>
            </View>
          )}

          {!loading && !error && stops.length > 0 && (
            <ScrollView
              style={styles.stopsList}
              refreshControl={
                <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
              }
            >
              {stops.map((stop) => (
                <View key={stop.id} style={styles.stopItem}>
                  <View style={styles.stopCircle}>
                    <Ionicons name="location" size={16} color="#FFFFFF" />
                  </View>
                  <View style={styles.stopInfo}>
                    {/* CREATE THE NEW ONPRESS SCREEN */}
                    <TouchableOpacity onPress={() => handleStopPress(stop)}>
                        <Text style={styles.stopName}>{stop.name}</Text>
                    </TouchableOpacity>
                  </View>
                </View>
              ))}
            </ScrollView>
          )}
        </View>

        <StationModal
          visible={showStationModal}
          station={selectedStop}
          onClose={() => setShowStationModal(false)}
        />
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F8F9FA",
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    padding: 20,
    paddingTop: 60,
    backgroundColor: "#FFFFFF",
    borderBottomWidth: 1,
    borderBottomColor: "#E1E5E9",
  },
  routeHeader: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    marginRight: 10,
  },
  routeInfo: {
    marginLeft: 12,
    flex: 1,
  },
  routeName: {
    fontSize: 24,
    fontWeight: "bold",
    color: "#1A1A1A",
  },
  routeDescription: {
    fontSize: 14,
    color: "#666666",
    marginTop: 2,
  },
  closeButton: {
    width: 30,
    height: 30,
    borderRadius: 15,
    backgroundColor: "#F0F0F0",
    justifyContent: "center",
    alignItems: "center",
  },
  closeButtonText: {
    fontSize: 18,
    color: "#666666",
  },
  stopsSection: {
    flex: 1,
    backgroundColor: "#FFFFFF",
  },
  stopsHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: "#E1E5E9",
  },
  stopsTitle: {
    fontSize: 20,
    fontWeight: "bold",
    color: "#1A1A1A",
  },
  refreshButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: "#007AFF",
    justifyContent: "center",
    alignItems: "center",
  },
  refreshButtonText: {
    fontSize: 18,
    color: "#FFFFFF",
  },
  loadingContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 40,
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: "#666666",
  },
  errorContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 40,
  },
  errorText: {
    fontSize: 16,
    color: "#FF4444",
    textAlign: "center",
    marginBottom: 20,
  },
  retryButton: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    backgroundColor: "#007AFF",
    borderRadius: 8,
  },
  retryButtonText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "600",
  },
  noStopsContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 40,
  },
  noStopsText: {
    fontSize: 16,
    color: "#666666",
    textAlign: "center",
    marginTop: 16,
  },
  stopsList: {
    flex: 1,
  },
  stopItem: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: "#E1E5E9",
    backgroundColor: "#FFFFFF",
  },
  stopCircle: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: "#007AFF",
    justifyContent: "center",
    alignItems: "center",
    marginRight: 16,
  },
  stopInfo: {
    flex: 1,
  },
  stopName: {
    fontSize: 16,
    fontWeight: "600",
    color: "#1A1A1A",
  },
});
