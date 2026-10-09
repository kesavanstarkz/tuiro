/**
 * Tasks list screen: displays work items, allows filtering by status/priority.
 */
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { useState } from "react";
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from "react-native";

import { tasksApi, type TaskItem } from "@/api/tasks";
import { Button, EmptyState, ErrorState, LoadingState, PageHeader, Screen } from "@/components";
import { colors, radius, shadow, spacing, typography } from "@/theme";

const STATUS_TABS = ["ALL", "TODO", "IN_PROGRESS", "DONE"] as const;

const PRIORITY_COLORS: Record<string, { bg: string; text: string }> = {
    LOW: { bg: "#F3F4F6", text: "#4B5563" },
    MEDIUM: { bg: "#EFF6FF", text: "#1D4ED8" },
    HIGH: { bg: "#FEF3C7", text: "#92400E" },
    URGENT: { bg: "#FEE2E2", text: "#991B1B" },
};

function TaskCard({ item, onPress }: { item: TaskItem; onPress: () => void }) {
    const pStyle = PRIORITY_COLORS[item.priority] || PRIORITY_COLORS.MEDIUM;

    return (
        <Pressable onPress={onPress} style={({ pressed }) => [styles.card, pressed && styles.pressed]}>
            <View style={styles.cardHeader}>
                <View style={[styles.priorityBadge, { backgroundColor: pStyle.bg }]}>
                    <Text style={[styles.priorityText, { color: pStyle.text }]}>{item.priority}</Text>
                </View>
                <View style={styles.statusBadge}>
                    <Text style={styles.statusText}>{item.status.replace(/_/g, " ")}</Text>
                </View>
            </View>

            <Text style={styles.cardTitle} numberOfLines={2}>{item.title}</Text>
            {item.description ? (
                <Text style={styles.cardDesc} numberOfLines={2}>{item.description}</Text>
            ) : null}

            <View style={styles.cardFooter}>
                {item.due_date ? (
                    <View style={styles.footerItem}>
                        <MaterialCommunityIcons name="clock-outline" size={13} color={colors.textSecondary} />
                        <Text style={styles.footerText}>Due {item.due_date}</Text>
                    </View>
                ) : null}
                {item.group_name ? (
                    <View style={styles.footerItem}>
                        <MaterialCommunityIcons name="account-group-outline" size={13} color={colors.textSecondary} />
                        <Text style={styles.footerText}>{item.group_name}</Text>
                    </View>
                ) : null}
            </View>
        </Pressable>
    );
}

export default function TasksScreen() {
    const [selectedTab, setSelectedTab] = useState<typeof STATUS_TABS[number]>("ALL");

    const { data, isLoading, isError, refetch } = useQuery({
        queryKey: ["tasks", selectedTab],
        queryFn: () => tasksApi.list({ status: selectedTab === "ALL" ? undefined : selectedTab }),
    });

    const tasks = data ?? [];

    return (
        <Screen>
            <PageHeader
                eyebrow="WORK & PROJECTS"
                title="Tasks"
                right={
                    <Pressable
                        onPress={() => router.push("/tasks/create" as never)}
                        style={styles.addBtn}
                        accessibilityRole="button"
                        accessibilityLabel="New task"
                    >
                        <MaterialCommunityIcons name="plus" size={20} color={colors.white} />
                    </Pressable>
                }
            />

            {/* Filter Tabs */}
            <View style={styles.tabsRow}>
                {STATUS_TABS.map((tab) => (
                    <Pressable
                        key={tab}
                        onPress={() => setSelectedTab(tab)}
                        style={[styles.tabChip, selectedTab === tab && styles.tabChipActive]}
                    >
                        <Text style={[styles.tabChipText, selectedTab === tab && styles.tabChipTextActive]}>
                            {tab.replace(/_/g, " ")}
                        </Text>
                    </Pressable>
                ))}
            </View>

            {isLoading && <LoadingState />}
            {isError && <ErrorState onRetry={() => void refetch()} />}

            {!isLoading && !isError && (
                <FlatList
                    data={tasks}
                    keyExtractor={(t) => t.id}
                    refreshControl={<RefreshControl refreshing={isLoading} onRefresh={() => void refetch()} />}
                    renderItem={({ item }) => (
                        <TaskCard item={item} onPress={() => router.push(`/tasks/${item.id}` as never)} />
                    )}
                    ItemSeparatorComponent={() => <View style={styles.separator} />}
                    ListEmptyComponent={
                        <EmptyState
                            icon="✅"
                            title="No tasks found"
                            message="Create a new task to organize deliverables and assignments."
                            action={
                                <Button onPress={() => router.push("/tasks/create" as never)}>
                                    Create Task
                                </Button>
                            }
                        />
                    }
                    contentContainerStyle={tasks.length === 0 ? styles.emptyContainer : undefined}
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
    tabsRow: {
        flexDirection: "row",
        gap: spacing.xs + 2,
        marginBottom: spacing.md,
    },
    tabChip: {
        paddingHorizontal: spacing.md,
        paddingVertical: spacing.xs + 2,
        borderRadius: radius.pill,
        backgroundColor: colors.white,
        borderWidth: 1,
        borderColor: colors.border,
    },
    tabChipActive: {
        backgroundColor: colors.ink,
        borderColor: colors.ink,
    },
    tabChipText: {
        ...typography.caption,
        fontSize: 12,
        fontWeight: "600",
        color: colors.textSecondary,
    },
    tabChipTextActive: {
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
    priorityBadge: {
        borderRadius: radius.sm,
        paddingHorizontal: 8,
        paddingVertical: 2,
    },
    priorityText: {
        ...typography.caption,
        fontSize: 10,
        fontWeight: "700",
    },
    statusBadge: {
        backgroundColor: colors.surfaceCard,
        borderRadius: radius.sm,
        paddingHorizontal: 8,
        paddingVertical: 2,
    },
    statusText: {
        ...typography.caption,
        fontSize: 10,
        fontWeight: "600",
        color: colors.textSecondary,
    },
    cardTitle: {
        ...typography.body,
        fontWeight: "600",
        fontSize: 15,
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
        fontSize: 11,
    },
    separator: { height: spacing.sm },
    emptyContainer: { flex: 1 },
});
