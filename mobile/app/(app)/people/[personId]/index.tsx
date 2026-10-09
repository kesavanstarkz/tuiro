/**
 * Employee detail screen — view, edit and archive a corporate employee record.
 */
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { employeesApi } from "@/api/platformPeople";
import { Card, PageHeader, Screen, SectionHeader } from "@/components";
import { colors, radius, spacing, typography } from "@/theme";

function InfoRow({ label, value }: { label: string; value: string | null | undefined }) {
    if (!value) return null;
    return (
        <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>{label}</Text>
            <Text style={styles.infoValue}>{value}</Text>
        </View>
    );
}

export default function PersonDetailScreen() {
    const { personId } = useLocalSearchParams<{ personId: string }>();
    const qc = useQueryClient();

    const { data: employee, isLoading, isError, refetch } = useQuery({
        queryKey: ["employee", personId],
        queryFn: () => employeesApi.get(personId),
        enabled: !!personId,
    });

    const archiveMutation = useMutation({
        mutationFn: () => employeesApi.archive(personId),
        onSuccess: () => {
            void qc.invalidateQueries({ queryKey: ["employees"] });
            router.back();
        },
    });

    const handleArchive = () => {
        Alert.alert(
            "Archive Employee",
            "This employee will be hidden from active lists. You can restore them later.",
            [
                { text: "Cancel", style: "cancel" },
                {
                    text: "Archive",
                    style: "destructive",
                    onPress: () => archiveMutation.mutate(),
                },
            ],
        );
    };

    if (isLoading) {
        return (
            <Screen>
                <View style={styles.loadingRow}>
                    <View style={[styles.skeletonLine, { width: "60%" }]} />
                    <View style={[styles.skeletonLine, { width: "40%", height: 14 }]} />
                </View>
            </Screen>
        );
    }

    if (isError || !employee) {
        return (
            <Screen>
                <Text style={styles.errorText}>Employee not found.</Text>
                <Pressable onPress={() => void refetch()} style={styles.retryBtn}>
                    <Text style={styles.retryText}>Retry</Text>
                </Pressable>
            </Screen>
        );
    }

    const fullName = [employee.first_name, employee.last_name].filter(Boolean).join(" ");
    const initials = [employee.first_name[0], employee.last_name?.[0]].filter(Boolean).join("").toUpperCase();

    return (
        <Screen>
            <PageHeader
                eyebrow="EMPLOYEE"
                title={fullName}
                right={
                    <Pressable onPress={() => router.push(`/people/${personId}/edit` as never)} style={styles.editBtn} accessibilityLabel="Edit employee">
                        <MaterialCommunityIcons name="pencil-outline" size={18} color={colors.ink} />
                    </Pressable>
                }
            />

            <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.content}>
                {/* Avatar + status */}
                <View style={styles.heroCard}>
                    <View style={styles.avatarLarge}>
                        <Text style={styles.avatarText}>{initials}</Text>
                    </View>
                    <Text style={styles.heroName}>{fullName}</Text>
                    <View style={[styles.badge, employee.status === "ACTIVE" ? styles.badgeActive : styles.badgeArchived]}>
                        <Text style={styles.badgeText}>{employee.status}</Text>
                    </View>
                </View>

                <SectionHeader title="DETAILS" />
                <Card>
                    <InfoRow label="Employee #" value={employee.employee_number} />
                    <InfoRow label="Email" value={employee.email} />
                    <InfoRow label="Phone" value={employee.phone} />
                    <InfoRow label="Employment Type" value={employee.employment_type} />
                    <InfoRow label="Start Date" value={employee.start_date} />
                </Card>

                {employee.status === "ACTIVE" && (
                    <Pressable onPress={handleArchive} style={styles.archiveBtn} accessibilityRole="button">
                        <MaterialCommunityIcons name="archive-outline" size={18} color={colors.danger} />
                        <Text style={styles.archiveText}>Archive Employee</Text>
                    </Pressable>
                )}
            </ScrollView>
        </Screen>
    );
}

const styles = StyleSheet.create({
    content: { gap: spacing.md, paddingBottom: spacing.xxl },
    heroCard: { alignItems: "center", paddingVertical: spacing.xl, gap: spacing.sm },
    avatarLarge: {
        width: 80,
        height: 80,
        borderRadius: 40,
        backgroundColor: colors.primaryLight,
        alignItems: "center",
        justifyContent: "center",
    },
    avatarText: { color: colors.primary, fontWeight: "700", fontSize: 28 },
    heroName: { ...typography.display, fontSize: 20, fontWeight: "700", color: colors.ink, textAlign: "center" },
    badge: { borderRadius: radius.sm, paddingHorizontal: 10, paddingVertical: 4 },
    badgeActive: { backgroundColor: "#E6F4EA" },
    badgeArchived: { backgroundColor: colors.border },
    badgeText: { fontSize: 12, fontWeight: "700", color: colors.ink },
    infoRow: {
        flexDirection: "row",
        justifyContent: "space-between",
        paddingVertical: spacing.sm,
        borderBottomWidth: 1,
        borderBottomColor: colors.border,
    },
    infoLabel: { ...typography.caption, color: colors.textSecondary, flex: 1 },
    infoValue: { ...typography.body, color: colors.ink, fontWeight: "500", flex: 2, textAlign: "right" },
    editBtn: {
        width: 40,
        height: 40,
        borderRadius: 20,
        backgroundColor: colors.surface,
        alignItems: "center",
        justifyContent: "center",
        borderWidth: 1,
        borderColor: colors.border,
    },
    archiveBtn: {
        flexDirection: "row",
        alignItems: "center",
        justifyContent: "center",
        gap: spacing.sm,
        paddingVertical: spacing.md,
        marginTop: spacing.md,
        borderRadius: radius.lg,
        borderWidth: 1,
        borderColor: colors.danger,
    },
    archiveText: { color: colors.danger, fontWeight: "600", fontSize: 15 },
    loadingRow: { paddingTop: spacing.xl, gap: spacing.md },
    skeletonLine: { height: 20, backgroundColor: colors.border, borderRadius: radius.sm },
    errorText: { ...typography.body, color: colors.textSecondary, textAlign: "center", marginTop: spacing.xl },
    retryBtn: { alignSelf: "center", marginTop: spacing.md, padding: spacing.sm },
    retryText: { color: colors.primary, fontWeight: "600" },
});
