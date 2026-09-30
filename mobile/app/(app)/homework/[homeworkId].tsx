import { Alert, ScrollView, StyleSheet, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { MaterialCommunityIcons } from "@expo/vector-icons";

import { useHomeworkItem } from "@/api/hooks";
import { homeworkApi } from "@/api/homework";
import { Badge, Button, Card, ErrorState, LoadingState, PageHeader, Screen } from "@/components";
import { colors, radius, spacing, typography } from "@/theme";

export default function HomeworkDetailScreen() {
    const { homeworkId } = useLocalSearchParams<{ homeworkId: string }>();
    const query = useHomeworkItem(homeworkId);

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

    const homework = query.data;

    const handleDelete = () => {
        Alert.alert(
            "Delete assignment",
            `Are you sure you want to delete "${homework.title}"?`,
            [
                { text: "Cancel", style: "cancel" },
                {
                    text: "Delete",
                    style: "destructive",
                    onPress: async () => {
                        try {
                            await homeworkApi.remove(homework.id);
                            router.back();
                        } catch {
                            Alert.alert("Error", "Could not delete the assignment.");
                        }
                    },
                },
            ]
        );
    };

    return (
        <Screen>
            <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
                <PageHeader
                    eyebrow="ACADEMICS"
                    title={homework.title}
                    action={
                        <Button variant="secondary" size="sm" onPress={() => router.back()}>
                            Back
                        </Button>
                    }
                />

                <Card style={styles.card}>
                    <View style={styles.headerRow}>
                        <View style={styles.iconBox}>
                            <MaterialCommunityIcons name="book-open-variant" size={28} color={colors.primary} />
                        </View>
                        <View style={styles.headerInfo}>
                            <Text style={styles.title}>{homework.title}</Text>
                            <Text style={styles.targetClass}>{homework.class_name ?? "Class assignment"}</Text>
                        </View>
                        {homework.due_date ? (
                            <Badge tone="warning">Due {homework.due_date}</Badge>
                        ) : null}
                    </View>

                    {homework.description ? (
                        <View style={styles.section}>
                            <Text style={styles.sectionLabel}>Instructions & Notes</Text>
                            <Text style={styles.description}>{homework.description}</Text>
                        </View>
                    ) : null}
                </Card>

                <View style={styles.actions}>
                    <Button variant="danger" onPress={handleDelete}>
                        Delete assignment
                    </Button>
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
    card: {
        gap: spacing.md,
        padding: spacing.lg,
    },
    headerRow: {
        alignItems: "center",
        flexDirection: "row",
        gap: spacing.md,
    },
    iconBox: {
        alignItems: "center",
        backgroundColor: colors.coralSoft,
        borderRadius: radius.md,
        height: 52,
        justifyContent: "center",
        width: 52,
    },
    headerInfo: {
        flex: 1,
    },
    title: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 18,
    },
    targetClass: {
        ...typography.caption,
        marginTop: 2,
    },
    section: {
        borderTopColor: colors.line,
        borderTopWidth: 1,
        gap: spacing.xs,
        paddingTop: spacing.md,
    },
    sectionLabel: {
        ...typography.label,
        color: colors.muted,
    },
    description: {
        ...typography.body,
        color: colors.ink,
        lineHeight: 22,
    },
    actions: {
        marginTop: spacing.md,
    },
});
