import { MaterialCommunityIcons } from "@expo/vector-icons";
import { router } from "expo-router";
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { Card, PageHeader, Screen } from "@/components";
import { useAuthStore } from "@/store/auth";
import { colors, radius, shadow, spacing, typography } from "@/theme";

type MenuItem = {
    title: string;
    route: string;
    icon: keyof typeof MaterialCommunityIcons.glyphMap;
};

const GROUPS: Array<{ title: string; items: MenuItem[] }> = [
    {
        title: "ACADEMIC",
        items: [
            { title: "Homework", route: "/homework", icon: "book-open-page-variant-outline" },
            { title: "Tests", route: "/tests", icon: "clipboard-text-outline" },
            { title: "Schedule", route: "/schedule", icon: "calendar-clock-outline" },
        ],
    },
    {
        title: "PEOPLE",
        items: [
            { title: "Parents", route: "/parents", icon: "account-group-outline" },
            { title: "Teachers", route: "/teachers", icon: "account-tie-outline" },
            { title: "Classes", route: "/classes", icon: "google-classroom" },
        ],
    },
    {
        title: "BUSINESS",
        items: [
            { title: "Receipts", route: "/receipts", icon: "receipt-text-outline" },
            { title: "Reports", route: "/reports", icon: "chart-line" },
        ],
    },
    {
        title: "SYSTEM",
        items: [
            { title: "Notifications", route: "/notifications", icon: "bell-outline" },
            { title: "Subscription", route: "/subscription", icon: "star-outline" },
            { title: "Settings", route: "/settings", icon: "cog-outline" },
            { title: "Help", route: "/help", icon: "help-circle-outline" },
        ],
    },
];

export default function MoreScreen() {
    const signOut = useAuthStore((state) => state.signOut);

    const handleSignOut = () => {
        Alert.alert("Sign Out", "Are you sure you want to sign out of your account?", [
            { text: "Cancel", style: "cancel" },
            {
                text: "Sign Out",
                style: "destructive",
                onPress: () => {
                    void signOut().then(() => router.replace("/auth/login"));
                },
            },
        ]);
    };

    return (
        <Screen>
            <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.content}>
                <PageHeader eyebrow="WORKSPACE" title="More" subtitle="Your centre, organised." />

                {GROUPS.map((group) => (
                    <View key={group.title} style={styles.group}>
                        <Text style={styles.groupTitle}>{group.title}</Text>
                        <Card style={styles.menuCard}>
                            {group.items.map((item, index) => {
                                const isLast = index === group.items.length - 1;
                                return (
                                    <Pressable
                                        key={item.title}
                                        accessibilityRole="button"
                                        onPress={() => router.push(item.route as never)}
                                        style={({ pressed }) => [
                                            styles.row,
                                            !isLast && styles.rowDivider,
                                            pressed && styles.pressed,
                                        ]}
                                    >
                                        <View style={styles.iconWrap}>
                                            <MaterialCommunityIcons name={item.icon} color={colors.primary} size={20} />
                                        </View>
                                        <Text style={styles.rowTitle}>{item.title}</Text>
                                        <MaterialCommunityIcons name="chevron-right" color={colors.muted} size={20} />
                                    </Pressable>
                                );
                            })}
                        </Card>
                    </View>
                ))}

                <Pressable accessibilityRole="button" style={styles.signOut} onPress={handleSignOut}>
                    <MaterialCommunityIcons name="logout" color={colors.danger} size={20} />
                    <Text style={styles.signOutText}>Sign out</Text>
                </Pressable>
            </ScrollView>
        </Screen>
    );
}

const styles = StyleSheet.create({
    content: {
        paddingBottom: spacing.xxl,
        gap: spacing.lg,
    },
    group: {
        gap: spacing.xs,
    },
    groupTitle: {
        ...typography.label,
        paddingHorizontal: spacing.xs,
    },
    menuCard: {
        padding: 0,
        overflow: "hidden",
    },
    row: {
        alignItems: "center",
        flexDirection: "row",
        minHeight: 56,
        paddingHorizontal: spacing.lg,
    },
    rowDivider: {
        borderBottomColor: colors.border,
        borderBottomWidth: StyleSheet.hairlineWidth,
    },
    pressed: {
        backgroundColor: colors.featureBlue,
    },
    iconWrap: {
        alignItems: "center",
        backgroundColor: colors.primaryLight,
        borderRadius: radius.sm,
        height: 36,
        justifyContent: "center",
        marginRight: spacing.md,
        width: 36,
    },
    rowTitle: {
        ...typography.body,
        color: colors.ink,
        flex: 1,
        fontSize: 15,
        fontWeight: "600",
    },
    signOut: {
        alignItems: "center",
        flexDirection: "row",
        gap: spacing.sm,
        justifyContent: "center",
        minHeight: 48,
        marginTop: spacing.md,
    },
    signOutText: {
        color: colors.danger,
        fontSize: 15,
        fontWeight: "600",
        fontFamily: typography.body.fontFamily,
    },
});
