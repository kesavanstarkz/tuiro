import { Tabs } from "expo-router";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { ColorValue, Platform, Pressable, StyleSheet, Text, View } from "react-native";
import type { ReactNode } from "react";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { colors } from "@/theme";

export default function TabsLayout() {
    return <Tabs tabBar={(props) => <PremiumTabBar {...(props as unknown as TabBarProps)} />} screenOptions={{ headerShown: false }}><Tabs.Screen name="index" options={{ title: "Home", tabBarIcon: icon("view-dashboard-outline") }} /><Tabs.Screen name="students" options={{ title: "Students", tabBarIcon: icon("account-school-outline") }} /><Tabs.Screen name="attendance" options={{ title: "Attendance", tabBarIcon: icon("calendar-check-outline") }} /><Tabs.Screen name="fees" options={{ title: "Fees", tabBarIcon: icon("cash-multiple") }} /><Tabs.Screen name="more" options={{ title: "More", tabBarIcon: icon("dots-grid") }} /></Tabs>;
}

const icon = (name: keyof typeof MaterialCommunityIcons.glyphMap) => ({ color, focused }: { color: ColorValue; focused: boolean }) => <MaterialCommunityIcons name={name} color={color as string} size={focused ? 22 : 21} accessibilityLabel={name} />;
type TabProps = { focused: boolean; color: ColorValue; size: number };
type TabBarProps = { state: { index: number; routes: Array<{ key: string; name: string; params?: object }> }; descriptors: Record<string, { options: { title?: string; tabBarLabel?: unknown; tabBarAccessibilityLabel?: string; tabBarIcon?: (props: TabProps) => ReactNode } }>; navigation: { emit: (event: { type: string; target: string; canPreventDefault?: boolean }) => { defaultPrevented?: boolean }; navigate: (name: string, params?: object) => void } };
function PremiumTabBar({ state, descriptors, navigation }: TabBarProps) {
    const insets = useSafeAreaInsets();
    return <View style={[styles.tabShell, { paddingBottom: Math.max(insets.bottom, 10) }]}><View style={styles.tabBar}>{state.routes.map((route) => {
        const focused = state.routes[state.index]?.key === route.key; const options = descriptors[route.key].options; const label = typeof options.tabBarLabel === "string" ? options.tabBarLabel : options.title ?? route.name;
        const onPress = () => { const event = navigation.emit({ type: "tabPress", target: route.key, canPreventDefault: true }); if (!focused && !event.defaultPrevented) navigation.navigate(route.name, route.params); };
        return <Pressable key={route.key} accessibilityRole="tab" accessibilityState={{ selected: focused }} accessibilityLabel={options.tabBarAccessibilityLabel ?? label} onPress={onPress} style={({ pressed }) => [styles.tabItem, pressed && styles.tabPressed]}><View style={[styles.iconSlot, focused && styles.iconSlotActive]}>{options.tabBarIcon?.({ focused, color: focused ? colors.white : colors.muted, size: 21 })}</View><Text style={[styles.tabLabel, focused && styles.tabLabelActive]}>{label}</Text>{focused && <View style={styles.activeDot} />}</Pressable>;
    })}</View></View>;
}
const tabShadow = Platform.select({ web: { boxShadow: "0 8px 18px rgba(32, 40, 58, 0.12)" }, ios: { shadowColor: colors.ink, shadowOffset: { width: 0, height: 8 }, shadowOpacity: 0.12, shadowRadius: 18 }, android: { elevation: 8 }, default: {} });
const styles = StyleSheet.create({ tabShell: { bottom: 0, left: 0, paddingHorizontal: 16, position: "absolute", right: 0 }, tabBar: { alignItems: "center", backgroundColor: colors.white, borderColor: colors.line, borderRadius: 26, borderWidth: 1, flexDirection: "row", height: 72, justifyContent: "space-around", paddingHorizontal: 6, ...tabShadow }, tabItem: { alignItems: "center", borderRadius: 18, flex: 1, gap: 2, justifyContent: "center", minHeight: 60 }, iconSlot: { alignItems: "center", height: 27, justifyContent: "center", width: 32 }, iconSlotActive: { backgroundColor: colors.primary, borderRadius: 10 }, tabLabel: { color: colors.muted, fontSize: 10, fontWeight: "700" }, tabLabelActive: { color: colors.primary, fontWeight: "800" }, activeDot: { backgroundColor: colors.accent, borderRadius: 3, height: 4, marginTop: 1, width: 4 }, tabPressed: { opacity: 0.72, transform: [{ scale: .97 }] } });
