import { router } from "expo-router";
import { ScrollView, StyleSheet, Text, View } from "react-native";

import { useStudent } from "@/api/hooks";
import { Avatar, Badge, Button, Card, FeatureCard, PageHeader, Screen } from "./ui";
import { colors, radius, spacing, typography } from "@/theme";

export function ClassHub({ classId }: { classId: string }) {
    const destinations = [
        ["Students", "Class roster", `/classes/${classId}`],
        ["Attendance", "Mark or review", `/(app)/(tabs)/attendance?groupId=${classId}`],
        ["Homework", "Assignments", `/homework`],
        ["Tests", "Assessments", `/tests`],
        ["Schedule", "Class times", `/schedule`],
    ] as const;
    return (
        <Screen>
            <ScrollView contentContainerStyle={styles.content}>
                <PageHeader eyebrow="CLASS" title="Class details" />
                <Card>
                    <Text style={styles.copy}>
                        Use this class as the hub for its roster, daily register, and academic work.
                    </Text>
                </Card>
                <View style={styles.grid}>
                    {destinations.map(([title, subtitle, href]) => (
                        <FeatureCard
                            key={title}
                            title={title}
                            subtitle={subtitle}
                            icon="→"
                            color={colors.coralSoft}
                            onPress={() => router.push(href as never)}
                        />
                    ))}
                </View>
            </ScrollView>
        </Screen>
    );
}

export function StudentHub({ studentId }: { studentId: string }) {
    const student = useStudent(studentId);
    const studentData = student.data;
    const name = studentData ? `${studentData.first_name} ${studentData.last_name}`.trim() : "Student details";

    const destinations = [
        ["Attendance", "View records", `/students/${studentId}/attendance`],
        ["Fees", "Billing & dues", `/students/${studentId}/fees`],
        ["Homework", "Assigned work", `/students/${studentId}/homework`],
        ["Tests", "Assessments", `/students/${studentId}/tests`],
        ["Parent", "Guardian contact", `/students/${studentId}/parent`],
    ] as const;

    return (
        <Screen>
            <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
                <PageHeader eyebrow="STUDENT" title={name} />

                {studentData && (
                    <View style={styles.profileCard}>
                        <Avatar name={name} size={48} />
                        <View style={styles.profileInfo}>
                            <Text style={styles.profileName}>{name}</Text>
                            <Text style={styles.profileMeta}>
                                {studentData.grade ?? "Student"}
                                {studentData.student_number ? ` · Roll #${studentData.student_number}` : ""}
                            </Text>
                        </View>
                        <Badge tone={studentData.status === "ACTIVE" ? "success" : "neutral"}>
                            {studentData.status}
                        </Badge>
                    </View>
                )}

                <View style={styles.grid}>
                    {destinations.map(([title, subtitle, href]) => (
                        <FeatureCard
                            key={title}
                            title={title}
                            subtitle={subtitle}
                            icon="→"
                            color={colors.coralSoft}
                            onPress={() => router.push(href as never)}
                        />
                    ))}
                </View>
            </ScrollView>
        </Screen>
    );
}

export function ContextScreen({ title, eyebrow = "DETAIL" }: { title: string; eyebrow?: string }) {
    return (
        <Screen>
            <ScrollView contentContainerStyle={styles.content}>
                <PageHeader eyebrow={eyebrow} title={title} />
                <Card>
                    <Text style={styles.copy}>
                        This route is ready for its contextual view. Existing centre-wide workflows remain available
                        from their primary screens.
                    </Text>
                </Card>
                <Button variant="secondary" onPress={() => router.back()}>
                    Back
                </Button>
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
    copy: {
        ...typography.body,
        lineHeight: 21,
    },
    grid: {
        flexDirection: "row",
        flexWrap: "wrap",
        gap: spacing.sm,
    },
    profileCard: {
        alignItems: "center",
        backgroundColor: colors.white,
        borderColor: colors.line,
        borderRadius: radius.md,
        borderWidth: 1,
        flexDirection: "row",
        padding: spacing.md,
    },
    profileInfo: {
        flex: 1,
        marginHorizontal: spacing.md,
    },
    profileName: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 16,
    },
    profileMeta: {
        ...typography.caption,
        marginTop: 2,
    },
});
