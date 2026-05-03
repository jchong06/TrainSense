import { Ionicons } from "@expo/vector-icons";
import React, { useEffect, useState } from "react";
import {
  Alert,
  Keyboard,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import RouteSymbol from "../components/RouteSymbol";
import { apiService, Stop, TripOption, TripPlan, TripLeg } from "../services/api";

const SearchScreen = () => {
  const [fromLocation, setFromLocation] = useState("");
  const [toLocation, setToLocation] = useState("");
  const [stops, setStops] = useState<Stop[]>([]);
  const [filteredStops, setFilteredStops] = useState<Stop[]>([]);
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [activeInput, setActiveInput] = useState<"from" | "to" | null>(null);
  const [tripResult, setTripResult] = useState<TripPlan | null>(null);
  const [selectedFromStop, setSelectedFromStop] = useState<Stop | null>(null);
  const [selectedToStop, setSelectedToStop] = useState<Stop | null>(null);

  useEffect(() => {
    loadStops();
  }, []);

  const loadStops = async () => {
    setLoading(true);
    try {
      const response = await apiService.getStops();
      if (response.success && response.data) {
        setStops(response.data);
      }
    } catch (error) {
      console.error("Error loading stops:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (text: string, field: "from" | "to") => {
    if (field === "from") {
      setFromLocation(text);
      setSelectedFromStop(null);
    } else {
      setToLocation(text);
      setSelectedToStop(null);
    }
    setTripResult(null);

    if (text.length > 0) {
      const filtered = stops.filter((stop) =>
        stop.name.toLowerCase().includes(text.toLowerCase())
      );
      setFilteredStops(filtered.slice(0, 6));
      setActiveInput(field);
    } else {
      setFilteredStops([]);
      setActiveInput(null);
    }
  };

  const handleStopSelect = (stop: Stop) => {
    if (activeInput === "from") {
      setFromLocation(stop.name);
      setSelectedFromStop(stop);
    } else {
      setToLocation(stop.name);
      setSelectedToStop(stop);
    }
    setFilteredStops([]);
    setActiveInput(null);
    Keyboard.dismiss();
  };

  const handleSwapLocations = () => {
    const tempText = fromLocation;
    const tempStop = selectedFromStop;
    setFromLocation(toLocation);
    setSelectedFromStop(selectedToStop);
    setToLocation(tempText);
    setSelectedToStop(tempStop);
    setTripResult(null);
  };

  const handleSearch = async () => {
    if (!selectedFromStop || !selectedToStop) {
      Alert.alert("Select Stations", "Please select stations from the dropdown suggestions.");
      return;
    }
    if (selectedFromStop.id === selectedToStop.id) {
      Alert.alert("Same Station", "Origin and destination must be different stations.");
      return;
    }

    setSearching(true);
    setTripResult(null);
    try {
      const response = await apiService.planTrip(selectedFromStop.id, selectedToStop.id);
      if (response.success && response.data) {
        setTripResult(response.data);
      } else {
        Alert.alert("No Route Found", response.error || "Could not find a route between these stations.");
      }
    } catch (error) {
      Alert.alert("Error", "Failed to plan trip. Make sure the backend is running.");
    } finally {
      setSearching(false);
    }
  };

  const renderLeg = (leg: TripLeg, index: number, total: number) => {
    const isLast = index === total - 1;
    return (
      <View key={index}>
        <View style={styles.legRow}>
          <View style={styles.legLeft}>
            <RouteSymbol routeId={leg.route.short_name} size={34} />
            {!isLast && <View style={styles.legLine} />}
          </View>
          <View style={styles.legContent}>
            <Text style={styles.legRouteName}>{leg.route.long_name}</Text>
            <Text style={styles.legStop}>Board at {leg.from_stop.name}</Text>
            <Text style={styles.legStop}>Exit at {leg.to_stop.name}</Text>
          </View>
        </View>
        {!isLast && (
          <View style={styles.transferRow}>
            <View style={styles.transferDot} />
            <Text style={styles.transferText}>Transfer at {leg.to_stop.name}</Text>
          </View>
        )}
      </View>
    );
  };

  const renderOption = (option: TripOption, index: number) => (
    <View key={index} style={styles.optionCard}>
      {/* Option header */}
      <View style={styles.optionHeader}>
        <View style={styles.optionBadges}>
          {option.legs.map((leg, i) => (
            <RouteSymbol key={i} routeId={leg.route.short_name} size={28} />
          ))}
        </View>
        <View style={styles.optionMeta}>
          <Text style={styles.optionTransfers}>
            {option.transfers === 0 ? "Direct" : `${option.transfers} transfer${option.transfers > 1 ? "s" : ""}`}
          </Text>
        </View>
      </View>

      <View style={styles.divider} />

      {/* Origin dot */}
      <View style={styles.endpointRow}>
        <View style={styles.endpointDotOrigin} />
        <Text style={styles.endpointName}>{tripResult!.origin.name}</Text>
      </View>

      {/* Legs */}
      <View style={styles.legsContainer}>
        {option.legs.map((leg, i) => renderLeg(leg, i, option.legs.length))}
      </View>

      {/* Destination dot */}
      <View style={styles.endpointRow}>
        <View style={styles.endpointDotDest} />
        <Text style={styles.endpointName}>{tripResult!.destination.name}</Text>
      </View>
    </View>
  );

  return (
    <View style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Plan Trip</Text>
        </View>

        <ScrollView
          style={styles.scrollView}
          contentContainerStyle={styles.scrollContent}
          showsVerticalScrollIndicator={false}
          keyboardShouldPersistTaps="handled"
          onScrollBeginDrag={Keyboard.dismiss}
        >
          {/* Search Card */}
          <View style={styles.searchCard}>
            {/* From Input */}
            <View style={styles.inputRow}>
              <View style={styles.inputDot}>
                <View style={styles.dotInner} />
              </View>
              <View style={styles.inputContainer}>
                <TextInput
                  style={styles.input}
                  placeholder="From"
                  value={fromLocation}
                  onChangeText={(text) => handleInputChange(text, "from")}
                  onFocus={() => setActiveInput("from")}
                  placeholderTextColor="#999"
                />
              </View>
            </View>

            {/* Connector */}
            <View style={styles.connectorContainer}>
              <View style={styles.connectorLine} />
              <TouchableOpacity style={styles.swapButton} onPress={handleSwapLocations}>
                <Ionicons name="swap-vertical" size={18} color="#1a1a1a" />
              </TouchableOpacity>
            </View>

            {/* To Input */}
            <View style={styles.inputRow}>
              <View style={[styles.inputDot, styles.inputDotDest]}>
                <View style={styles.dotInnerDest} />
              </View>
              <View style={styles.inputContainer}>
                <TextInput
                  style={styles.input}
                  placeholder="To"
                  value={toLocation}
                  onChangeText={(text) => handleInputChange(text, "to")}
                  onFocus={() => setActiveInput("to")}
                  placeholderTextColor="#999"
                />
              </View>
            </View>

            {/* Autocomplete */}
            {filteredStops.length > 0 && (
              <View style={styles.suggestionsContainer}>
                {filteredStops.map((stop) => (
                  <TouchableOpacity
                    key={stop.id}
                    style={styles.suggestionItem}
                    onPress={() => handleStopSelect(stop)}
                  >
                    <Ionicons name="train-outline" size={16} color="#666" />
                    <Text style={styles.suggestionText}>{stop.name}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            )}

            {/* Search Button */}
            <TouchableOpacity
              style={[styles.searchButton, searching && styles.searchButtonDisabled]}
              onPress={handleSearch}
              activeOpacity={0.8}
              disabled={searching}
            >
              <Text style={styles.searchButtonText}>
                {searching ? "Finding Routes..." : "Find Routes"}
              </Text>
              {!searching && <Ionicons name="arrow-forward" size={18} color="#FFFFFF" />}
            </TouchableOpacity>
          </View>

          {/* Results */}
          {tripResult && tripResult.options.length > 0 && (
            <View>
              <Text style={styles.resultsHeader}>
                {tripResult.options.length} route{tripResult.options.length > 1 ? "s" : ""} found
              </Text>
              {tripResult.options.map((option, i) => renderOption(option, i))}
            </View>
          )}

          <View style={styles.bottomSpacer} />
        </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F8F9FA" },
  header: {
    paddingTop: Platform.OS === "ios" ? 60 : 48,
    paddingBottom: 16,
    paddingHorizontal: 20,
    backgroundColor: "#F8F9FA",
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: "700",
    color: "#1a1a1a",
    letterSpacing: -0.5,
  },
  scrollView: { flex: 1 },
  scrollContent: { paddingHorizontal: 16 },
  searchCard: {
    backgroundColor: "#FFFFFF",
    borderRadius: 20,
    padding: 20,
    marginBottom: 20,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08,
    shadowRadius: 12,
    elevation: 4,
  },
  inputRow: { flexDirection: "row", alignItems: "center", gap: 14 },
  inputDot: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: "rgba(26,26,26,0.08)",
    alignItems: "center",
    justifyContent: "center",
  },
  inputDotDest: { backgroundColor: "rgba(26,26,26,0.08)" },
  dotInner: { width: 10, height: 10, borderRadius: 5, backgroundColor: "#1a1a1a" },
  dotInnerDest: { width: 10, height: 10, borderRadius: 2, backgroundColor: "#1a1a1a" },
  inputContainer: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#F8F9FA",
    borderRadius: 12,
    paddingHorizontal: 14,
  },
  input: {
    flex: 1,
    fontSize: 16,
    fontWeight: "500",
    color: "#1a1a1a",
    paddingVertical: 14,
  },
  connectorContainer: {
    flexDirection: "row",
    alignItems: "center",
    paddingLeft: 11,
    marginVertical: 4,
  },
  connectorLine: {
    width: 2,
    height: 24,
    backgroundColor: "rgba(26,26,26,0.1)",
    borderRadius: 1,
  },
  swapButton: {
    marginLeft: "auto",
    width: 36,
    height: 36,
    borderRadius: 10,
    backgroundColor: "#F8F9FA",
    alignItems: "center",
    justifyContent: "center",
  },
  suggestionsContainer: {
    marginTop: 12,
    borderTopWidth: 1,
    borderTopColor: "rgba(0,0,0,0.05)",
    paddingTop: 12,
  },
  suggestionItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    paddingVertical: 10,
    paddingHorizontal: 4,
  },
  suggestionText: { fontSize: 15, color: "#1a1a1a" },
  searchButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: "#1a1a1a",
    borderRadius: 14,
    paddingVertical: 16,
    marginTop: 20,
  },
  searchButtonDisabled: { backgroundColor: "#999" },
  searchButtonText: { fontSize: 16, fontWeight: "600", color: "#FFFFFF" },
  resultsHeader: {
    fontSize: 15,
    fontWeight: "600",
    color: "#555",
    marginBottom: 12,
    paddingHorizontal: 4,
  },
  // Option card
  optionCard: {
    backgroundColor: "#FFFFFF",
    borderRadius: 20,
    padding: 18,
    marginBottom: 16,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.07,
    shadowRadius: 10,
    elevation: 3,
  },
  optionHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 14,
  },
  optionBadges: { flexDirection: "row", gap: 6, flexWrap: "wrap", flex: 1 },
  optionMeta: { alignItems: "flex-end" },
  optionTime: { fontSize: 18, fontWeight: "700", color: "#1a1a1a" },
  optionTransfers: { fontSize: 13, color: "#666", marginTop: 2 },
  divider: { height: 1, backgroundColor: "rgba(0,0,0,0.06)", marginBottom: 14 },
  endpointRow: { flexDirection: "row", alignItems: "center", gap: 12, marginVertical: 3 },
  endpointDotOrigin: { width: 12, height: 12, borderRadius: 6, backgroundColor: "#1a1a1a" },
  endpointDotDest: { width: 12, height: 12, borderRadius: 2, backgroundColor: "#1a1a1a" },
  endpointName: { fontSize: 14, fontWeight: "600", color: "#1a1a1a", flex: 1 },
  legsContainer: { paddingLeft: 4, marginVertical: 6 },
  legRow: { flexDirection: "row", gap: 12, marginBottom: 2 },
  legLeft: { alignItems: "center", width: 34 },
  legLine: { flex: 1, width: 2, backgroundColor: "rgba(0,0,0,0.08)", marginTop: 4, minHeight: 20 },
  legContent: { flex: 1, paddingBottom: 10 },
  legRouteName: { fontSize: 13, fontWeight: "600", color: "#1a1a1a", marginBottom: 1 },
  legStop: { fontSize: 12, color: "#555" },
  transferRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    paddingLeft: 7,
    marginBottom: 6,
  },
  transferDot: {
    width: 18,
    height: 18,
    borderRadius: 9,
    borderWidth: 2,
    borderColor: "#ccc",
    backgroundColor: "#fff",
  },
  transferText: { fontSize: 12, color: "#888", fontStyle: "italic" },
  bottomSpacer: { height: 120 },
});

export default SearchScreen;
