/**
 * Requests list screen: shows My Requests and Pending Approvals (for approvers).
 */
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { useState } from "react";
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from "react-native";

import { requestsApi, type ApprovalRequest } from "@/api/requests";
import { Button, EmptyState, ErrorState, LoadingState, PageHeader, Screen } from "@/components";
import { useAuthStore } from "@/store/auth";
import { colors, radius, shadow, spacing, typography } from "@/theme";

const STATUS_COLORS: Record<string, { bg: string; text: string }> = {
    PENDING: { bg: "#FEF3C7", text: "#92400E" },
    APPROVED: { bg: "#D1FAE5", text: "#065F46" },
    REJECTED: { bg: "#FEE2E2", text: "#991B1B" },
    CANCELLED: { bg: "#F3F4F6", text: "#4B5563" },
};

function RequestCard({ item, onPress }: { item: ApprovalRequest; onPress: () => void }) {
    const statusStyle = STATUS_COLORS[item.status] || STATUS_COLORS.PENDING;
    const dateRange = [item.start_date, item.end_date].filter(Boolean).join(" → ");

    return (
        <Pressable onPress={onPress} style={({ pressed }) => [styles.card, pressed && styles.pressed]}>
            <View style={styles.cardHeader}>
                <View style={styles.typeBadge}>
                    <Text style={styles.typeText}>{item.request_type.replace(/_/g, " ")}</Text>
                </View>
                <View style={[styles.statusBadge, { backgroundColor: statusStyle.bg }]}>
                    <Text style={[styles.statusText, { color: statusStyle.text }]}>{item.status}</Text>
                </View>
            </View>

            <Text style={styles.cardTitle} numberOfLines={1}>{item.title}</Text>
            {item.description ? (
                <Text style={styles.cardDesc} numberOfLines={2}>{item.description}</Text>
            ) : null}

            <View style={styles.cardFooter}>
                {dateRange ? (
                    <View style={styles.footerItem}>
                        <MaterialCommunityIcons name="calendar-range" size={14} color={colors.textSecondary} />
                        <Text style={styles.footerText}>{dateRange}</Text>
                    </View>
                ) : null}
                {item.requester_name ? (
                    <View style={styles.footerItem}>
                        <MaterialCommunityIcons name="account-outline" size={14} color={colors.textSecondary} />
                        <Text style={styles.footerText}>{item.requester_name}</Text>
                    </View>
                ) : null}
            </View>
        </Pressable>
    );
}

export default function RequestsScreen() {
    const { user } = useAuthStore();
    const isApprover = user?.role === "OWNER" || user?.role === "ADMIN";
    const [tab, setTab] = useState<"my" | "pending">(isApprover ? "pending" : "my");

    const { data, isLoading, isError, refetch } = useQuery({
        queryKey: ["requests", tab],
        queryFn: () => requestsApi.list({ scope: tab }),
    });

    const requests = data ?? [];

    return (
        <Screen>
            <PageHeader
                eyebrow="WORKFLOWS"
                title="Requests"
                right={
                    <Pressable
                        onPress={() => router.push("/requests/create" as never)}
                        style={styles.addBtn}
                        accessibilityRole="button"
                        accessibilityLabel="New request"
                    >
                        <MaterialCommunityIcons name="plus" size={20} color={colors.white} />
                    </Pressable>
                }
            />

            {isApprover && (
                <View style={styles.tabBar}>
                    <Pressable
                        onPress={() => setTab("pending")}
                        style={[styles.tabItem, tab === "pending" && styles.tabItemActive]}
                    >
                        <Text style={[styles.tabText, tab === "pending" && styles.tabTextActive]}>Pending Approval</Text>
                    </Pressable>
                    <Pressable
                        onPress={() => setTab("my")}
                        style={[styles.tabItem, tab === "my" && styles.tabItemActive]}
                    >
                        <Text style={[styles.tabText, tab === "my" && styles.tabTextActive]}>My Requests</Text>
                    </Pressable>
                </View>
            )}

            {isLoading && <LoadingState />}
            {isError && <ErrorState onRetry={() => void refetch()} />}

            {!isLoading && !isError && (
                <FlatList
                    data={requests}
                    keyExtractor={(r) => r.id}
                    refreshControl={<RefreshControl refreshing={isLoading} onRefresh={() => void refetch()} />}
                    renderItem={({ item }) => (
                        <RequestCard item={item} onPress={() => router.push(`/requests/${item.id}` as never)} />
                    )}
                    ItemSeparatorComponent={() => <View style={styles.separator} />}
                    ListEmptyComponent={
                        <EmptyState
                            icon="📋"
                            title={tab === "pending" ? "No pending approvals" : "No requests submitted"}
                            message={
                                tab === "pending"
                                    ? "All requests have been reviewed."
                                    : "Submit a request for leave, attendance correction, or permission."
                            }
                            action={
                                <Button onPress={() => router.push("/requests/create" as never)}>
                                    New Request
                                </Button>
                            }
                        />
                    }
                    contentContainerStyle={requests.length === 0 ? styles.emptyContainer : undefined}
                    showsVerticalScrollIndicator={false}
                />
            )}
        </Screen>
    );
}

const styles = StyleSheet.create({
    addBtn: {
        width: 40,
        height: 40,
        borderRadius: 20,
        backgroundColor: colors.primary,
        alignItems: "center",
        justifyContent: "center",
    },
    tabBar: {
        flexDirection: "row",
        backgroundColor: colors.surfaceCard,
        borderRadius: radius.pill,
        borderWidth: 1,
        borderColor: colors.border,
        padding: 4,
        marginBottom: spacing.md,
    },
    tabItem: {
        flex: 1,
        paddingVertical: spacing.xs + 2,
        alignItems: "center",
        borderRadius: radius.pill,
    },
    tabItemActive: {
        backgroundColor: colors.ink,
    },
    tabText: {
        ...typography.body,
        fontSize: 13,
        fontWeight: "600",
        color: colors.textSecondary,
    },
    tabTextActive: {
        color: colors.white,
    },
    card: {
        backgroundColor: colors.white,
        borderRadius: radius.lg,
        padding: spacing.md,
        gap: spacing.xs,
        ...shadow,
    },
    pressed: { opacity: 0.8 },
    cardHeader: {
        flexDirection: "row",
        justifyContent: "space-between",
        alignItems: "center",
    },
    typeBadge: {
        backgroundColor: colors.primaryLight,
        borderRadius: radius.sm,
        paddingHorizontal: 8,
        paddingVertical: 2,
    },
    typeText: {
        ...typography.caption,
        fontSize: 11,
        fontWeight: "700",
        color: colors.primary,
        textTransform: "uppercase",
    },
    statusBadge: {
        borderRadius: radius.sm,
        paddingHorizontal: 8,
        paddingVertical: 2,
    },
    statusText: {
        ...typography.caption,
        fontSize: 11,
        fontWeight: "700",
    },
    cardTitle: {
        ...typography.body,
        fontWeight: "600",
        fontSize: 16,
        color: colors.ink,
        marginTop: 2,
    },
    cardDesc: {
        ...typography.caption,
        color: colors.textSecondary,
        lineHeight: 18,
    },
    cardFooter: {
        flexDirection: "row",
        alignItems: "center",
        gap: spacing.md,
        marginTop: spacing.xs,
        paddingTop: spacing.xs,
        borderTopWidth: StyleSheet.hairlineWidth,
        borderTopColor: colors.border,
    },
    footerItem: {
        flexDirection: "row",
        alignItems: "center",
        gap: 4,
    },
    footerText: {
        ...typography.caption,
        color: colors.textSecondary,
        fontSize: 12,
    },
    separator: { height: spacing.sm },
    emptyContainer: { flex: 1 },
});
