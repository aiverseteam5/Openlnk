/**
 * Root layout — loads fonts, wraps providers.
 *
 * DESIGN.md: DM Sans (UI) + JetBrains Mono (amounts/dates/IDs/state).
 * NativeWind v4, no shadows, no dark mode.
 */

import { useEffect } from "react";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useFonts } from "expo-font";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { View, ActivityIndicator } from "react-native";

import "../global.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1 },
  },
});

export default function RootLayout() {
  const [fontsLoaded] = useFonts({
    "DM Sans": require("../assets/fonts/DMSans-Regular.ttf"),
    "DM Sans Medium": require("../assets/fonts/DMSans-Medium.ttf"),
    "DM Sans SemiBold": require("../assets/fonts/DMSans-SemiBold.ttf"),
    "JetBrains Mono": require("../assets/fonts/JetBrainsMono-Regular.ttf"),
    "JetBrains Mono SemiBold": require("../assets/fonts/JetBrainsMono-SemiBold.ttf"),
  });

  if (!fontsLoaded) {
    return (
      <View className="flex-1 items-center justify-center bg-bg">
        <ActivityIndicator color="#1A4FBF" />
      </View>
    );
  }

  return (
    <QueryClientProvider client={queryClient}>
      <StatusBar style="dark" />
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: "#F5F2EC" },
          animation: "fade",
          animationDuration: 150,
        }}
      />
    </QueryClientProvider>
  );
}
