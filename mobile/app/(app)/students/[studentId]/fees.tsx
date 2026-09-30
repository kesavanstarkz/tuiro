import { FlatList, Pressable, StyleSheet, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";

import { useStudent, useStudentFees } from "@/api/hooks";
import { Badge, Button, Card, EmptyState, ErrorState, LoadingState, PageHeader, Screen } from "@/components";
import { colors, radius, spacing, typography } from "@/theme";
import { formatMoney } from "@/utils/currency";

export default function StudentFeesScreen() {
    const { studentId } = useLocalSearchParams<{ studentId: string }>();
    const studentQuery = useStudent(studentId);
    const feesQuery = useStudentFees(studentId);

    if (studentQuery.isLoading || feesQuery.isLoading) {
        return (
            <Screen>
                <LoadingState />
            </Screen>
        );
    }

    if (studentQuery.isError || !studentQuery.data) {
        return (
            <Screen>
                <ErrorState onRetry={() => {
                    void studentQuery.refetch();
                    void feesQuery.refetch();
                }} />
            </Screen>
        );
    }

    const student = studentQuery.data;
    const name = `${student.first_name} ${student.last_name}`.trim();
    const fees = feesQuery.data ?? [];

    const totalDue = fees.reduce((sum, f) => sum + Number(f.amount || 0), 0);
    const totalPaid = fees.reduce((sum, f) => sum + Number(f.paid_amount || 0), 0);
    const outstanding = Math.max(0, totalDue - totalPaid);

    return (
        <Screen>
            <FlatList
                contentContainerStyle={styles.content}
                data={fees}
                keyExtractor={(item) => item.id}
                showsVerticalScrollIndicator={false}
                ListHeaderComponent={
                    <View style={styles.headerWrap}>
                        <PageHeader
                            eyebrow="STUDENT BILLING"
                            title={`${name}'s Fees`}
                            action={
                                <Button variant="secondary" size="sm" onPress={() => router.back()}>
                                    Back
                                </Button>
                            }
                        />

                        <Card style={styles.summaryCard}>
                            <View style={styles.summaryRow}>
                                <View style={styles.summaryCol}>
                                    <Text style={styles.summaryLabel}>Total Billed</Text>
                                    <Text style={styles.summaryValue}>{formatMoney(totalDue)}</Text>
                                </View>
                                <View style={styles.summaryDivider} />
                                <View style={styles.summaryCol}>
                                    <Text style={styles.summaryLabel}>Outstanding</Text>
                                    <Text style={[styles.summaryValue, outstanding > 0 ? styles.dueValue : null]}>
                                        {formatMoney(outstanding)}
                                    </Text>
                                </View>
                                <View style={styles.summaryDivider} />
                                <View style={styles.summaryCol}>
                                    <Text style={styles.summaryLabel}>Paid</Text>
                                    <Text style={styles.summaryValue}>{formatMoney(totalPaid)}</Text>
                                </View>
                            </View>
                        </Card>

                        <Text style={styles.sectionTitle}>Fee Invoices ({fees.length})</Text>
                    </View>
                }
                ListEmptyComponent={
                    <EmptyState
                        icon="💳"
                        title="No fee records"
                        message="There are currently no fees recorded or generated for this student."
                        action={<Button onPress={() => router.push("/(app)/fees/collect" as never)}>Create Fee</Button>}
                    />
                }
                renderItem={({ item }) => (
                    <Pressable onPress={() => router.push(`/fees/${item.id}` as never)}>
                        <Card style={styles.feeCard}>
                            <View style={styles.feeTop}>
                                <View style={styles.feeInfo}>
                                    <Text style={styles.periodText}>{item.billing_period}</Text>
                                    <Text style={styles.dueText}>Due {item.due_date}</Text>
                                </View>
                                <Badge tone={item.status === "PAID" ? "success" : item.status === "OVERDUE" ? "danger" : "warning"}>
                                    {item.status}
                                </Badge>
                            </View>

                            <View style={styles.feeBottom}>
                                <Text style={styles.amountLabel}>
                                    Outstanding: <Text style={styles.amountHighlight}>{formatMoney(item.outstanding_amount ?? item.amount)}</Text>
                                </Text>
                                <Text style={styles.totalText}>Total: {formatMoney(item.amount)}</Text>
                            </View>
                        </Card>
                    </Pressable>
                )}
            />
        </Screen>
    );
}

const styles = StyleSheet.create({
    content: {
        gap: spacing.sm,
        paddingBottom: spacing.xxl,
        paddingTop: spacing.xs,
    },
    headerWrap: {
        gap: spacing.md,
        marginBottom: spacing.xs,
    },
    summaryCard: {
        padding: spacing.md,
    },
    summaryRow: {
        alignItems: "center",
        flexDirection: "row",
        justifyContent: "space-around",
    },
    summaryCol: {
        alignItems: "center",
        flex: 1,
    },
    summaryDivider: {
        backgroundColor: colors.line,
        height: 28,
        width: 1,
    },
    summaryLabel: {
        ...typography.caption,
        color: colors.muted,
    },
    summaryValue: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 16,
        marginTop: 2,
    },
    dueValue: {
        color: colors.red,
    },
    sectionTitle: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 16,
        marginTop: spacing.sm,
    },
    feeCard: {
        gap: spacing.sm,
        padding: spacing.md,
    },
    feeTop: {
        alignItems: "center",
        flexDirection: "row",
        justifyContent: "space-between",
    },
    feeInfo: {
        flex: 1,
    },
    periodText: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 15,
    },
    dueText: {
        ...typography.caption,
        marginTop: 2,
    },
    feeBottom: {
        alignItems: "center",
        borderTopColor: colors.line,
        borderTopWidth: 1,
        flexDirection: "row",
        justifyContent: "space-between",
        paddingTop: spacing.xs,
    },
    amountLabel: {
        ...typography.caption,
        color: colors.muted,
    },
    amountHighlight: {
        color: colors.ink,
        fontWeight: "700",
    },
    totalText: {
        ...typography.caption,
        color: colors.muted,
    },
});
