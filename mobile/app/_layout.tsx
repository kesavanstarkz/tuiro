import { Stack } from "expo-router";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { StatusBar } from "react-native";

import { AppProvider } from "@/providers/AppProvider";

export default function RootLayout() {
    return <SafeAreaProvider><StatusBar barStyle="dark-content" /><AppProvider><Stack screenOptions={{ headerShown: false }} /></AppProvider></SafeAreaProvider>;
}
