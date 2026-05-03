import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { getMtaColor } from "../utils/mtaColors";

interface RouteSymbolProps {
  routeId: string;
  size?: number;
}

function isExpress(routeId: string) {
  return routeId.endsWith("X");
}

const RouteSymbol: React.FC<RouteSymbolProps> = ({ routeId, size = 32 }) => {
  const { background, text } = getMtaColor(routeId);
  const express = isExpress(routeId);
  const displayText = routeId.replace("X", "");

  if (express) {
    // Diamond shape for express, shrink by sqrt(2)/2 to fit in circle
    const diamondSize = size * 0.8; // sqrt(2)/2
    return (
      <View
        style={{
          width: size,
          height: size,
          alignItems: "center",
          justifyContent: "center",
          marginHorizontal: 2,
          marginBottom: 6,
        }}
      >
        <View
          style={{
            width: diamondSize,
            height: diamondSize,
            backgroundColor: background,
            transform: [{ rotate: "45deg" }],
            position: "absolute",
            borderRadius: size * 0.1,
          }}
        />
        <Text
          style={{
            color: text,
            fontWeight: "bold",
            fontSize: size * 0.6,
            textAlign: "center",
            zIndex: 1,
            // No rotation, keep upright
          }}
        >
          {displayText}
        </Text>
      </View>
    );
  }

  // Circle for local
  return (
    <View
      style={[
        styles.symbol,
        {
          backgroundColor: background,
          width: size,
          height: size,
          borderRadius: size / 2,
          marginBottom: 6,
        },
      ]}
    >
      <Text style={[styles.text, { color: text, fontSize: size * 0.6 }]}>
        {displayText}
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  symbol: {
    justifyContent: "center",
    alignItems: "center",
    marginHorizontal: 2,
  },
  text: {
    fontWeight: "bold",
    textAlign: "center",
  },
});

export default RouteSymbol;
