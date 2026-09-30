import { Alert, FlatList, StyleSheet, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { MaterialCommunityIcons } from "@expo/vector-icons";

import { useSchedules } from "@/api/hooks";
import { teachersApi } from "@/api/teachers";
import { Avatar, Badge, Button, Card, EmptyState, ErrorState, LoadingState, PageHeader, Screen } from "@/components";
import { colors, radius, spacing, typography } from "@/theme";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export default function TeacherDetailScreen() {
    const { teacherId } = useLocalSearchParams<{ teacherId: string }>();

    const teacherQuery = useQuery({
        queryKey: ["teacher", teacherId],
        queryFn: () => teachersApi.get(teacherId),
        enabled: Boolean(teacherId),
    });

    const schedulesQuery = useSchedules();

    if (teacherQuery.isLoading || schedulesQuery.isLoading) {
        return (
            <Screen>
                <LoadingState />
            </Screen>
        );
    }

    if (teacherQuery.isError || !teacherQuery.data) {
        return (
            <Screen>
                <ErrorState onRetry={() => {
                    void teacherQuery.refetch();
                    void schedulesQuery.refetch();
                }} />
            </Screen>
        );
    }

    const teacher = teacherQuery.data;
    const name = teacher.name ?? teacher.display_name ?? `Teacher #${teacher.employee_number ?? teacher.id.slice(0, 6)}`;
    const teacherSchedules = (schedulesQuery.data ?? []).filter((s) => s.teacher_id === teacherId);

    const handleDelete = () => {
        Alert.alert(
            "Remove teacher",
            `Are you sure you want to remove ${name} from your center?`,
            [
                { text: "Cancel", style: "cancel" },
                {
                    text: "Delete",
                    style: "destructive",
                    onPress: async () => {
                        try {
                            await teachersApi.remove(teacher.id);
                            router.back();
                        } catch {
                            Alert.alert("Error", "Could not remove teacher.");
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
                data={teacherSchedules}
                keyExtractor={(item) => item.id}
                showsVerticalScrollIndicator={false}
                ListHeaderComponent={
                    <View style={styles.headerWrap}>
                        <PageHeader
                            eyebrow="FACULTY"
                            title={name}
                            action={
                                <Button variant="secondary" size="sm" onPress={() => router.back()}>
                                    Back
                                </Button>
                            }
                        />

                        <Card style={styles.profileCard}>
                            <View style={styles.profileTop}>
                                <Avatar name={name} size={52} />
                                <View style={styles.profileInfo}>
                                    <Text style={styles.profileName}>{name}</Text>
                                    <Text style={styles.profileMeta}>
                                        {teacher.specialization ? `${teacher.specialization} Specialist` : "Faculty Member"}
                                        {teacher.employee_number ? ` · ID: ${teacher.employee_number}` : ""}
                                    </Text>
                                </View>
                                <Badge tone={teacher.status === "ACTIVE" ? "success" : "neutral"}>
                                    {teacher.status}
                                </Badge>
                            </View>

                            <View style={styles.detailRows}>
                                {Boolean(teacher.joining_date) && (
                                    <View style={styles.detailRow}>
                                        <Text style={styles.detailLabel}>Joined Date:</Text>
                                        <Text style={styles.detailVal}>{teacher.joining_date}</Text>
                                    </View>
                                )}
                                {Boolean(teacher.email) && (
                                    <View style={styles.detailRow}>
                                        <Text style={styles.detailLabel}>Email:</Text>
                                        <Text style={styles.detailVal}>{teacher.email}</Text>
                                    </View>
                                )}
                            </View>

                            <View style={styles.actionRow}>
                                <Button size="sm" variant="danger" onPress={handleDelete}>
                                    Remove Teacher
                                </Button>
                            </View>
                        </Card>

                        <Text style={styles.sectionTitle}>Weekly Teaching Schedule ({teacherSchedules.length})</Text>
                    </View>
                }
                ListEmptyComponent={
                    <EmptyState
                        icon="📅"
                        title="No classes assigned"
                        message="This teacher has no active weekly class schedule entries assigned yet."
                        action={<Button onPress={() => router.push("/(app)/schedule" as never)}>Manage Schedule</Button>}
                    />
                }
                renderItem={({ item }) => (
                    <Card style={styles.scheduleCard}>
                        <View style={styles.timeBox}>
                            <Text style={styles.timeText}>{item.start_time}</Text>
                            <Text style={styles.timeEndText}>{item.end_time}</Text>
                        </View>
                        <View style={styles.scheduleInfo}>
                            <Text style={styles.dayText}>{DAYS[item.day_of_week] ?? `Day ${item.day_of_week}`}</Text>
                            <Text style={styles.roomText}>{item.room ? `Room: ${item.room}` : "Standard Classroom"}</Text>
                        </View>
                        <MaterialCommunityIcons name="clock-outline" size={20} color={colors.primary} />
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
    profileCard: {
        gap: spacing.md,
        padding: spacing.lg,
    },
    profileTop: {
        alignItems: "center",
        flexDirection: "row",
        gap: spacing.md,
    },
    profileInfo: {
        flex: 1,
    },
    profileName: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 18,
    },
    profileMeta: {
        ...typography.caption,
        marginTop: 2,
    },
    detailRows: {
        borderTopColor: colors.line,
        borderTopWidth: 1,
        gap: 6,
        paddingTop: spacing.md,
    },
    detailRow: {
        flexDirection: "row",
        justifyContent: "space-between",
    },
    detailLabel: {
        ...typography.caption,
        color: colors.muted,
    },
    detailVal: {
        ...typography.body,
        color: colors.ink,
        fontWeight: "600",
    },
    actionRow: {
        marginTop: spacing.xs,
    },
    sectionTitle: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 16,
        marginTop: spacing.sm,
    },
    scheduleCard: {
        alignItems: "center",
        flexDirection: "row",
        gap: spacing.md,
        padding: spacing.md,
    },
    timeBox: {
        alignItems: "center",
        backgroundColor: colors.surface,
        borderRadius: radius.sm,
        paddingHorizontal: spacing.sm,
        paddingVertical: 6,
        width: 76,
    },
    timeText: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 14,
    },
    timeEndText: {
        ...typography.caption,
        color: colors.muted,
    },
    scheduleInfo: {
        flex: 1,
    },
    dayText: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 15,
    },
    roomText: {
        ...typography.caption,
        color: colors.muted,
        marginTop: 2,
    },
});
