import { Redirect } from "expo-router";
import { ActivityIndicator, StyleSheet, View } from "react-native";

import { useAuthStore } from "@/store/auth";

export default function IndexScreen() {
    const { user, hydrated } = useAuthStore();
    if (!hydrated) return <View style={styles.loading}><ActivityIndicator color="#c45d3c" /></View>;
    return <Redirect href={user ? "/(app)/(tabs)" : "/auth/login"} />;
}

const styles = StyleSheet.create({
    loading: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: "#f7f5ef" },
});
