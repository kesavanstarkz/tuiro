import { useEffect, useState } from "react";
import { Alert, FlatList, KeyboardAvoidingView, Platform, StyleSheet, Text, TextInput, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";

import { useClassStudents, useTest, useTestMarks } from "@/api/hooks";
import { testsApi } from "@/api/tests";
import { Avatar, Button, Card, EmptyState, ErrorState, LoadingState, PageHeader, Screen } from "@/components";
import { colors, radius, spacing, typography } from "@/theme";

interface StudentMarkRow {
    studentId: string;
    studentName: string;
    marks: string;
    grade: string;
    remarks: string;
}

export default function TestMarksScreen() {
    const { testId } = useLocalSearchParams<{ testId: string }>();
    const testQuery = useTest(testId);
    const marksQuery = useTestMarks(testId);
    const studentsQuery = useClassStudents(testQuery.data?.class_id);

    const [rows, setRows] = useState<Record<string, { marks: string; grade: string; remarks: string }>>({});
    const [saving, setSaving] = useState(false);

    const test = testQuery.data;
    const students = studentsQuery.data ?? [];
    const existingMarks = marksQuery.data ?? [];

    useEffect(() => {
        if (students.length > 0) {
            const initial: Record<string, { marks: string; grade: string; remarks: string }> = {};
            students.forEach((stu) => {
                const existing = existingMarks.find((m: { student_id: string; marks: number; grade?: string; remarks?: string }) => m.student_id === stu.id);
                initial[stu.id] = {
                    marks: existing ? String(existing.marks) : "",
                    grade: existing?.grade ?? "",
                    remarks: existing?.remarks ?? "",
                };
            });
            setRows(initial);
        }
    }, [students.length, existingMarks.length]);

    if (testQuery.isLoading || studentsQuery.isLoading || marksQuery.isLoading) {
        return (
            <Screen>
                <LoadingState />
            </Screen>
        );
    }

    if (testQuery.isError || !test) {
        return (
            <Screen>
                <ErrorState onRetry={() => void testQuery.refetch()} />
            </Screen>
        );
    }

    const updateField = (studentId: string, field: "marks" | "grade" | "remarks", value: string) => {
        setRows((prev) => ({
            ...prev,
            [studentId]: {
                ...(prev[studentId] || { marks: "", grade: "", remarks: "" }),
                [field]: value,
            },
        }));
    };

    const handleSaveAll = async () => {
        const entries = Object.entries(rows).filter(([_, data]) => data.marks.trim() !== "");
        if (entries.length === 0) {
            return Alert.alert("No marks entered", "Please enter marks for at least one student.");
        }

        const maxMarks = Number(test.maximum_marks);
        for (const [_, data] of entries) {
            const num = parseFloat(data.marks);
            if (isNaN(num) || num < 0 || num > maxMarks) {
                return Alert.alert("Invalid marks", `Marks must be a number between 0 and ${maxMarks}.`);
            }
        }

        try {
            setSaving(true);
            for (const [studentId, data] of entries) {
                await testsApi.saveMark(test.id, {
                    student_id: studentId,
                    marks: parseFloat(data.marks),
                    grade: data.grade.trim() || undefined,
                    remarks: data.remarks.trim() || undefined,
                });
            }
            Alert.alert("Success", "Test marks have been saved successfully.", [
                { text: "OK", onPress: () => router.back() },
            ]);
        } catch {
            Alert.alert("Error", "Failed to save test marks. Please try again.");
        } finally {
            setSaving(false);
        }
    };

    return (
        <Screen>
            <KeyboardAvoidingView
                behavior={Platform.OS === "ios" ? "padding" : undefined}
                style={styles.keyboardWrap}
            >
                <FlatList
                    contentContainerStyle={styles.content}
                    data={students}
                    keyExtractor={(item) => item.id}
                    showsVerticalScrollIndicator={false}
                    ListHeaderComponent={
                        <View style={styles.headerWrap}>
                            <PageHeader
                                eyebrow="TEST MARKS"
                                title={test.name ?? test.title ?? "Record Marks"}
                                action={
                                    <Button variant="secondary" size="sm" onPress={() => router.back()}>
                                        Cancel
                                    </Button>
                                }
                            />
                            <Card style={styles.infoCard}>
                                <Text style={styles.infoTitle}>{test.name ?? test.title}</Text>
                                <Text style={styles.infoSubtitle}>
                                    Maximum marks: <Text style={styles.highlight}>{test.maximum_marks}</Text>
                                    {test.class_name ? ` · Class: ${test.class_name}` : ""}
                                </Text>
                            </Card>
                        </View>
                    }
                    ListEmptyComponent={
                        <EmptyState
                            icon="👥"
                            title="No students enrolled"
                            message="This class has no students yet. Add students to the class roster before entering marks."
                            action={<Button onPress={() => router.back()}>Go Back</Button>}
                        />
                    }
                    renderItem={({ item }) => {
                        const rowData = rows[item.id] || { marks: "", grade: "", remarks: "" };
                        const name = `${item.first_name} ${item.last_name}`.trim();
                        return (
                            <Card style={styles.studentCard}>
                                <View style={styles.stuHeader}>
                                    <Avatar name={name} size={36} />
                                    <View style={styles.stuInfo}>
                                        <Text style={styles.stuName}>{name}</Text>
                                        <Text style={styles.stuRoll}>
                                            {item.student_number ? `Roll: ${item.student_number}` : "Enrolled"}
                                        </Text>
                                    </View>
                                </View>

                                <View style={styles.inputsRow}>
                                    <View style={styles.markInputWrap}>
                                        <Text style={styles.inputLabel}>Marks (/{test.maximum_marks})</Text>
                                        <TextInput
                                            style={styles.input}
                                            value={rowData.marks}
                                            onChangeText={(val) => updateField(item.id, "marks", val)}
                                            placeholder="0"
                                            placeholderTextColor={colors.muted}
                                            keyboardType="decimal-pad"
                                        />
                                    </View>
                                    <View style={styles.gradeInputWrap}>
                                        <Text style={styles.inputLabel}>Grade</Text>
                                        <TextInput
                                            style={styles.input}
                                            value={rowData.grade}
                                            onChangeText={(val) => updateField(item.id, "grade", val)}
                                            placeholder="A"
                                            placeholderTextColor={colors.muted}
                                            autoCapitalize="characters"
                                            maxLength={5}
                                        />
                                    </View>
                                </View>

                                <View style={styles.remarkWrap}>
                                    <Text style={styles.inputLabel}>Remarks (Optional)</Text>
                                    <TextInput
                                        style={styles.remarkInput}
                                        value={rowData.remarks}
                                        onChangeText={(val) => updateField(item.id, "remarks", val)}
                                        placeholder="Good performance, needs work in..."
                                        placeholderTextColor={colors.muted}
                                    />
                                </View>
                            </Card>
                        );
                    }}
                    ListFooterComponent={
                        students.length > 0 ? (
                            <View style={styles.footerWrap}>
                                <Button disabled={saving} onPress={() => void handleSaveAll()}>
                                    {saving ? "Saving marks..." : "Save all marks"}
                                </Button>
                            </View>
                        ) : null
                    }
                />
            </KeyboardAvoidingView>
        </Screen>
    );
}

const styles = StyleSheet.create({
    keyboardWrap: {
        flex: 1,
    },
    content: {
        gap: spacing.sm,
        paddingBottom: spacing.xxl,
        paddingTop: spacing.xs,
    },
    headerWrap: {
        gap: spacing.md,
        marginBottom: spacing.xs,
    },
    infoCard: {
        backgroundColor: colors.surface,
        gap: spacing.xs,
        padding: spacing.md,
    },
    infoTitle: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 16,
    },
    infoSubtitle: {
        ...typography.caption,
        color: colors.muted,
    },
    highlight: {
        color: colors.primary,
        fontWeight: "700",
    },
    studentCard: {
        gap: spacing.sm,
        padding: spacing.md,
    },
    stuHeader: {
        alignItems: "center",
        flexDirection: "row",
        gap: spacing.md,
    },
    stuInfo: {
        flex: 1,
    },
    stuName: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 15,
    },
    stuRoll: {
        ...typography.caption,
        marginTop: 2,
    },
    inputsRow: {
        flexDirection: "row",
        gap: spacing.md,
    },
    markInputWrap: {
        flex: 2,
    },
    gradeInputWrap: {
        flex: 1,
    },
    remarkWrap: {
        flex: 1,
    },
    inputLabel: {
        ...typography.caption,
        color: colors.muted,
        marginBottom: 4,
    },
    input: {
        backgroundColor: colors.surface,
        borderColor: colors.line,
        borderRadius: radius.sm,
        borderWidth: 1,
        color: colors.ink,
        fontSize: 15,
        fontWeight: "600",
        paddingHorizontal: spacing.sm,
        paddingVertical: 8,
    },
    remarkInput: {
        backgroundColor: colors.surface,
        borderColor: colors.line,
        borderRadius: radius.sm,
        borderWidth: 1,
        color: colors.ink,
        fontSize: 13,
        paddingHorizontal: spacing.sm,
        paddingVertical: 6,
    },
    footerWrap: {
        marginTop: spacing.md,
    },
});
