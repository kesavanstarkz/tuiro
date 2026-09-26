import { useState } from "react";
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";

import { useCreateGroupFee, useGroups, useStudents } from "@/api/hooks";
import { Button, Card, EmptyState, ErrorState, LoadingState, PageHeader, Screen, TuiroInput } from "@/components";
import { colors, radius, spacing, typography } from "@/theme";

export default function CollectFeeScreen() {
    const groups = useGroups();
    const students = useStudents();
    const create = useCreateGroupFee();

    const [target, setTarget] = useState<string>("");
    const [individual, setIndividual] = useState(false);
    const [amount, setAmount] = useState("");
    const [dueDate, setDueDate] = useState("");

    if (groups.isLoading || students.isLoading) return <Screen><LoadingState /></Screen>;
    if (groups.isError || students.isError) {
        return (
            <Screen>
                <ErrorState
                    onRetry={() => {
                        void groups.refetch();
                        void students.refetch();
                    }}
                />
            </Screen>
        );
    }

    const groupList = groups.data ?? [];
    const studentList = students.data ?? [];

    if (!individual && groupList.length === 0) {
        return (
            <Screen>
                <PageHeader eyebrow="FINANCE" title="Create fee" />
                <EmptyState
                    icon="🏫"
                    title="Create a class first"
                    message="Group fees require a class roster. Add your first batch before creating a fee."
                    action={<Button onPress={() => router.push("/(app)/classes")}>Create a class</Button>}
                />
            </Screen>
        );
    }

    const submit = async () => {
        if (!target || !Number(amount) || !dueDate) {
            return Alert.alert("Complete the fee", "Choose a group (or student), amount, and due date.");
        }
        try {
            await create.mutateAsync(
                individual
                    ? { student_id: target, amount: Number(amount), due_date: dueDate }
                    : { group_id: target, amount: Number(amount), due_date: dueDate }
            );
            Alert.alert(
                "Fee created",
                individual ? "This is an individual charge." : "It now applies to all active group members.",
                [{ text: "OK", onPress: () => router.back() }]
            );
        } catch {
            Alert.alert("Could not create fee", "Please check the entered details.");
        }
    };

    const choices = individual ? studentList : groupList;

    return (
        <Screen>
            <ScrollView contentContainerStyle={styles.list} showsVerticalScrollIndicator={false}>
                <PageHeader eyebrow="FINANCE" title="Create fee" />
                <Text style={styles.help}>Start with a group batch. Use the individual path only for a one-off charge.</Text>

                {/* Scope selector */}
                <View style={styles.mode}>
                    <Button
                        variant={individual ? "secondary" : "primary"}
                        onPress={() => {
                            setIndividual(false);
                            setTarget("");
                        }}
                    >
                        Group
                    </Button>
                    <Button
                        variant={individual ? "primary" : "secondary"}
                        onPress={() => {
                            setIndividual(true);
                            setTarget("");
                        }}
                    >
                        Individual student
                    </Button>
                </View>

                <Text style={styles.label}>{individual ? "Choose student" : "Choose group / batch"}</Text>

                <View style={styles.choicesWrap}>
                    {choices.map((item) => {
                        const isSelected = target === item.id;
                        const title = "name" in item ? item.name : `${item.first_name} ${item.last_name}`;
                        const meta = "student_count" in item ? `${item.student_count} active students` : item.grade ?? "Student";

                        return (
                            <Pressable key={item.id} onPress={() => setTarget(item.id)}>
                                <Card style={[styles.choiceCard, isSelected && styles.choiceSelected]}>
                                    <View style={styles.choiceCopy}>
                                        <Text style={[styles.choiceName, isSelected && styles.choiceNameSelected]}>
                                            {title}
                                        </Text>
                                        <Text style={styles.choiceMeta}>{meta}</Text>
                                    </View>
                                    <View style={[styles.radio, isSelected && styles.radioActive]}>
                                        {isSelected && <View style={styles.radioInner} />}
                                    </View>
                                </Card>
                            </Pressable>
                        );
                    })}
                </View>

                <View style={styles.inputsSection}>
                    <TuiroInput
                        label="Amount (₹)"
                        keyboardType="decimal-pad"
                        value={amount}
                        onChangeText={setAmount}
                        placeholder="2500"
                    />
                    <TuiroInput
                        label="Due date (YYYY-MM-DD)"
                        value={dueDate}
                        onChangeText={setDueDate}
                        placeholder="2026-10-01"
                    />
                </View>

                <Button disabled={create.isPending || !target} onPress={() => void submit()}>
                    {create.isPending ? "Creating..." : "Create fee"}
                </Button>
            </ScrollView>
        </Screen>
    );
}

const styles = StyleSheet.create({
    list: {
        gap: spacing.md,
        paddingBottom: spacing.xxl,
    },
    help: {
        ...typography.body,
        color: colors.muted,
        marginTop: -spacing.xs,
    },
    mode: {
        flexDirection: "row",
        gap: spacing.sm,
        marginTop: spacing.xs,
    },
    label: {
        ...typography.label,
        color: colors.ink,
        marginTop: spacing.sm,
    },
    choicesWrap: {
        gap: spacing.xs,
    },
    choiceCard: {
        alignItems: "center",
        flexDirection: "row",
        padding: spacing.md,
    },
    choiceSelected: {
        borderColor: colors.primary,
        borderWidth: 2,
    },
    choiceCopy: {
        flex: 1,
    },
    choiceName: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 15,
    },
    choiceNameSelected: {
        color: colors.primary,
    },
    choiceMeta: {
        ...typography.caption,
        marginTop: 2,
    },
    radio: {
        alignItems: "center",
        borderColor: colors.line,
        borderRadius: 12,
        borderWidth: 2,
        height: 22,
        justifyContent: "center",
        width: 22,
    },
    radioActive: {
        borderColor: colors.primary,
    },
    radioInner: {
        backgroundColor: colors.primary,
        borderRadius: 6,
        height: 12,
        width: 12,
    },
    inputsSection: {
        gap: spacing.sm,
        marginTop: spacing.xs,
    },
});
