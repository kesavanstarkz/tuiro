import { Stack } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";

export default function AuthLayout() { return <SafeAreaView edges={["top", "bottom"]} style={{ flex: 1, backgroundColor: "#f7f5ef" }}><Stack screenOptions={{ headerShown: false }} /></SafeAreaView>; }
