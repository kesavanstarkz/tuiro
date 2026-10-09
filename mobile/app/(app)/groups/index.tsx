/**
 * Canonical Groups list screen (v2 API).
 * Shows groups of all kinds (team, class, department, batch).
 * Kind label is terminology-driven; here we show the raw kind with a chip.
 */
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { useState } from "react";
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, TextInput, View } from "react-native";

import { v2GroupsApi, type CanonicalGroup } from "@/api/v2Groups";
import { Button, EmptyState, ErrorState, LoadingState, PageHeader, Screen } from "@/components";
import { colors, radius, shadow, spacing, typography } from "@/theme";

const KIND_ICONS: Record<string, keyof typeof MaterialCommunityIcons.glyphMap> = {
    team: "account-group",
    department: "office-building-outline",
    class: "google-classroom",
    batch: "layers-outline",
};

function GroupRow({ group, onPress }: { group: CanonicalGroup; onPress: () => void }) {
    const icon = KIND_ICONS[group.kind] ?? "folder-outline";
    return (
        <Pressable onPress={onPress} style={({ pressed }) => [styles.row, pressed && styles.pressed]}>
            <View style={styles.iconWrap}>
                <MaterialCommunityIcons name={icon} size={22} color={colors.primary} />
            </View>
            <View style={styles.rowInfo}>
                <Text style={styles.rowName} numberOfLines={1}>{group.name}</Text>
                {group.description ? (
                    <Text style={styles.rowSub} numberOfLines={1}>{group.description}</Text>
                ) : (
                    <Text style={styles.rowKind}>{group.kind}</Text>
                )}
            </View>
            <MaterialCommunityIcons name="chevron-right" size={18} color={colors.muted} />
        </Pressable>
    );
}

export default function GroupsScreen() {
    const [search, setSearch] = useState("");
    const [showArchived, setShowArchived] = useState(false);

    const { data, isLoading, isError, refetch } = useQuery({
        queryKey: ["v2groups", showArchived],
        queryFn: () => v2GroupsApi.list({ include_archived: showArchived }),
    });

    const groups = (data ?? []).filter((g) =>
        search ? g.name.toLowerCase().includes(search.toLowerCase()) : true,
    );

    return (
        <Screen>
            <PageHeader
                eyebrow="ORGANIZATION"
                title="Groups"
                right={
                    <Pressable
                        onPress={() => router.push("/groups/create" as never)}
                        style={styles.addBtn}
                        accessibilityRole="button"
                        accessibilityLabel="Create group"
                    >
                        <MaterialCommunityIcons name="plus" size={20} color={colors.white} />
                    </Pressable>
                }
            />

            <View style={styles.searchRow}>
                <View style={styles.searchBox}>
                    <MaterialCommunityIcons name="magnify" size={18} color={colors.muted} />
                    <TextInput
                        placeholder="Search groups…"
                        placeholderTextColor={colors.muted}
                        value={search}
                        onChangeText={setSearch}
                        style={styles.searchInput}
                        clearButtonMode="while-editing"
                    />
                </View>
                <Pressable onPress={() => setShowArchived((v) => !v)} style={[styles.filterBtn, showArchived && styles.filterBtnActive]}>
                    <Text style={[styles.filterText, showArchived && styles.filterTextActive]}>Archived</Text>
                </Pressable>
            </View>

            {isLoading && <LoadingState />}
            {isError && <ErrorState onRetry={() => void refetch()} />}
            {!isLoading && !isError && (
                <FlatList
                    data={groups}
                    keyExtractor={(g) => g.id}
                    refreshControl={<RefreshControl refreshing={isLoading} onRefresh={() => void refetch()} />}
                    renderItem={({ item }) => (
                        <GroupRow group={item} onPress={() => router.push(`/groups/${item.id}` as never)} />
                    )}
                    ItemSeparatorComponent={() => <View style={styles.separator} />}
                    ListEmptyComponent={
                        <EmptyState
                            icon="📁"
                            title="No groups yet"
                            message="Create a team, class or department to get started."
                            action={<Button onPress={() => router.push("/groups/create" as never)}>Create Group</Button>}
                        />
                    }
                    contentContainerStyle={groups.length === 0 ? styles.emptyContainer : undefined}
                    showsVerticalScrollIndicator={false}
                />
            )}
        </Screen>
    );
}

const styles = StyleSheet.create({
    searchRow: { flexDirection: "row", gap: spacing.sm, marginBottom: spacing.md },
    searchBox: {
        flex: 1,
        flexDirection: "row",
        alignItems: "center",
        backgroundColor: colors.white,
        borderRadius: radius.pill,
        borderWidth: 1,
        borderColor: colors.border,
        paddingHorizontal: spacing.md,
        height: 44,
        gap: spacing.sm,
    },
    searchInput: { flex: 1, ...typography.body, color: colors.ink, fontSize: 14 },
    filterBtn: {
        height: 44,
        paddingHorizontal: spacing.md,
        borderRadius: radius.pill,
        borderWidth: 1,
        borderColor: colors.border,
        backgroundColor: colors.white,
        alignItems: "center",
        justifyContent: "center",
    },
    filterBtnActive: { backgroundColor: colors.ink, borderColor: colors.ink },
    filterText: { ...typography.body, color: colors.textSecondary, fontSize: 13, fontWeight: "600" },
    filterTextActive: { color: colors.white },
    row: {
        flexDirection: "row",
        alignItems: "center",
        backgroundColor: colors.white,
        borderRadius: radius.lg,
        padding: spacing.md,
        gap: spacing.md,
        ...shadow,
    },
    pressed: { opacity: 0.75 },
    separator: { height: spacing.sm },
    iconWrap: {
        width: 44,
        height: 44,
        borderRadius: radius.md,
        backgroundColor: colors.primaryLight,
        alignItems: "center",
        justifyContent: "center",
    },
    rowInfo: { flex: 1 },
    rowName: { ...typography.body, fontWeight: "600", color: colors.ink, fontSize: 15 },
    rowSub: { ...typography.caption, color: colors.textSecondary, marginTop: 2 },
    rowKind: { ...typography.caption, color: colors.primary, marginTop: 2, fontWeight: "600", textTransform: "uppercase" },
    addBtn: {
        width: 40,
        height: 40,
        borderRadius: 20,
        backgroundColor: colors.primary,
        alignItems: "center",
        justifyContent: "center",
    },
    emptyContainer: { flex: 1 },
});
