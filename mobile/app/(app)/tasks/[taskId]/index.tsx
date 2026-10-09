/**
 * Task detail screen: status toggles, checklists, and deletion.
 */
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { useState } from "react";
import {
    ActivityIndicator,
    Alert,
    Pressable,
    ScrollView,
    StyleSheet,
    Text,
    TextInput,
    View,
} from "react-native";

import { tasksApi } from "@/api/tasks";
import { Card, ErrorState, LoadingState, PageHeader, Screen, SectionHeader } from "@/components";
import { colors, radius, shadow, spacing, typography } from "@/theme";

const STATUSES = ["TODO", "IN_PROGRESS", "REVIEW", "DONE"] as const;

export default function TaskDetailScreen() {
    const { taskId } = useLocalSearchParams<{ taskId: string }>();
    const qc = useQueryClient();
    const [newItemText, setNewItemText] = useState("");

    const { data: task, isLoading, isError, refetch } = useQuery({
        queryKey: ["task", taskId],
        queryFn: () => tasksApi.get(taskId),
        enabled: !!taskId,
    });

    const statusMutation = useMutation({
        mutationFn: (nextStatus: "TODO" | "IN_PROGRESS" | "REVIEW" | "DONE") =>
            tasksApi.patch(taskId, { status: nextStatus }),
        onSuccess: () => {
            void qc.invalidateQueries({ queryKey: ["tasks"] });
            void qc.invalidateQueries({ queryKey: ["task", taskId] });
        },
    });

    const checklistToggleMutation = useMutation({
        mutationFn: (itemId: string) => tasksApi.toggleChecklistItem(taskId, itemId),
        onSuccess: () => {
            void qc.invalidateQueries({ queryKey: ["task", taskId] });
        },
    });

    const addChecklistMutation = useMutation({
        mutationFn: (title: string) => tasksApi.addChecklistItem(taskId, title),
        onSuccess: () => {
            setNewItemText("");
            void qc.invalidateQueries({ queryKey: ["task", taskId] });
        },
    });

    const deleteMutation = useMutation({
        mutationFn: () => tasksApi.delete(taskId),
        onSuccess: () => {
            void qc.invalidateQueries({ queryKey: ["tasks"] });
            router.back();
        },
    });

    const handleDelete = () => {
        Alert.alert("Delete Task", "Are you sure you want to permanently delete this task?", [
            { text: "Cancel", style: "cancel" },
            { text: "Delete", style: "destructive", onPress: () => deleteMutation.mutate() },
        ]);
    };

    if (isLoading) return <Screen><LoadingState /></Screen>;
    if (isError || !task) return <Screen><ErrorState onRetry={() => void refetch()} /></Screen>;

    return (
        <Screen>
            <PageHeader
                eyebrow={task.priority}
                title={task.title}
                right={
                    <Pressable onPress={handleDelete} style={styles.deleteBtn}>
                        <MaterialCommunityIcons name="trash-can-outline" size={20} color={colors.danger} />
                    </Pressable>
                }
            />

            <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.content}>
                {/* Status Switcher */}
                <View style={styles.statusRow}>
                    {STATUSES.map((st) => (
                        <Pressable
                            key={st}
                            onPress={() => statusMutation.mutate(st)}
                            style={[styles.statusChip, task.status === st && styles.statusChipActive]}
                        >
                            <Text style={[styles.statusChipText, task.status === st && styles.statusChipTextActive]}>
                                {st.replace(/_/g, " ")}
                            </Text>
                        </Pressable>
                    ))}
                </View>

                {/* Details */}
                <Card>
                    {task.description ? (
                        <Text style={styles.description}>{task.description}</Text>
                    ) : (
                        <Text style={styles.noDesc}>No description provided.</Text>
                    )}

                    <View style={styles.metaRow}>
                        {task.due_date ? (
                            <View style={styles.metaItem}>
                                <Text style={styles.metaLabel}>Due</Text>
                                <Text style={styles.metaValue}>{task.due_date}</Text>
                            </View>
                        ) : null}
                        {task.group_name ? (
                            <View style={styles.metaItem}>
                                <Text style={styles.metaLabel}>Group</Text>
                                <Text style={styles.metaValue}>{task.group_name}</Text>
                            </View>
                        ) : null}
                    </View>
                </Card>

                {/* Checklist Section */}
                <SectionHeader title={`CHECKLIST (${task.checklist?.filter((i) => i.is_completed).length || 0}/${task.checklist?.length || 0})`} />

                {task.checklist?.map((item) => (
                    <Pressable
                        key={item.id}
                        onPress={() => checklistToggleMutation.mutate(item.id)}
                        style={styles.checkItem}
                    >
                        <MaterialCommunityIcons
                            name={item.is_completed ? "checkbox-marked" : "checkbox-blank-outline"}
                            size={20}
                            color={item.is_completed ? colors.primary : colors.muted}
                        />
                        <Text style={[styles.checkTitle, item.is_completed && styles.checkTitleCompleted]}>
                            {item.title}
                        </Text>
                    </Pressable>
                ))}

                {/* Add Item Input */}
                <View style={styles.addItemRow}>
                    <TextInput
                        placeholder="Add checklist item..."
                        placeholderTextColor={colors.muted}
                        value={newItemText}
                        onChangeText={setNewItemText}
                        style={styles.addInput}
                    />
                    <Pressable
                        onPress={() => newItemText.trim() && addChecklistMutation.mutate(newItemText.trim())}
                        disabled={!newItemText.trim() || addChecklistMutation.isPending}
                        style={[styles.addBtn, !newItemText.trim() && { opacity: 0.5 }]}
                    >
                        <MaterialCommunityIcons name="plus" size={20} color={colors.white} />
                    </Pressable>
                </View>
            </ScrollView>
        </Screen>
    );
}

const styles = StyleSheet.create({
    content: { gap: spacing.md, paddingBottom: spacing.xxl },
    deleteBtn: {
        width: 40,
        height: 40,
        borderRadius: 20,
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: colors.surfaceCard,
    },
    statusRow: {
        flexDirection: "row",
        gap: spacing.xs + 2,
    },
    statusChip: {
        flex: 1,
        alignItems: "center",
        paddingVertical: spacing.xs + 2,
        borderRadius: radius.pill,
        backgroundColor: colors.white,
        borderWidth: 1,
        borderColor: colors.border,
    },
    statusChipActive: {
        backgroundColor: colors.ink,
        borderColor: colors.ink,
    },
    statusChipText: {
        ...typography.caption,
        fontSize: 11,
        fontWeight: "700",
        color: colors.textSecondary,
    },
    statusChipTextActive: {
        color: colors.white,
    },
    description: {
        ...typography.body,
        color: colors.ink,
        fontSize: 14,
        lineHeight: 20,
    },
    noDesc: {
        ...typography.caption,
        color: colors.textSecondary,
        fontStyle: "italic",
    },
    metaRow: {
        flexDirection: "row",
        gap: spacing.xl,
        marginTop: spacing.md,
        paddingTop: spacing.sm,
        borderTopWidth: StyleSheet.hairlineWidth,
        borderTopColor: colors.border,
    },
    metaItem: {
        gap: 2,
    },
    metaLabel: {
        ...typography.caption,
        fontSize: 10,
        color: colors.textSecondary,
        textTransform: "uppercase",
        fontWeight: "600",
    },
    metaValue: {
        ...typography.body,
        fontSize: 13,
        fontWeight: "600",
        color: colors.ink,
    },
    checkItem: {
        flexDirection: "row",
        alignItems: "center",
        gap: spacing.sm,
        backgroundColor: colors.white,
        borderRadius: radius.md,
        padding: spacing.md,
        borderWidth: 1,
        borderColor: colors.border,
    },
    checkTitle: {
        ...typography.body,
        fontSize: 14,
        color: colors.ink,
        flex: 1,
    },
    checkTitleCompleted: {
        textDecorationLine: "line-through",
        color: colors.textSecondary,
    },
    addItemRow: {
        flexDirection: "row",
        gap: spacing.sm,
        marginTop: spacing.xs,
    },
    addInput: {
        flex: 1,
        height: 44,
        backgroundColor: colors.white,
        borderWidth: 1,
        borderColor: colors.border,
        borderRadius: radius.pill,
        paddingHorizontal: spacing.md,
        ...typography.body,
        fontSize: 14,
        color: colors.ink,
    },
    addBtn: {
        width: 44,
        height: 44,
        borderRadius: 22,
        backgroundColor: colors.primary,
        alignItems: "center",
        justifyContent: "center",
    },
});
