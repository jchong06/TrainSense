import 'dotenv/config';

export default {
  expo: {
    name: "train-sense",
    entryPoint: "./App.tsx",
    plugins: [
      [
        "expo-splash-screen",
        {
          image: "./assets/images/splash-icon.png",
          imageWidth: 200,
          resizeMode: "contain",
          backgroundColor: "#ffffff"
        }
      ],
      [
        "@rnmapbox/maps",
        {
          "RNMapboxMapsVersion": "11.13.4"
        }
      ],
      [
        "expo-location",
        {
          locationWhenInUsePermission: "TrainSense needs your location to show where you are on the map.",
          locationAlwaysAndWhenInUsePermission: "TrainSense needs your location to show where you are on the map."
        }
      ]
    ],
    slug: "train-sense",
    version: "1.0.0",
    orientation: "portrait",
    icon: "./assets/images/icon.png",
    scheme: "trainsense",
    userInterfaceStyle: "automatic",
    newArchEnabled: true,
    ios: {
      supportsTablet: true,
      bundleIdentifier: "com.anonymous.train-sense",
      infoPlist: {
        NSLocationWhenInUseUsageDescription: "TrainSense needs your location to show where you are on the map.",
        NSLocationAlwaysAndWhenInUseUsageDescription: "TrainSense needs your location to show where you are on the map."
      }
    },
    android: {
      package: "com.anonymous.trainsense",
      adaptiveIcon: {
        foregroundImage: "./assets/images/adaptive-icon.png",
        backgroundColor: "#ffffff"
      },
      edgeToEdgeEnabled: true,
      permissions: [
        "ACCESS_FINE_LOCATION",
        "ACCESS_COARSE_LOCATION"
      ]
    },
    web: {
      bundler: "metro",
      favicon: "./assets/images/favicon.png"
    },
    extra: {
      mapboxAccessToken: process.env.MAPBOX_ACCESS_TOKEN
    }
  }
};