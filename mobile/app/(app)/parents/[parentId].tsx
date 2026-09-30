import { Alert, FlatList, Linking, Pressable, StyleSheet, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useQuery } from "@tanstack/react-query";

import { parentsApi } from "@/api/parents";
import { Avatar, Badge, Button, Card, EmptyState, ErrorState, LoadingState, PageHeader, Screen } from "@/components";
import { colors, radius, spacing, typography } from "@/theme";

export default function ParentDetailScreen() {
    const { parentId } = useLocalSearchParams<{ parentId: string }>();

    const parentQuery = useQuery({
        queryKey: ["parent", parentId],
        queryFn: () => parentsApi.get(parentId),
        enabled: Boolean(parentId),
    });

    const studentsQuery = useQuery({
        queryKey: ["parent-students", parentId],
        queryFn: () => parentsApi.students(parentId),
        enabled: Boolean(parentId),
    });

    if (parentQuery.isLoading || studentsQuery.isLoading) {
        return (
            <Screen>
                <LoadingState />
            </Screen>
        );
    }

    if (parentQuery.isError || !parentQuery.data) {
        return (
            <Screen>
                <ErrorState onRetry={() => {
                    void parentQuery.refetch();
                    void studentsQuery.refetch();
                }} />
            </Screen>
        );
    }

    const parent = parentQuery.data;
    const students = studentsQuery.data ?? [];

    const handleCall = () => {
        if (!parent.phone) return;
        Linking.openURL(`tel:${parent.phone}`).catch(() => {
            Alert.alert("Unable to call", `Could not place call to ${parent.phone}`);
        });
    };

    const handleEmail = () => {
        if (!parent.email) return;
        Linking.openURL(`mailto:${parent.email}`).catch(() => {
            Alert.alert("Unable to email", `Could not send email to ${parent.email}`);
        });
    };

    const handleWhatsApp = () => {
        if (!parent.phone) return;
        const clean = parent.phone.replace(/[^0-9]/g, "");
        Linking.openURL(`https://wa.me/${clean}`).catch(() => {
            Alert.alert("Unable to open WhatsApp", "Make sure WhatsApp is installed.");
        });
    };

    const handleDelete = () => {
        Alert.alert(
            "Delete parent contact",
            `Are you sure you want to remove ${parent.name} from records?`,
            [
                { text: "Cancel", style: "cancel" },
                {
                    text: "Delete",
                    style: "destructive",
                    onPress: async () => {
                        try {
                            await parentsApi.remove(parent.id);
                            router.back();
                        } catch {
                            Alert.alert("Error", "Could not remove parent contact.");
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
                data={students}
                keyExtractor={(item) => item.id}
                showsVerticalScrollIndicator={false}
                ListHeaderComponent={
                    <View style={styles.headerWrap}>
                        <PageHeader
                            eyebrow="GUARDIAN PROFILE"
                            title={parent.name}
                            action={
                                <Button variant="secondary" size="sm" onPress={() => router.back()}>
                                    Back
                                </Button>
                            }
                        />

                        <Card style={styles.profileCard}>
                            <View style={styles.profileTop}>
                                <Avatar name={parent.name} size={52} />
                                <View style={styles.profileInfo}>
                                    <Text style={styles.profileName}>{parent.name}</Text>
                                    <Text style={styles.profileMeta}>
                                        {parent.relationship ?? "Guardian / Parent"}
                                    </Text>
                                </View>
                                <Badge tone="neutral">Parent</Badge>
                            </View>

                            <View style={styles.contactDetails}>
                                {Boolean(parent.phone) && (
                                    <View style={styles.detailRow}>
                                        <Text style={styles.detailLabel}>Phone:</Text>
                                        <Text style={styles.detailVal}>{parent.phone}</Text>
                                    </View>
                                )}
                                {Boolean(parent.email) && (
                                    <View style={styles.detailRow}>
                                        <Text style={styles.detailLabel}>Email:</Text>
                                        <Text style={styles.detailVal}>{parent.email}</Text>
                                    </View>
                                )}
                            </View>

                            <View style={styles.quickActions}>
                                {Boolean(parent.phone) && (
                                    <>
                                        <Button size="sm" variant="secondary" onPress={handleCall}>
                                            Call
                                        </Button>
                                        <Button size="sm" variant="secondary" onPress={handleWhatsApp}>
                                            WhatsApp
                                        </Button>
                                    </>
                                )}
                                {Boolean(parent.email) && (
                                    <Button size="sm" variant="secondary" onPress={handleEmail}>
                                        Email
                                    </Button>
                                )}
                                <Button size="sm" variant="danger" onPress={handleDelete}>
                                    Delete
                                </Button>
                            </View>
                        </Card>

                        <Text style={styles.sectionTitle}>Linked Students ({students.length})</Text>
                    </View>
                }
                ListEmptyComponent={
                    <EmptyState
                        icon="🎒"
                        title="No linked students"
                        message="This parent has not been linked to any students yet."
                        action={<Button onPress={() => router.push("/(app)/(tabs)/students")}>View Students</Button>}
                    />
                }
                renderItem={({ item }) => {
                    const studentName = `${item.first_name} ${item.last_name}`.trim();
                    return (
                        <Pressable onPress={() => router.push(`/students/${item.id}` as never)}>
                            <Card style={styles.studentCard}>
                                <Avatar name={studentName} size={40} />
                                <View style={styles.studentInfo}>
                                    <Text style={styles.studentName}>{studentName}</Text>
                                    <Text style={styles.studentMeta}>
                                        {item.grade ? `${item.grade} · ` : ""}
                                        {item.student_number ? `#${item.student_number}` : "Enrolled"}
                                    </Text>
                                </View>
                                <Button
                                    size="sm"
                                    variant="secondary"
                                    onPress={() => router.push(`/students/${item.id}` as never)}
                                >
                                    View Hub
                                </Button>
                            </Card>
                        </Pressable>
                    );
                }}
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
    contactDetails: {
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
    quickActions: {
        flexDirection: "row",
        flexWrap: "wrap",
        gap: spacing.xs,
        marginTop: spacing.xs,
    },
    sectionTitle: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 16,
        marginTop: spacing.sm,
    },
    studentCard: {
        alignItems: "center",
        flexDirection: "row",
        gap: spacing.md,
        padding: spacing.md,
    },
    studentInfo: {
        flex: 1,
    },
    studentName: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 15,
    },
    studentMeta: {
        ...typography.caption,
        marginTop: 2,
    },
});
