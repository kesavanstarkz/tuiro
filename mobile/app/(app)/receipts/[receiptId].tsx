import { Alert, ScrollView, Share, StyleSheet, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";

import { receiptsApi } from "@/api/receipts";
import { Badge, Button, Card, ErrorState, LoadingState, PageHeader, Screen } from "@/components";
import { colors, radius, spacing, typography } from "@/theme";
import { formatMoney } from "@/utils/currency";

export default function ReceiptDetailScreen() {
    const { receiptId } = useLocalSearchParams<{ receiptId: string }>();
    const query = useQuery({
        queryKey: ["receipt", receiptId],
        queryFn: () => receiptsApi.get(receiptId),
        enabled: Boolean(receiptId),
    });

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

    const receipt = query.data as {
        id: string;
        receipt_number: string;
        issued_at: string;
        amount: number | string;
        payment_method: string;
        transaction_reference?: string;
        student_name: string;
        billing_period: string;
        notes?: string;
    };

    const handleShare = async () => {
        try {
            await Share.share({
                title: `Fee Receipt #${receipt.receipt_number}`,
                message: `Tuiro Tuition Fee Receipt #${receipt.receipt_number}\nStudent: ${receipt.student_name}\nAmount Paid: ${formatMoney(receipt.amount)}\nBilling Period: ${receipt.billing_period}\nPayment Method: ${receipt.payment_method}\nDate: ${receipt.issued_at}`,
            });
        } catch {
            Alert.alert("Unable to share", "Could not open share dialogue.");
        }
    };

    return (
        <Screen>
            <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
                <PageHeader
                    eyebrow="OFFICIAL RECEIPT"
                    title={`Receipt #${receipt.receipt_number}`}
                    action={
                        <Button variant="secondary" size="sm" onPress={() => router.back()}>
                            Back
                        </Button>
                    }
                />

                <Card style={styles.receiptCard}>
                    <View style={styles.receiptHeader}>
                        <View style={styles.iconBox}>
                            <MaterialCommunityIcons name="check-decagram" size={32} color={colors.primary} />
                        </View>
                        <View style={styles.headerInfo}>
                            <Text style={styles.receiptKicker}>PAYMENT RECEIVED</Text>
                            <Text style={styles.amountText}>{formatMoney(receipt.amount)}</Text>
                            <Text style={styles.receiptDate}>{receipt.issued_at ? String(receipt.issued_at).slice(0, 10) : ""}</Text>
                        </View>
                        <Badge tone="success">PAID</Badge>
                    </View>

                    <View style={styles.table}>
                        <View style={styles.row}>
                            <Text style={styles.label}>Receipt Number</Text>
                            <Text style={styles.value}>#{receipt.receipt_number}</Text>
                        </View>
                        <View style={styles.row}>
                            <Text style={styles.label}>Student</Text>
                            <Text style={styles.value}>{receipt.student_name}</Text>
                        </View>
                        <View style={styles.row}>
                            <Text style={styles.label}>Billing Period</Text>
                            <Text style={styles.value}>{receipt.billing_period || "General Tuition"}</Text>
                        </View>
                        <View style={styles.row}>
                            <Text style={styles.label}>Payment Method</Text>
                            <Text style={styles.value}>{receipt.payment_method}</Text>
                        </View>
                        {Boolean(receipt.transaction_reference) && (
                            <View style={styles.row}>
                                <Text style={styles.label}>Reference</Text>
                                <Text style={styles.value}>{receipt.transaction_reference}</Text>
                            </View>
                        )}
                        {Boolean(receipt.notes) && (
                            <View style={styles.row}>
                                <Text style={styles.label}>Notes</Text>
                                <Text style={styles.value}>{receipt.notes}</Text>
                            </View>
                        )}
                    </View>
                </Card>

                <View style={styles.actions}>
                    <Button onPress={handleShare}>Share receipt</Button>
                </View>
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
    receiptCard: {
        gap: spacing.lg,
        padding: spacing.xl,
    },
    receiptHeader: {
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
    receiptKicker: {
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
    receiptDate: {
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
    actions: {
        marginTop: spacing.sm,
    },
});
