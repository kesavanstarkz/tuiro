import { useState } from "react";
import { Alert, KeyboardAvoidingView, Modal, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { MaterialCommunityIcons } from "@expo/vector-icons";

import { useFee } from "@/api/hooks";
import { paymentsApi } from "@/api/payments";
import { Badge, Button, Card, ErrorState, LoadingState, PageHeader, Screen } from "@/components";
import { colors, radius, spacing, typography } from "@/theme";
import { formatMoney } from "@/utils/currency";

export default function FeeDetailScreen() {
    const { feeId } = useLocalSearchParams<{ feeId: string }>();
    const query = useFee(feeId);

    const [modalVisible, setModalVisible] = useState(false);
    const [amount, setAmount] = useState("");
    const [method, setMethod] = useState("CASH");
    const [reference, setReference] = useState("");
    const [notes, setNotes] = useState("");
    const [submitting, setSubmitting] = useState(false);

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

    const fee = query.data;
    const totalAmount = Number(fee.amount || 0);
    const paidAmount = Number(fee.paid_amount || 0);
    const outstanding = Math.max(0, Number(fee.outstanding_amount ?? (totalAmount - paidAmount)));

    const handleRecordPayment = async () => {
        const num = parseFloat(amount);
        if (isNaN(num) || num <= 0) {
            return Alert.alert("Invalid amount", "Please enter a valid payment amount.");
        }
        if (num > outstanding) {
            return Alert.alert("Amount exceeds balance", `Payment cannot exceed the outstanding balance of ${formatMoney(outstanding)}.`);
        }

        try {
            setSubmitting(true);
            await paymentsApi.create({
                fee_id: fee.id,
                amount: num,
                payment_method: method,
                reference: reference.trim() || undefined,
                notes: notes.trim() || undefined,
            });
            setModalVisible(false);
            setAmount("");
            setReference("");
            setNotes("");
            void query.refetch();
            Alert.alert("Payment Recorded", `Payment of ${formatMoney(num)} has been recorded.`);
        } catch {
            Alert.alert("Payment Error", "Failed to record payment. Please try again.");
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <Screen>
            <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
                <PageHeader
                    eyebrow="FEE INVOICE"
                    title={fee.billing_period}
                    action={
                        <Button variant="secondary" size="sm" onPress={() => router.back()}>
                            Back
                        </Button>
                    }
                />

                <Card style={styles.card}>
                    <View style={styles.headerRow}>
                        <View style={styles.iconBox}>
                            <MaterialCommunityIcons name="receipt" size={32} color={colors.primary} />
                        </View>
                        <View style={styles.headerInfo}>
                            <Text style={styles.studentName}>{fee.student_name}</Text>
                            <Text style={styles.periodText}>{fee.billing_period}</Text>
                            <Text style={styles.dueText}>Due date: {fee.due_date}</Text>
                        </View>
                        <Badge tone={fee.status === "PAID" ? "success" : fee.status === "OVERDUE" ? "danger" : "warning"}>
                            {fee.status}
                        </Badge>
                    </View>

                    <View style={styles.amountsRow}>
                        <View style={styles.amountCol}>
                            <Text style={styles.amountLabel}>Total Billed</Text>
                            <Text style={styles.amountVal}>{formatMoney(totalAmount)}</Text>
                        </View>
                        <View style={styles.divider} />
                        <View style={styles.amountCol}>
                            <Text style={styles.amountLabel}>Paid to Date</Text>
                            <Text style={styles.amountVal}>{formatMoney(paidAmount)}</Text>
                        </View>
                        <View style={styles.divider} />
                        <View style={styles.amountCol}>
                            <Text style={styles.amountLabel}>Outstanding</Text>
                            <Text style={[styles.amountVal, outstanding > 0 ? styles.dueVal : null]}>
                                {formatMoney(outstanding)}
                            </Text>
                        </View>
                    </View>
                </Card>

                {outstanding > 0 ? (
                    <View style={styles.actionWrap}>
                        <Button
                            onPress={() => {
                                setAmount(String(outstanding));
                                setModalVisible(true);
                            }}
                        >
                            Record Payment ({formatMoney(outstanding)})
                        </Button>
                    </View>
                ) : (
                    <Card style={styles.settledCard}>
                        <MaterialCommunityIcons name="check-circle" size={24} color={colors.green} />
                        <Text style={styles.settledText}>This fee has been fully settled.</Text>
                    </Card>
                )}

                <View style={styles.secondaryActions}>
                    <Button variant="secondary" onPress={() => router.push("/(app)/receipts" as never)}>
                        View Receipts
                    </Button>
                </View>
            </ScrollView>

            {/* Record Payment Modal */}
            <Modal visible={modalVisible} transparent animationType="slide" onRequestClose={() => setModalVisible(false)}>
                <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={styles.modalOverlay}>
                    <View style={styles.sheet}>
                        <View style={styles.sheetHeader}>
                            <Text style={styles.sheetTitle}>Record Fee Payment</Text>
                            <Pressable onPress={() => setModalVisible(false)}>
                                <MaterialCommunityIcons name="close" size={24} color={colors.ink} />
                            </Pressable>
                        </View>

                        <Text style={styles.sheetSubtitle}>
                            Student: <Text style={styles.bold}>{fee.student_name}</Text> · Balance: {formatMoney(outstanding)}
                        </Text>

                        <View style={styles.formGroup}>
                            <Text style={styles.inputLabel}>Amount to Pay</Text>
                            <TextInput
                                style={styles.input}
                                value={amount}
                                onChangeText={setAmount}
                                placeholder="0.00"
                                placeholderTextColor={colors.muted}
                                keyboardType="decimal-pad"
                            />
                        </View>

                        <View style={styles.formGroup}>
                            <Text style={styles.inputLabel}>Payment Method</Text>
                            <View style={styles.methodRow}>
                                {["CASH", "UPI", "BANK_TRANSFER", "CARD"].map((m) => (
                                    <Pressable
                                        key={m}
                                        style={[styles.methodChip, method === m && styles.methodChipActive]}
                                        onPress={() => setMethod(m)}
                                    >
                                        <Text style={[styles.methodText, method === m && styles.methodTextActive]}>
                                            {m === "BANK_TRANSFER" ? "BANK" : m}
                                        </Text>
                                    </Pressable>
                                ))}
                            </View>
                        </View>

                        <View style={styles.formGroup}>
                            <Text style={styles.inputLabel}>Transaction Reference / Note (Optional)</Text>
                            <TextInput
                                style={styles.input}
                                value={reference}
                                onChangeText={setReference}
                                placeholder="UPI ref / Cheque # / Notes"
                                placeholderTextColor={colors.muted}
                            />
                        </View>

                        <View style={styles.sheetActions}>
                            <Button variant="secondary" onPress={() => setModalVisible(false)}>
                                Cancel
                            </Button>
                            <Button disabled={submitting || !amount.trim()} onPress={() => void handleRecordPayment()}>
                                {submitting ? "Recording..." : "Confirm Payment"}
                            </Button>
                        </View>
                    </View>
                </KeyboardAvoidingView>
            </Modal>
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
    studentName: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 18,
    },
    periodText: {
        ...typography.caption,
        color: colors.muted,
        marginTop: 2,
    },
    dueText: {
        ...typography.caption,
        marginTop: 2,
    },
    amountsRow: {
        alignItems: "center",
        backgroundColor: colors.surface,
        borderRadius: radius.sm,
        flexDirection: "row",
        justifyContent: "space-around",
        paddingVertical: spacing.md,
    },
    amountCol: {
        alignItems: "center",
        flex: 1,
    },
    divider: {
        backgroundColor: colors.line,
        height: 32,
        width: 1,
    },
    amountLabel: {
        ...typography.caption,
        color: colors.muted,
    },
    amountVal: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 16,
        marginTop: 2,
    },
    dueVal: {
        color: colors.red,
    },
    actionWrap: {
        marginTop: spacing.xs,
    },
    settledCard: {
        alignItems: "center",
        backgroundColor: colors.surface,
        flexDirection: "row",
        gap: spacing.sm,
        justifyContent: "center",
        padding: spacing.md,
    },
    settledText: {
        ...typography.body,
        color: colors.green,
        fontWeight: "600",
    },
    secondaryActions: {
        marginTop: spacing.xs,
    },
    modalOverlay: {
        backgroundColor: "rgba(20,28,40,.45)",
        flex: 1,
        justifyContent: "flex-end",
    },
    sheet: {
        backgroundColor: colors.paper,
        borderTopLeftRadius: 28,
        borderTopRightRadius: 28,
        gap: spacing.md,
        padding: spacing.xl,
    },
    sheetHeader: {
        alignItems: "center",
        flexDirection: "row",
        justifyContent: "space-between",
    },
    sheetTitle: {
        ...typography.display,
        fontSize: 20,
    },
    sheetSubtitle: {
        ...typography.caption,
        color: colors.muted,
    },
    bold: {
        color: colors.ink,
        fontWeight: "700",
    },
    formGroup: {
        gap: 6,
    },
    inputLabel: {
        ...typography.caption,
        color: colors.muted,
    },
    input: {
        backgroundColor: colors.surface,
        borderColor: colors.line,
        borderRadius: radius.sm,
        borderWidth: 1,
        color: colors.ink,
        fontSize: 16,
        paddingHorizontal: spacing.md,
        paddingVertical: 10,
    },
    methodRow: {
        flexDirection: "row",
        flexWrap: "wrap",
        gap: spacing.xs,
    },
    methodChip: {
        backgroundColor: colors.surface,
        borderColor: colors.line,
        borderRadius: radius.pill,
        borderWidth: 1,
        paddingHorizontal: spacing.md,
        paddingVertical: 8,
    },
    methodChipActive: {
        backgroundColor: colors.primary,
        borderColor: colors.primary,
    },
    methodText: {
        ...typography.caption,
        color: colors.ink,
        fontWeight: "600",
    },
    methodTextActive: {
        color: colors.white,
    },
    sheetActions: {
        flexDirection: "row",
        gap: spacing.sm,
        justifyContent: "flex-end",
        marginTop: spacing.md,
    },
});
