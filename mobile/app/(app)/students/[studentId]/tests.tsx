import { FlatList, Pressable, StyleSheet, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";

import { useStudent, useStudentTests } from "@/api/hooks";
import { Badge, Button, Card, EmptyState, ErrorState, LoadingState, PageHeader, Screen } from "@/components";
import { colors, radius, spacing, typography } from "@/theme";

export default function StudentTestsScreen() {
    const { studentId } = useLocalSearchParams<{ studentId: string }>();
    const studentQuery = useStudent(studentId);
    const testsQuery = useStudentTests(studentId);

    if (studentQuery.isLoading || testsQuery.isLoading) {
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
                    void testsQuery.refetch();
                }} />
            </Screen>
        );
    }

    const student = studentQuery.data;
    const name = `${student.first_name} ${student.last_name}`.trim();
    const testMarks = testsQuery.data ?? [];

    const averageScore = testMarks.length > 0
        ? Math.round(testMarks.reduce((sum: number, item: { percentage?: number }) => sum + (item.percentage || 0), 0) / testMarks.length)
        : 0;

    return (
        <Screen>
            <FlatList
                contentContainerStyle={styles.content}
                data={testMarks}
                keyExtractor={(item) => item.id}
                showsVerticalScrollIndicator={false}
                ListHeaderComponent={
                    <View style={styles.headerWrap}>
                        <PageHeader
                            eyebrow="STUDENT ACADEMICS"
                            title={`${name}'s Tests`}
                            action={
                                <Button variant="secondary" size="sm" onPress={() => router.back()}>
                                    Back
                                </Button>
                            }
                        />

                        <Card style={styles.summaryCard}>
                            <View style={styles.summaryRow}>
                                <View style={styles.summaryCol}>
                                    <Text style={styles.summaryLabel}>Assessments</Text>
                                    <Text style={styles.summaryValue}>{testMarks.length}</Text>
                                </View>
                                <View style={styles.summaryDivider} />
                                <View style={styles.summaryCol}>
                                    <Text style={styles.summaryLabel}>Avg Score</Text>
                                    <Text style={[styles.summaryValue, averageScore >= 50 ? styles.goodScore : null]}>
                                        {averageScore}%
                                    </Text>
                                </View>
                            </View>
                        </Card>

                        <Text style={styles.sectionTitle}>Test Results ({testMarks.length})</Text>
                    </View>
                }
                ListEmptyComponent={
                    <EmptyState
                        icon="📝"
                        title="No test marks recorded"
                        message="There are no academic test marks recorded for this student yet."
                        action={<Button onPress={() => router.push("/(app)/tests" as never)}>View Tests</Button>}
                    />
                }
                renderItem={({ item }) => (
                    <Pressable onPress={() => router.push(`/tests/${item.test_id}` as never)}>
                        <Card style={styles.testCard}>
                            <View style={styles.testHeader}>
                                <View style={styles.testInfo}>
                                    <Text style={styles.testTitle}>{item.test_name ?? item.test_title}</Text>
                                    <Text style={styles.testMeta}>
                                        {item.subject ? `${item.subject} · ` : ""}
                                        {item.test_date}
                                    </Text>
                                </View>
                                {Boolean(item.grade) && (
                                    <Badge tone="success">{item.grade}</Badge>
                                )}
                            </View>

                            <View style={styles.scoreRow}>
                                <View style={styles.scoreBox}>
                                    <Text style={styles.scoreText}>
                                        {item.marks} / {item.maximum_marks}
                                    </Text>
                                    <Text style={styles.percentageText}>{item.percentage}%</Text>
                                </View>
                                {Boolean(item.remarks) && (
                                    <Text style={styles.remarksText}>"{item.remarks}"</Text>
                                )}
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
    goodScore: {
        color: colors.green,
    },
    sectionTitle: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 16,
        marginTop: spacing.sm,
    },
    testCard: {
        gap: spacing.sm,
        padding: spacing.md,
    },
    testHeader: {
        alignItems: "flex-start",
        flexDirection: "row",
        justifyContent: "space-between",
    },
    testInfo: {
        flex: 1,
        marginRight: spacing.sm,
    },
    testTitle: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 15,
    },
    testMeta: {
        ...typography.caption,
        marginTop: 2,
    },
    scoreRow: {
        alignItems: "center",
        borderTopColor: colors.line,
        borderTopWidth: 1,
        flexDirection: "row",
        justifyContent: "space-between",
        paddingTop: spacing.xs,
    },
    scoreBox: {
        flexDirection: "row",
        gap: spacing.sm,
    },
    scoreText: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 14,
    },
    percentageText: {
        ...typography.caption,
        color: colors.primary,
        fontWeight: "700",
    },
    remarksText: {
        ...typography.caption,
        color: colors.muted,
        fontStyle: "italic",
    },
});
