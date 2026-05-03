import { Ionicons } from "@expo/vector-icons";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { useNavigation } from "@react-navigation/native";
import React, { useEffect, useState } from "react";
import {
  Platform,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import RouteSymbol from "../components/RouteSymbol";
import { TrainStopsModal } from "../components/TrainStopsModal";
import { apiService, Route } from "../services/api";

const FAVORITES_KEY = "favorite_routes";

const RouteScreen = () => {
  const [routes, setRoutes] = useState<Route[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [favoriteRoutes, setFavoriteRoutes] = useState<string[]>([]);
  const [selectedRoute, setSelectedRoute] = useState<Route | null>(null);
  const [modalVisible, setModalVisible] = useState(false);
  const navigation = useNavigation<any>();

  useEffect(() => {
    loadRoutes();
    loadFavorites();
  }, []);

  const loadRoutes = async () => {
    setLoading(true);
    try {
      const response = await apiService.getRoutes();
      if (response.success && response.data) {
        setRoutes(response.data);
      }
    } catch (error) {
      console.error("Error loading routes:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadFavorites = async () => {
    try {
      const favs = await AsyncStorage.getItem(FAVORITES_KEY);
      if (favs) setFavoriteRoutes(JSON.parse(favs));
    } catch {}
  };

  const saveFavorites = async (favs: string[]) => {
    setFavoriteRoutes(favs);
    await AsyncStorage.setItem(FAVORITES_KEY, JSON.stringify(favs));
  };

  const toggleFavorite = (routeId: string) => {
    let favs = [...favoriteRoutes];
    if (favs.includes(routeId)) {
      favs = favs.filter((id) => id !== routeId);
    } else {
      favs.push(routeId);
    }
    saveFavorites(favs);
  };

  const handleRoutePress = (route: Route) => {
    setSelectedRoute(route);
    setModalVisible(true);
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadRoutes();
    setRefreshing(false);
  };

  // Group routes by color/line family
  const groupedRoutes = React.useMemo(() => {
    const groups: { [key: string]: Route[] } = {};
    routes.forEach((route) => {
      const color = route.route_color || "000000";
      if (!groups[color]) groups[color] = [];
      groups[color].push(route);
    });
    return Object.entries(groups).sort((a, b) => b[1].length - a[1].length);
  }, [routes]);

  const favoriteRoutesList = routes.filter((r) =>
    favoriteRoutes.includes(r.id)
  );

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Subway Lines</Text>
        <View style={styles.headerBadge}>
          <Text style={styles.headerBadgeText}>{routes.length}</Text>
        </View>
      </View>

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor="#1a1a1a"
          />
        }
      >
        {/* Favorites Section */}
        {favoriteRoutesList.length > 0 && (
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <Ionicons name="star" size={16} color="#1a1a1a" />
              <Text style={styles.sectionTitle}>Favorites</Text>
            </View>
            <View style={styles.routeGrid}>
              {favoriteRoutesList.map((route) => (
                <TouchableOpacity
                  key={route.id}
                  style={styles.routeCard}
                  onPress={() => handleRoutePress(route)}
                  activeOpacity={0.7}
                >
                  <RouteSymbol routeId={route.short_name} size={36} />
                  <Text style={styles.routeName} numberOfLines={1}>
                    {route.long_name}
                  </Text>
                  <TouchableOpacity
                    style={styles.favoriteButton}
                    onPress={() => toggleFavorite(route.id)}
                    hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
                  >
                    <Ionicons name="star" size={16} color="#FFB800" />
                  </TouchableOpacity>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        )}

        {/* All Lines Section */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Ionicons name="git-branch" size={16} color="#1a1a1a" />
            <Text style={styles.sectionTitle}>All Lines</Text>
          </View>

          {loading ? (
            <View style={styles.loadingContainer}>
              <Text style={styles.loadingText}>Loading lines...</Text>
            </View>
          ) : (
            groupedRoutes.map(([color, groupRoutes]) => (
              <View key={color} style={styles.lineGroup}>
                <View style={styles.routeGrid}>
                  {groupRoutes.map((route) => (
                    <TouchableOpacity
                      key={route.id}
                      style={styles.routeCard}
                      onPress={() => handleRoutePress(route)}
                      activeOpacity={0.7}
                    >
                      <RouteSymbol routeId={route.short_name} size={36} />
                      <Text style={styles.routeName} numberOfLines={1}>
                        {route.long_name}
                      </Text>
                      <TouchableOpacity
                        style={styles.favoriteButton}
                        onPress={() => toggleFavorite(route.id)}
                        hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
                      >
                        <Ionicons
                          name={
                            favoriteRoutes.includes(route.id)
                              ? "star"
                              : "star-outline"
                          }
                          size={16}
                          color={
                            favoriteRoutes.includes(route.id)
                              ? "#FFB800"
                              : "#ccc"
                          }
                        />
                      </TouchableOpacity>
                    </TouchableOpacity>
                  ))}
                </View>
              </View>
            ))
          )}
        </View>

        {/* Bottom spacing for tab bar */}
        <View style={styles.bottomSpacer} />
      </ScrollView>

      <TrainStopsModal
        visible={modalVisible}
        route={selectedRoute}
        onClose={() => {
          setModalVisible(false);
          setSelectedRoute(null);
        }}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F8F9FA",
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
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
  headerBadge: {
    backgroundColor: "rgba(26, 26, 26, 0.08)",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
  },
  headerBadgeText: {
    fontSize: 14,
    fontWeight: "600",
    color: "#1a1a1a",
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: 16,
  },
  section: {
    marginBottom: 24,
  },
  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 12,
    paddingHorizontal: 4,
  },
  sectionTitle: {
    fontSize: 15,
    fontWeight: "600",
    color: "#1a1a1a",
    letterSpacing: 0.2,
  },
  lineGroup: {
    marginBottom: 8,
  },
  routeGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
  },
  routeCard: {
    backgroundColor: "#FFFFFF",
    borderRadius: 16,
    padding: 14,
    width: "31%",
    alignItems: "center",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 2,
  },
  routeName: {
    fontSize: 11,
    fontWeight: "500",
    color: "#666",
    marginTop: 8,
    textAlign: "center",
  },
  favoriteButton: {
    position: "absolute",
    top: 8,
    right: 8,
  },
  loadingContainer: {
    paddingVertical: 40,
    alignItems: "center",
  },
  loadingText: {
    fontSize: 14,
    color: "#999",
  },
  bottomSpacer: {
    height: 120,
  },
});

export default RouteScreen;