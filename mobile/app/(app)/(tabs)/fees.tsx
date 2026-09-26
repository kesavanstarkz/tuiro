import { useMemo } from "react";
import { FlatList, StyleSheet, Text, View } from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { router } from "expo-router";

import { useGroupFeeAttention } from "@/api/hooks";
import { Avatar, Badge, EmptyState, ErrorState, IconButton, LoadingState, PageHeader, Screen } from "@/components";
import { colors, radius, spacing, typography } from "@/theme";

const tone: Record<string, "success" | "warning" | "danger" | "neutral"> = {
    PAID: "success",
    PARTIAL: "warning",
    OVERDUE: "danger",
    PENDING: "warning",
};

const money = (value: string | number) =>
    new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(
        Number(value) || 0
    );

export default function FeesScreen() {
    const query = useGroupFeeAttention();

    const rawFees = query.data ?? [];
    const sortedFees = useMemo(() => {
        return [...rawFees].sort((a, b) => {
            if (a.status === "OVERDUE" && b.status !== "OVERDUE") return -1;
            if (b.status === "OVERDUE" && a.status !== "OVERDUE") return 1;
            return a.due_date.localeCompare(b.due_date);
        });
    }, [rawFees]);

    const outstanding = rawFees.reduce((total, fee) => total + Number(fee.outstanding_amount || 0), 0);
    const overdue = rawFees.filter((fee) => fee.status === "OVERDUE");

    if (query.isLoading) return <Screen><LoadingState /></Screen>;
    if (query.isError) return <Screen><ErrorState onRetry={() => void query.refetch()} /></Screen>;

    return (
        <Screen>
            <PageHeader
                eyebrow="FINANCE"
                title="Fees"
                right={
                    <IconButton
                        label="Create fee"
                        onPress={() => router.push("/(app)/fees/collect")}
                        tone="primary"
                        icon={<MaterialCommunityIcons name="plus" color="#fff" size={22} />}
                    />
                }
            />

            {/* Total Outstanding Hero Card */}
            <View style={styles.balance}>
                <Text style={styles.balanceLabel}>TOTAL OUTSTANDING</Text>
                <Text style={styles.balanceAmount}>{money(outstanding)}</Text>
                <View style={styles.balanceFooter}>
                    <Text style={styles.balanceMeta}>
                        {rawFees.length} student payment{rawFees.length === 1 ? "" : "s"} need attention
                    </Text>
                    {overdue.length > 0 && (
                        <View style={styles.overdue}>
                            <MaterialCommunityIcons name="alert-circle-outline" color={colors.red} size={15} />
                            <Text style={styles.overdueText}>{overdue.length} overdue</Text>
                        </View>
                    )}
                </View>
            </View>

            {/* Follow-up Queue */}
            <View style={styles.section}>
                <Text style={styles.sectionTitle}>Follow-up queue</Text>
                <Text style={styles.sectionMeta}>Sorted by urgency</Text>
            </View>

            <FlatList
                showsVerticalScrollIndicator={false}
                refreshing={query.isRefetching}
                onRefresh={() => void query.refetch()}
                contentContainerStyle={styles.list}
                data={sortedFees}
                keyExtractor={(item) => `${item.fee_id}-${item.student_id}`}
                ListEmptyComponent={
                    <EmptyState
                        icon="🎉"
                        title="Fees are settled"
                        message="No follow-up needed right now."
                    />
                }
                renderItem={({ item, index }) => (
                    <View style={[styles.row, index === 0 && item.status === "OVERDUE" && styles.overdueLeadRow]}>
                        <Avatar name={item.student_name} size={42} />
                        <View style={styles.copy}>
                            <Text style={styles.name}>{item.student_name}</Text>
                            <Text style={styles.meta}>
                                {item.source} fee · Due {item.due_date}
                            </Text>
                        </View>
                        <View style={styles.amountBlock}>
                            <Text style={styles.amount}>{money(item.outstanding_amount)}</Text>
                            <Badge tone={tone[item.status] ?? "neutral"}>{item.status}</Badge>
                        </View>
                    </View>
                )}
            />
        </Screen>
    );
}

const styles = StyleSheet.create({
    balance: {
        backgroundColor: colors.ink,
        borderRadius: radius.lg,
        padding: spacing.xl,
    },
    balanceLabel: {
        color: colors.primary,
        fontSize: 11,
        fontWeight: "800",
        letterSpacing: 1.2,
    },
    balanceAmount: {
        color: colors.white,
        fontFamily: typography.display.fontFamily,
        fontSize: 42,
        fontWeight: "800",
        letterSpacing: -1,
        marginTop: spacing.xs,
    },
    balanceFooter: {
        alignItems: "center",
        flexDirection: "row",
        justifyContent: "space-between",
        marginTop: spacing.lg,
    },
    balanceMeta: {
        color: "#B4C0B8",
        fontSize: 13,
    },
    overdue: {
        alignItems: "center",
        backgroundColor: colors.redSoft,
        borderRadius: radius.pill,
        flexDirection: "row",
        gap: 4,
        paddingHorizontal: spacing.sm,
        paddingVertical: 4,
    },
    overdueText: {
        color: colors.red,
        fontSize: 12,
        fontWeight: "800",
    },
    section: {
        alignItems: "baseline",
        flexDirection: "row",
        justifyContent: "space-between",
        marginTop: spacing.lg,
    },
    sectionTitle: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 18,
    },
    sectionMeta: {
        ...typography.caption,
    },
    list: {
        flexGrow: 1,
        gap: spacing.xs,
        paddingBottom: spacing.xxl,
        paddingTop: spacing.sm,
    },
    row: {
        alignItems: "center",
        backgroundColor: colors.white,
        borderColor: colors.line,
        borderRadius: radius.md,
        borderWidth: 1,
        flexDirection: "row",
        padding: spacing.md,
    },
    overdueLeadRow: {
        borderLeftColor: colors.red,
        borderLeftWidth: 4,
    },
    copy: {
        flex: 1,
        marginHorizontal: spacing.md,
    },
    name: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 15,
    },
    meta: {
        ...typography.caption,
        marginTop: 2,
    },
    amountBlock: {
        alignItems: "flex-end",
        gap: spacing.xs,
    },
    amount: {
        color: colors.ink,
        fontSize: 16,
        fontWeight: "800",
    },
});
