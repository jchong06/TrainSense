import { Ionicons } from "@expo/vector-icons";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { NavigationContainer } from "@react-navigation/native";
import { StatusBar } from "expo-status-bar";
import React from "react";
import { Platform, View } from "react-native";

import MapScreen from "./src/screens/MapScreen";
import RouteScreen from "./src/screens/RouteScreen";
import SearchScreen from "./src/screens/SearchScreen";

const Tab = createBottomTabNavigator();

// Custom floating tab bar with minimalist design
function MinimalTabBar({ state, descriptors, navigation }: any) {
  return (
    <View
      style={{
        position: "absolute",
        bottom: Platform.OS === "ios" ? 32 : 24,
        left: 24,
        right: 24,
        backgroundColor: "rgba(18, 18, 18, 0.94)",
        borderRadius: 24,
        flexDirection: "row",
        paddingVertical: 14,
        paddingHorizontal: 12,
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 8 },
        shadowOpacity: 0.2,
        shadowRadius: 24,
        elevation: 12,
        borderWidth: 1,
        borderColor: "rgba(255, 255, 255, 0.06)",
      }}
    >
      {state.routes.map((route: any, index: number) => {
        const isFocused = state.index === index;

        const iconName = (() => {
          switch (route.name) {
            case "Map":
              return isFocused ? "navigate" : "navigate-outline";
            case "Lines":
              return isFocused ? "git-branch" : "git-branch-outline";
            case "Search":
              return isFocused ? "search" : "search-outline";
            default:
              return "help-outline";
          }
        })();

        const onPress = () => {
          const event = navigation.emit({
            type: "tabPress",
            target: route.key,
            canPreventDefault: true,
          });

          if (!isFocused && !event.defaultPrevented) {
            navigation.navigate(route.name);
          }
        };

        return (
          <View
            key={route.key}
            style={{
              flex: 1,
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <View
              style={{
                backgroundColor: isFocused
                  ? "rgba(255, 255, 255, 0.12)"
                  : "transparent",
                borderRadius: 14,
                paddingVertical: 10,
                paddingHorizontal: 24,
              }}
            >
              <Ionicons
                name={iconName as keyof typeof Ionicons.glyphMap}
                size={24}
                color={isFocused ? "#FFFFFF" : "rgba(255, 255, 255, 0.4)"}
                onPress={onPress}
              />
            </View>
          </View>
        );
      })}
    </View>
  );
}

export default function App() {
  return (
    <NavigationContainer>
      <StatusBar style="dark" />
      <Tab.Navigator
        initialRouteName="Map"
        tabBar={(props) => <MinimalTabBar {...props} />}
        screenOptions={{
          headerShown: false,
        }}
      >
        <Tab.Screen name="Map" component={MapScreen} />
        <Tab.Screen name="Lines" component={RouteScreen} />
        <Tab.Screen name="Search" component={SearchScreen} />
      </Tab.Navigator>
    </NavigationContainer>
  );
}