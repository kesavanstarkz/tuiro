import { Alert, FlatList, Pressable, StyleSheet, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { MaterialCommunityIcons } from "@expo/vector-icons";

import { useTest, useTestMarks } from "@/api/hooks";
import { testsApi } from "@/api/tests";
import { Avatar, Badge, Button, Card, EmptyState, ErrorState, LoadingState, PageHeader, Screen } from "@/components";
import { colors, radius, spacing, typography } from "@/theme";

export default function TestDetailScreen() {
    const { testId } = useLocalSearchParams<{ testId: string }>();
    const testQuery = useTest(testId);
    const marksQuery = useTestMarks(testId);

    if (testQuery.isLoading || marksQuery.isLoading) {
        return (
            <Screen>
                <LoadingState />
            </Screen>
        );
    }

    if (testQuery.isError || !testQuery.data) {
        return (
            <Screen>
                <ErrorState onRetry={() => {
                    void testQuery.refetch();
                    void marksQuery.refetch();
                }} />
            </Screen>
        );
    }

    const test = testQuery.data;
    const marks = marksQuery.data ?? [];

    const handleDelete = () => {
        Alert.alert(
            "Delete test",
            `Are you sure you want to delete "${test.name ?? test.title}"?`,
            [
                { text: "Cancel", style: "cancel" },
                {
                    text: "Delete",
                    style: "destructive",
                    onPress: async () => {
                        try {
                            await testsApi.remove(test.id);
                            router.back();
                        } catch {
                            Alert.alert("Error", "Could not delete test.");
                        }
                    },
                },
            ]
        );
    };

    return (
        <Screen>
            <FlatList
                contentContainerStyle={styles.content}
                data={marks}
                keyExtractor={(item) => item.id}
                showsVerticalScrollIndicator={false}
                ListHeaderComponent={
                    <View style={styles.headerWrap}>
                        <PageHeader
                            eyebrow="ACADEMICS"
                            title={test.name ?? test.title ?? "Test details"}
                            action={
                                <Button variant="secondary" size="sm" onPress={() => router.back()}>
                                    Back
                                </Button>
                            }
                        />

                        <Card style={styles.summaryCard}>
                            <View style={styles.topRow}>
                                <View style={styles.iconBox}>
                                    <MaterialCommunityIcons name="file-document-edit-outline" size={28} color={colors.primary} />
                                </View>
                                <View style={styles.topInfo}>
                                    <Text style={styles.testName}>{test.name ?? test.title}</Text>
                                    <Text style={styles.classText}>
                                        {test.class_name ? `Class: ${test.class_name}` : "Assessment"}
                                        {test.subject ? ` · ${test.subject}` : ""}
                                    </Text>
                                </View>
                                <Badge tone="neutral">{test.test_date}</Badge>
                            </View>

                            <View style={styles.metaRow}>
                                <View style={styles.metaCol}>
                                    <Text style={styles.metaLabel}>Max Marks</Text>
                                    <Text style={styles.metaValue}>{test.maximum_marks}</Text>
                                </View>
                                <View style={styles.metaDivider} />
                                <View style={styles.metaCol}>
                                    <Text style={styles.metaLabel}>Marks Recorded</Text>
                                    <Text style={styles.metaValue}>{marks.length}</Text>
                                </View>
                            </View>

                            <View style={styles.btnRow}>
                                <Button
                                    size="sm"
                                    onPress={() => router.push(`/tests/${testId}/marks` as never)}
                                >
                                    Enter / Edit Marks
                                </Button>
                                <Button
                                    variant="danger"
                                    size="sm"
                                    onPress={handleDelete}
                                >
                                    Delete
                                </Button>
                            </View>
                        </Card>

                        <Text style={styles.sectionTitle}>Student Results ({marks.length})</Text>
                    </View>
                }
                ListEmptyComponent={
                    <EmptyState
                        icon="📊"
                        title="No marks recorded yet"
                        message="Tap 'Enter / Edit Marks' above to record scores for students in this class."
                        action={
                            <Button onPress={() => router.push(`/tests/${testId}/marks` as never)}>
                                Record Marks
                            </Button>
                        }
                    />
                }
                renderItem={({ item }) => (
                    <Card style={styles.markCard}>
                        <Avatar name={item.student_name ?? "Student"} size={36} />
                        <View style={styles.markInfo}>
                            <Text style={styles.studentName}>{item.student_name ?? "Student"}</Text>
                            {Boolean(item.remarks) && (
                                <Text style={styles.remarksText}>{item.remarks}</Text>
                            )}
                        </View>
                        <View style={styles.scoreWrap}>
                            <Text style={styles.scoreText}>
                                {item.marks} / {item.maximum_marks}
                            </Text>
                            <Text style={styles.percentageText}>{item.percentage}%</Text>
                        </View>
                        {Boolean(item.grade) && (
                            <Badge tone="success">{item.grade}</Badge>
                        )}
                    </Card>
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
        gap: spacing.md,
        padding: spacing.md,
    },
    topRow: {
        alignItems: "center",
        flexDirection: "row",
        gap: spacing.md,
    },
    iconBox: {
        alignItems: "center",
        backgroundColor: colors.coralSoft,
        borderRadius: radius.md,
        height: 48,
        justifyContent: "center",
        width: 48,
    },
    topInfo: {
        flex: 1,
    },
    testName: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 17,
    },
    classText: {
        ...typography.caption,
        marginTop: 2,
    },
    metaRow: {
        alignItems: "center",
        backgroundColor: colors.surface,
        borderRadius: radius.sm,
        flexDirection: "row",
        justifyContent: "space-around",
        paddingVertical: spacing.sm,
    },
    metaCol: {
        alignItems: "center",
        flex: 1,
    },
    metaDivider: {
        backgroundColor: colors.line,
        height: 24,
        width: 1,
    },
    metaLabel: {
        ...typography.caption,
        color: colors.muted,
    },
    metaValue: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 16,
        marginTop: 2,
    },
    btnRow: {
        flexDirection: "row",
        gap: spacing.sm,
    },
    sectionTitle: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 16,
        marginTop: spacing.sm,
    },
    markCard: {
        alignItems: "center",
        flexDirection: "row",
        gap: spacing.md,
        padding: spacing.md,
    },
    markInfo: {
        flex: 1,
    },
    studentName: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 15,
    },
    remarksText: {
        ...typography.caption,
        color: colors.muted,
        marginTop: 2,
    },
    scoreWrap: {
        alignItems: "flex-end",
    },
    scoreText: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 15,
    },
    percentageText: {
        ...typography.caption,
        color: colors.muted,
    },
});
