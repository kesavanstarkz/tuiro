import { Tabs, router, usePathname } from "expo-router";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { ColorValue, Platform, Pressable, ScrollView, StyleSheet, Text, View, useWindowDimensions } from "react-native";
import type { ReactNode } from "react";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { colors, radius, shadow, spacing, typography } from "@/theme";
import { useAuthStore } from "@/store/auth";

export default function TabsLayout() {
    const { width } = useWindowDimensions();
    const isDesktop = width >= 768;

    return (
        <View style={styles.shell}>
            {isDesktop && <DesktopSidebar />}
            <View style={styles.main}>
                <Tabs
                    tabBar={(props) => (isDesktop ? null : <MobileTabBar {...(props as unknown as TabBarProps)} />)}
                    screenOptions={{ headerShown: false }}
                >
                    <Tabs.Screen name="index" options={{ title: "Home", tabBarIcon: icon("view-dashboard-outline", "view-dashboard") }} />
                    <Tabs.Screen name="students" options={{ title: "Students", tabBarIcon: icon("account-school-outline", "account-school") }} />
                    <Tabs.Screen name="attendance" options={{ title: "Attendance", tabBarIcon: icon("calendar-check-outline", "calendar-check") }} />
                    <Tabs.Screen name="fees" options={{ title: "Fees", tabBarIcon: icon("cash-multiple", "cash-multiple") }} />
                    <Tabs.Screen name="more" options={{ title: "More", tabBarIcon: icon("dots-grid", "dots-grid") }} />
                </Tabs>
            </View>
        </View>
    );
}

const icon = (outline: keyof typeof MaterialCommunityIcons.glyphMap, solid: keyof typeof MaterialCommunityIcons.glyphMap) =>
    ({ color, focused }: { color: ColorValue; focused: boolean }) => (
        <MaterialCommunityIcons name={focused ? solid : outline} color={color as string} size={22} />
    );

type TabProps = { focused: boolean; color: ColorValue; size: number };
type TabBarProps = {
    state: { index: number; routes: Array<{ key: string; name: string; params?: object }> };
    descriptors: Record<string, { options: { title?: string; tabBarLabel?: unknown; tabBarAccessibilityLabel?: string; tabBarIcon?: (props: TabProps) => ReactNode } }>;
    navigation: {
        emit: (event: { type: string; target: string; canPreventDefault?: boolean }) => { defaultPrevented?: boolean };
        navigate: (name: string, params?: object) => void;
    };
};

function MobileTabBar({ state, descriptors, navigation }: TabBarProps) {
    const insets = useSafeAreaInsets();
    return (
        <View style={[styles.tabShell, { paddingBottom: Math.max(insets.bottom, 10) }]}>
            {Platform.OS === "web" && (
                <style
                    // eslint-disable-next-line react/no-danger
                    dangerouslySetInnerHTML={{
                        __html: `
                            [role="tab"], [role="tab"]:focus, [role="tab"]:focus-visible, [role="tab"]:active {
                                outline: none !important;
                                box-shadow: none !important;
                                -webkit-tap-highlight-color: transparent !important;
                            }
                        `,
                    }}
                />
            )}
            <View style={styles.tabBar}>
                {state.routes.map((route) => {
                    const focused = state.routes[state.index]?.key === route.key;
                    const options = descriptors[route.key].options;
                    const label = typeof options.tabBarLabel === "string" ? options.tabBarLabel : options.title ?? route.name;
                    const onPress = () => {
                        const event = navigation.emit({ type: "tabPress", target: route.key, canPreventDefault: true });
                        if (!focused && !event.defaultPrevented) navigation.navigate(route.name, route.params);
                    };

                    return (
                        <Pressable
                            key={route.key}
                            accessibilityRole="tab"
                            accessibilityState={{ selected: focused }}
                            onPress={onPress}
                            style={({ pressed }) => [styles.tabItem, pressed && styles.tabPressed]}
                        >
                            <View style={[styles.indicatorPill, focused && styles.indicatorPillActive]}>
                                {options.tabBarIcon?.({
                                    focused,
                                    color: focused ? colors.white : colors.textSecondary,
                                    size: 20,
                                })}
                            </View>
                            <Text style={[styles.tabLabel, focused && styles.tabLabelActive]}>{label}</Text>
                        </Pressable>
                    );
                })}
            </View>
        </View>
    );
}

function DesktopSidebar() {
    const pathname = usePathname();
    const { user, signOut } = useAuthStore();

    const mainNav = [
        { label: "Home", route: "/(app)/(tabs)", icon: "view-dashboard-outline" as const, activeIcon: "view-dashboard" as const },
        { label: "Students", route: "/(app)/(tabs)/students", icon: "account-school-outline" as const, activeIcon: "account-school" as const },
        { label: "Attendance", route: "/(app)/(tabs)/attendance", icon: "calendar-check-outline" as const, activeIcon: "calendar-check" as const },
        { label: "Fees", route: "/(app)/(tabs)/fees", icon: "cash-multiple" as const, activeIcon: "cash-multiple" as const },
        { label: "Classes", route: "/classes", icon: "google-classroom" as const, activeIcon: "google-classroom" as const },
    ];

    const academicNav = [
        { label: "Homework", route: "/homework", icon: "book-open-page-variant-outline" as const },
        { label: "Tests", route: "/tests", icon: "clipboard-text-outline" as const },
        { label: "Schedule", route: "/schedule", icon: "calendar-clock-outline" as const },
    ];

    const peopleNav = [
        { label: "Parents", route: "/parents", icon: "account-group-outline" as const },
        { label: "Teachers", route: "/teachers", icon: "account-tie-outline" as const },
    ];

    const businessNav = [
        { label: "Receipts", route: "/receipts", icon: "receipt-text-outline" as const },
        { label: "Reports", route: "/reports", icon: "chart-line" as const },
    ];

    const systemNav = [
        { label: "Notifications", route: "/notifications", icon: "bell-outline" as const },
        { label: "Subscription", route: "/subscription", icon: "star-outline" as const },
        { label: "Settings", route: "/settings", icon: "cog-outline" as const },
    ];

    return (
        <View style={styles.sidebar}>
            <View style={styles.brand}>
                <Text style={styles.brandText}>TUIRO</Text>
                <View style={styles.brandDot} />
            </View>

            <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.sidebarScroll}>
                <View style={styles.sidebarGroup}>
                    {mainNav.map((item) => {
                        const active = pathname === item.route || (item.route === "/(app)/(tabs)" && pathname === "/");
                        return (
                            <Pressable
                                key={item.route}
                                onPress={() => router.push(item.route as never)}
                                style={({ pressed }) => [styles.sidebarItem, active && styles.sidebarItemActive, pressed && styles.pressed]}
                            >
                                <MaterialCommunityIcons
                                    name={active ? item.activeIcon : item.icon}
                                    size={20}
                                    color={active ? colors.white : colors.inkSoft}
                                />
                                <Text style={[styles.sidebarItemText, active && styles.sidebarItemTextActive]}>{item.label}</Text>
                            </Pressable>
                        );
                    })}
                </View>

                <Text style={styles.sidebarSectionTitle}>ACADEMIC</Text>
                <View style={styles.sidebarGroup}>
                    {academicNav.map((item) => {
                        const active = pathname.startsWith(item.route);
                        return (
                            <Pressable
                                key={item.route}
                                onPress={() => router.push(item.route as never)}
                                style={({ pressed }) => [styles.sidebarItem, active && styles.sidebarItemActive, pressed && styles.pressed]}
                            >
                                <MaterialCommunityIcons name={item.icon} size={19} color={active ? colors.white : colors.textSecondary} />
                                <Text style={[styles.sidebarItemText, active && styles.sidebarItemTextActive]}>{item.label}</Text>
                            </Pressable>
                        );
                    })}
                </View>

                <Text style={styles.sidebarSectionTitle}>PEOPLE</Text>
                <View style={styles.sidebarGroup}>
                    {peopleNav.map((item) => {
                        const active = pathname.startsWith(item.route);
                        return (
                            <Pressable
                                key={item.route}
                                onPress={() => router.push(item.route as never)}
                                style={({ pressed }) => [styles.sidebarItem, active && styles.sidebarItemActive, pressed && styles.pressed]}
                            >
                                <MaterialCommunityIcons name={item.icon} size={19} color={active ? colors.white : colors.textSecondary} />
                                <Text style={[styles.sidebarItemText, active && styles.sidebarItemTextActive]}>{item.label}</Text>
                            </Pressable>
                        );
                    })}
                </View>

                <Text style={styles.sidebarSectionTitle}>BUSINESS</Text>
                <View style={styles.sidebarGroup}>
                    {businessNav.map((item) => {
                        const active = pathname.startsWith(item.route);
                        return (
                            <Pressable
                                key={item.route}
                                onPress={() => router.push(item.route as never)}
                                style={({ pressed }) => [styles.sidebarItem, active && styles.sidebarItemActive, pressed && styles.pressed]}
                            >
                                <MaterialCommunityIcons name={item.icon} size={19} color={active ? colors.white : colors.textSecondary} />
                                <Text style={[styles.sidebarItemText, active && styles.sidebarItemTextActive]}>{item.label}</Text>
                            </Pressable>
                        );
                    })}
                </View>

                <Text style={styles.sidebarSectionTitle}>SYSTEM</Text>
                <View style={styles.sidebarGroup}>
                    {systemNav.map((item) => {
                        const active = pathname.startsWith(item.route);
                        return (
                            <Pressable
                                key={item.route}
                                onPress={() => router.push(item.route as never)}
                                style={({ pressed }) => [styles.sidebarItem, active && styles.sidebarItemActive, pressed && styles.pressed]}
                            >
                                <MaterialCommunityIcons name={item.icon} size={19} color={active ? colors.white : colors.textSecondary} />
                                <Text style={[styles.sidebarItemText, active && styles.sidebarItemTextActive]}>{item.label}</Text>
                            </Pressable>
                        );
                    })}
                </View>
            </ScrollView>

            <View style={styles.sidebarFooter}>
                <View style={styles.sidebarUser}>
                    <View style={styles.sidebarAvatar}>
                        <Text style={styles.sidebarAvatarText}>
                            {user?.display_name?.slice(0, 1).toUpperCase() ?? "T"}
                        </Text>
                    </View>
                    <View style={styles.sidebarUserInfo}>
                        <Text style={styles.sidebarUserName} numberOfLines={1}>{user?.display_name ?? "Teacher"}</Text>
                        <Text style={styles.sidebarUserRole}>{user?.role ?? "Centre Owner"}</Text>
                    </View>
                </View>
                <Pressable
                    onPress={() => void signOut().then(() => router.replace("/auth/login"))}
                    style={({ pressed }) => [styles.sidebarSignOut, pressed && styles.pressed]}
                >
                    <MaterialCommunityIcons name="logout" size={18} color={colors.danger} />
                </Pressable>
            </View>
        </View>
    );
}

const tabShadow = Platform.select({
    web: { boxShadow: "0 6px 20px rgba(30, 42, 35, 0.08)" },
    ios: { shadowColor: colors.ink, shadowOffset: { width: 0, height: 6 }, shadowOpacity: 0.08, shadowRadius: 16 },
    android: { elevation: 6 },
    default: {},
});

const styles = StyleSheet.create({
    shell: { flex: 1, flexDirection: "row", backgroundColor: colors.paper },
    main: { flex: 1, height: "100%" },

    // Mobile Bottom Tab Bar (§6)
    tabShell: { bottom: 0, left: 0, paddingHorizontal: 16, position: "absolute", right: 0 },
    tabBar: {
        alignItems: "center",
        backgroundColor: colors.white,
        borderColor: colors.border,
        borderRadius: 24,
        borderWidth: 1,
        flexDirection: "row",
        height: 68,
        justifyContent: "space-around",
        paddingHorizontal: 8,
        ...tabShadow,
    },
    tabItem: {
        alignItems: "center",
        borderRadius: 20,
        flex: 1,
        gap: 3,
        justifyContent: "center",
        minHeight: 56,
        outlineColor: "transparent",
        outlineWidth: 0,
        userSelect: "none",
    },
    indicatorPill: {
        alignItems: "center",
        borderRadius: 16,
        height: 32,
        justifyContent: "center",
        maxWidth: 54,
        outlineColor: "transparent",
        outlineWidth: 0,
        overflow: "hidden",
        width: 52,
    },
    indicatorPillActive: {
        backgroundColor: colors.ink,
        borderRadius: 16,
        overflow: "hidden",
    },
    tabLabel: { color: colors.textSecondary, fontSize: 10, fontWeight: "500", fontFamily: typography.caption.fontFamily },
    tabLabelActive: { color: colors.ink, fontWeight: "700" },
    tabPressed: { opacity: 0.75, transform: [{ scale: 0.98 }] },

    // Desktop Left Sidebar (§1, §6)
    sidebar: {
        width: 250,
        backgroundColor: colors.white,
        borderRightColor: colors.border,
        borderRightWidth: 1,
        height: "100%",
        paddingTop: spacing.xl,
        paddingBottom: spacing.lg,
    },
    brand: {
        flexDirection: "row",
        alignItems: "center",
        paddingHorizontal: spacing.xl,
        paddingBottom: spacing.lg,
        borderBottomColor: colors.border,
        borderBottomWidth: 1,
    },
    brandText: {
        ...typography.display,
        fontSize: 22,
        letterSpacing: 2,
        color: colors.primary,
        fontWeight: "800",
    },
    brandDot: {
        width: 6,
        height: 6,
        borderRadius: 3,
        backgroundColor: colors.ink,
        marginLeft: 4,
        marginTop: 6,
    },
    sidebarScroll: {
        paddingHorizontal: spacing.md,
        paddingTop: spacing.md,
        gap: spacing.xs,
    },
    sidebarSectionTitle: {
        ...typography.label,
        paddingHorizontal: spacing.md,
        paddingTop: spacing.lg,
        paddingBottom: spacing.xs,
        color: colors.muted,
    },
    sidebarGroup: {
        gap: 2,
    },
    sidebarItem: {
        flexDirection: "row",
        alignItems: "center",
        paddingHorizontal: spacing.md,
        paddingVertical: 10,
        borderRadius: radius.pill,
        gap: spacing.md,
        outlineColor: "transparent",
        outlineWidth: 0,
        overflow: "hidden",
        userSelect: "none",
    },
    sidebarItemActive: {
        backgroundColor: colors.ink,
        borderRadius: radius.pill,
    },
    sidebarItemText: {
        ...typography.body,
        fontSize: 14,
        fontWeight: "500",
        color: colors.inkSoft,
    },
    sidebarItemTextActive: {
        color: colors.white,
        fontWeight: "600",
    },
    sidebarFooter: {
        flexDirection: "row",
        alignItems: "center",
        justifyContent: "space-between",
        paddingHorizontal: spacing.lg,
        paddingTop: spacing.md,
        borderTopColor: colors.border,
        borderTopWidth: 1,
    },
    sidebarUser: {
        flexDirection: "row",
        alignItems: "center",
        gap: spacing.sm,
        flex: 1,
    },
    sidebarAvatar: {
        width: 34,
        height: 34,
        borderRadius: 17,
        backgroundColor: colors.primary,
        alignItems: "center",
        justifyContent: "center",
    },
    sidebarAvatarText: {
        color: colors.white,
        fontSize: 14,
        fontWeight: "700",
    },
    sidebarUserInfo: {
        flex: 1,
    },
    sidebarUserName: {
        ...typography.body,
        fontSize: 13,
        fontWeight: "600",
        color: colors.ink,
    },
    sidebarUserRole: {
        ...typography.caption,
        fontSize: 11,
    },
    sidebarSignOut: {
        padding: spacing.xs,
    },
    pressed: {
        opacity: 0.8,
    },
});
