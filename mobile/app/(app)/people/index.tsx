/**
 * People list screen — adapts to org type:
 * Corporate → employees list
 * Education → students/teachers/parents (via legacy v1 screens, linked from here)
 */
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { useState } from "react";
import { ActivityIndicator, FlatList, Pressable, RefreshControl, StyleSheet, Text, TextInput, View } from "react-native";

import { employeesApi, type Employee } from "@/api/platformPeople";
import { Button, Card, EmptyState, ErrorState, PageHeader, Screen } from "@/components";
import { useAuthStore } from "@/store/auth";
import { colors, radius, shadow, spacing, typography } from "@/theme";

function EmployeeRow({ item, onPress }: { item: Employee; onPress: () => void }) {
    const initials = [item.first_name[0], item.last_name?.[0]].filter(Boolean).join("").toUpperCase();
    return (
        <Pressable onPress={onPress} style={({ pressed }) => [styles.row, pressed && styles.pressed]}>
            <View style={styles.avatar}>
                <Text style={styles.avatarText}>{initials}</Text>
            </View>
            <View style={styles.rowInfo}>
                <Text style={styles.rowName} numberOfLines={1}>
                    {item.first_name} {item.last_name}
                </Text>
                <Text style={styles.rowSub} numberOfLines={1}>
                    #{item.employee_number}
                </Text>
            </View>
            <View style={[styles.badge, item.status === "ACTIVE" ? styles.badgeActive : styles.badgeArchived]}>
                <Text style={styles.badgeText}>{item.status}</Text>
            </View>
            <MaterialCommunityIcons name="chevron-right" size={18} color={colors.muted} />
        </Pressable>
    );
}

function EducationPeopleMenu() {
    const items = [
        { label: "Students", icon: "account-school-outline" as const, route: "/(app)/(tabs)/students" },
        { label: "Teachers", icon: "account-tie-outline" as const, route: "/teachers" },
        { label: "Parents", icon: "account-group-outline" as const, route: "/parents" },
    ];
    return (
        <View style={styles.eduMenu}>
            {items.map((item) => (
                <Pressable
                    key={item.label}
                    onPress={() => router.push(item.route as never)}
                    style={({ pressed }) => [styles.eduCard, pressed && styles.pressed]}
                >
                    <MaterialCommunityIcons name={item.icon} size={28} color={colors.primary} />
                    <Text style={styles.eduLabel}>{item.label}</Text>
                    <MaterialCommunityIcons name="chevron-right" size={16} color={colors.muted} />
                </Pressable>
            ))}
        </View>
    );
}

export default function PeopleScreen() {
    const { user } = useAuthStore();
    const [search, setSearch] = useState("");
    const [showArchived, setShowArchived] = useState(false);

    // Heuristic: orgs with type "corporate" or no Education-specific roles use employees
    // In practice, the org's config should drive this; for now we always show employees
    // tab here and link to education sub-screens.
    const isCorporate = user?.role === "OWNER" || user?.role === "ADMIN";

    const { data, isLoading, isError, refetch } = useQuery({
        queryKey: ["employees", search, showArchived],
        queryFn: () => employeesApi.list({ search: search || undefined, status: showArchived ? undefined : "ACTIVE" }),
        enabled: isCorporate,
    });

    const employees = data ?? [];

    return (
        <Screen>
            <PageHeader
                eyebrow="ORGANIZATION"
                title="People"
                right={
                    isCorporate ? (
                        <Pressable
                            onPress={() => router.push("/people/create" as never)}
                            style={styles.addBtn}
                            accessibilityRole="button"
                            accessibilityLabel="Add employee"
                        >
                            <MaterialCommunityIcons name="plus" size={20} color={colors.white} />
                        </Pressable>
                    ) : undefined
                }
            />

            {/* Education people navigation */}
            {!isCorporate && (
                <>
                    <Text style={styles.sectionLabel}>PEOPLE</Text>
                    <EducationPeopleMenu />
                </>
            )}

            {/* Corporate employee list */}
            {isCorporate && (
                <>
                    <View style={styles.searchRow}>
                        <View style={styles.searchBox}>
                            <MaterialCommunityIcons name="magnify" size={18} color={colors.muted} />
                            <TextInput
                                placeholder="Search employees…"
                                placeholderTextColor={colors.muted}
                                value={search}
                                onChangeText={setSearch}
                                style={styles.searchInput}
                                returnKeyType="search"
                                clearButtonMode="while-editing"
                            />
                        </View>
                        <Pressable onPress={() => setShowArchived((v) => !v)} style={[styles.filterBtn, showArchived && styles.filterBtnActive]}>
                            <Text style={[styles.filterText, showArchived && styles.filterTextActive]}>All</Text>
                        </Pressable>
                    </View>

                    {isLoading && (
                        <View style={styles.center}>
                            <ActivityIndicator color={colors.primary} />
                        </View>
                    )}

                    {isError && <ErrorState onRetry={() => void refetch()} />}

                    {!isLoading && !isError && (
                        <FlatList
                            data={employees}
                            keyExtractor={(e) => e.id}
                            refreshControl={<RefreshControl refreshing={isLoading} onRefresh={() => void refetch()} />}
                            renderItem={({ item }) => (
                                <EmployeeRow item={item} onPress={() => router.push(`/people/${item.id}` as never)} />
                            )}
                            ItemSeparatorComponent={() => <View style={styles.separator} />}
                            ListEmptyComponent={
                                <EmptyState
                                    icon="👤"
                                    title="No employees yet"
                                    message="Add your first employee to get started."
                                    action={<Button onPress={() => router.push("/people/create" as never)}>Add Employee</Button>}
                                />
                            }
                            contentContainerStyle={employees.length === 0 ? styles.emptyContainer : undefined}
                            showsVerticalScrollIndicator={false}
                        />
                    )}
                </>
            )}
        </Screen>
    );
}

const styles = StyleSheet.create({
    sectionLabel: { ...typography.label, marginBottom: spacing.xs, marginTop: spacing.sm },
    eduMenu: { gap: spacing.sm },
    eduCard: {
        flexDirection: "row",
        alignItems: "center",
        backgroundColor: colors.white,
        borderRadius: radius.lg,
        padding: spacing.lg,
        gap: spacing.md,
        ...shadow,
    },
    eduLabel: { ...typography.body, fontWeight: "600", color: colors.ink, flex: 1, fontSize: 15 },
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
    },
    pressed: { opacity: 0.75 },
    separator: { height: spacing.sm },
    avatar: {
        width: 44,
        height: 44,
        borderRadius: 22,
        backgroundColor: colors.primaryLight,
        alignItems: "center",
        justifyContent: "center",
    },
    avatarText: { color: colors.primary, fontWeight: "700", fontSize: 15 },
    rowInfo: { flex: 1 },
    rowName: { ...typography.body, fontWeight: "600", color: colors.ink, fontSize: 15 },
    rowSub: { ...typography.caption, color: colors.textSecondary, marginTop: 2 },
    badge: { borderRadius: radius.sm, paddingHorizontal: 8, paddingVertical: 3 },
    badgeActive: { backgroundColor: "#E6F4EA" },
    badgeArchived: { backgroundColor: colors.border },
    badgeText: { fontSize: 11, fontWeight: "700", color: colors.ink },
    addBtn: {
        width: 40,
        height: 40,
        borderRadius: 20,
        backgroundColor: colors.primary,
        alignItems: "center",
        justifyContent: "center",
    },
    center: { paddingVertical: spacing.xl, alignItems: "center" },
    emptyContainer: { flex: 1 },
});
