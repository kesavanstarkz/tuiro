import { ScrollView, StyleSheet, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { MaterialCommunityIcons } from "@expo/vector-icons";

import { usePayment } from "@/api/hooks";
import { Badge, Button, Card, ErrorState, LoadingState, PageHeader, Screen } from "@/components";
import { colors, radius, spacing, typography } from "@/theme";
import { formatMoney } from "@/utils/currency";

export default function PaymentDetailScreen() {
    const { paymentId } = useLocalSearchParams<{ paymentId: string }>();
    const query = usePayment(paymentId);

    if (query.isLoading) {
        return (
            <Screen>
                <LoadingState />
            </Screen>
        );
    }

    if (query.isError || !query.data) {
        return (
            <Screen>
                <ErrorState onRetry={() => void query.refetch()} />
            </Screen>
        );
    }

    const payment = query.data;

    return (
        <Screen>
            <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
                <PageHeader
                    eyebrow="TRANSACTION RECORD"
                    title="Payment Details"
                    action={
                        <Button variant="secondary" size="sm" onPress={() => router.back()}>
                            Back
                        </Button>
                    }
                />

                <Card style={styles.card}>
                    <View style={styles.headerRow}>
                        <View style={styles.iconBox}>
                            <MaterialCommunityIcons name="cash-check" size={32} color={colors.primary} />
                        </View>
                        <View style={styles.headerInfo}>
                            <Text style={styles.kicker}>FEE PAYMENT</Text>
                            <Text style={styles.amountText}>{formatMoney(payment.amount)}</Text>
                            <Text style={styles.dateText}>Recorded on {payment.payment_date}</Text>
                        </View>
                        <Badge tone="success">COMPLETED</Badge>
                    </View>

                    <View style={styles.table}>
                        <View style={styles.row}>
                            <Text style={styles.label}>Student</Text>
                            <Text style={styles.value}>{payment.student_name ?? "Student"}</Text>
                        </View>
                        <View style={styles.row}>
                            <Text style={styles.label}>Payment Method</Text>
                            <Text style={styles.value}>{payment.payment_method}</Text>
                        </View>
                        <View style={styles.row}>
                            <Text style={styles.label}>Billing Period</Text>
                            <Text style={styles.value}>{payment.billing_period || "General Tuition"}</Text>
                        </View>
                        {Boolean(payment.notes) && (
                            <View style={styles.row}>
                                <Text style={styles.label}>Notes</Text>
                                <Text style={styles.value}>{payment.notes}</Text>
                            </View>
                        )}
                    </View>
                </Card>

                {payment.fee_id ? (
                    <View style={styles.actionWrap}>
                        <Button onPress={() => router.push(`/fees/${payment.fee_id}` as never)}>
                            View associated fee invoice
                        </Button>
                    </View>
                ) : null}
            </ScrollView>
        </Screen>
    );
}

const styles = StyleSheet.create({
    content: {
        gap: spacing.md,
        paddingBottom: spacing.xxl,
        paddingTop: spacing.xs,
    },
    card: {
        gap: spacing.lg,
        padding: spacing.xl,
    },
    headerRow: {
        alignItems: "center",
        borderBottomColor: colors.line,
        borderBottomWidth: 1,
        flexDirection: "row",
        gap: spacing.md,
        paddingBottom: spacing.lg,
    },
    iconBox: {
        alignItems: "center",
        backgroundColor: colors.coralSoft,
        borderRadius: radius.md,
        height: 56,
        justifyContent: "center",
        width: 56,
    },
    headerInfo: {
        flex: 1,
    },
    kicker: {
        ...typography.label,
        color: colors.primary,
    },
    amountText: {
        ...typography.display,
        color: colors.ink,
        fontSize: 28,
        fontWeight: "800",
        marginTop: 2,
    },
    dateText: {
        ...typography.caption,
        marginTop: 2,
    },
    table: {
        gap: spacing.sm,
    },
    row: {
        alignItems: "center",
        flexDirection: "row",
        justifyContent: "space-between",
        paddingVertical: 6,
    },
    label: {
        ...typography.caption,
        color: colors.muted,
    },
    value: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 15,
    },
    actionWrap: {
        marginTop: spacing.sm,
    },
});
