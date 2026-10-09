/**
 * Create task screen with title, priority chips, status, due date, and description.
 */
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { router } from "expo-router";
import { Controller, useForm } from "react-hook-form";
import {
    ActivityIndicator,
    Alert,
    KeyboardAvoidingView,
    Platform,
    Pressable,
    ScrollView,
    StyleSheet,
    Text,
    TextInput,
    View,
} from "react-native";
import { z } from "zod";

import { tasksApi, type TaskCreateInput } from "@/api/tasks";
import { Button, PageHeader, Screen } from "@/components";
import { colors, radius, spacing, typography } from "@/theme";

const PRIORITIES = ["LOW", "MEDIUM", "HIGH", "URGENT"] as const;

const schema = z.object({
    title: z.string().min(1, "Required").max(255),
    description: z.string().max(5000).default(""),
    priority: z.enum(PRIORITIES).default("MEDIUM"),
    due_date: z.string().default(""),
});

type FormValues = z.infer<typeof schema>;

export default function CreateTaskScreen() {
    const qc = useQueryClient();

    const {
        control,
        handleSubmit,
        formState: { errors, isSubmitting },
    } = useForm<FormValues>({
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        resolver: zodResolver(schema) as any,
        defaultValues: {
            title: "",
            description: "",
            priority: "MEDIUM",
            due_date: "",
        },
    });

    const createMutation = useMutation({
        mutationFn: (values: FormValues) => {
            const payload: TaskCreateInput = {
                title: values.title,
                description: values.description || null,
                priority: values.priority,
                due_date: values.due_date || null,
            };
            return tasksApi.create(payload);
        },
        onSuccess: (task) => {
            void qc.invalidateQueries({ queryKey: ["tasks"] });
            router.replace(`/tasks/${task.id}` as never);
        },
        onError: (e: unknown) => {
            Alert.alert("Error", e instanceof Error ? e.message : "Failed to create task.");
        },
    });

    const onSubmit = (values: FormValues) => {
        createMutation.mutate(values);
    };

    const busy = isSubmitting || createMutation.isPending;

    return (
        <Screen>
            <PageHeader eyebrow="NEW TASK" title="Create Task" />
            <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1 }}>
                <ScrollView
                    showsVerticalScrollIndicator={false}
                    contentContainerStyle={styles.content}
                    keyboardShouldPersistTaps="handled"
                >
                    <View style={styles.field}>
                        <Text style={styles.label}>
                            Title <Text style={{ color: colors.danger }}>*</Text>
                        </Text>
                        <Controller
                            control={control}
                            name="title"
                            render={({ field }) => (
                                <TextInput
                                    placeholder="e.g. Prepare curriculum syllabus"
                                    value={field.value}
                                    onChangeText={field.onChange}
                                    onBlur={field.onBlur}
                                    style={[styles.input, !!errors.title && styles.inputError]}
                                    placeholderTextColor={colors.muted}
                                />
                            )}
                        />
                        {errors.title ? <Text style={styles.error}>{errors.title.message}</Text> : null}
                    </View>

                    <View style={styles.field}>
                        <Text style={styles.label}>Priority</Text>
                        <Controller
                            control={control}
                            name="priority"
                            render={({ field }) => (
                                <View style={styles.chips}>
                                    {PRIORITIES.map((p) => (
                                        <Pressable
                                            key={p}
                                            onPress={() => field.onChange(p)}
                                            style={[styles.chip, field.value === p && styles.chipSelected]}
                                        >
                                            <Text
                                                style={[
                                                    styles.chipText,
                                                    field.value === p && styles.chipTextSelected,
                                                ]}
                                            >
                                                {p}
                                            </Text>
                                        </Pressable>
                                    ))}
                                </View>
                            )}
                        />
                    </View>

                    <View style={styles.field}>
                        <Text style={styles.label}>Due Date</Text>
                        <Controller
                            control={control}
                            name="due_date"
                            render={({ field }) => (
                                <TextInput
                                    placeholder="YYYY-MM-DD"
                                    value={field.value}
                                    onChangeText={field.onChange}
                                    onBlur={field.onBlur}
                                    style={styles.input}
                                    placeholderTextColor={colors.muted}
                                    keyboardType="numeric"
                                />
                            )}
                        />
                    </View>

                    <View style={styles.field}>
                        <Text style={styles.label}>Description</Text>
                        <Controller
                            control={control}
                            name="description"
                            render={({ field }) => (
                                <TextInput
                                    placeholder="Details, checklist items, links..."
                                    value={field.value}
                                    onChangeText={field.onChange}
                                    onBlur={field.onBlur}
                                    style={[styles.input, styles.textArea]}
                                    placeholderTextColor={colors.muted}
                                    multiline
                                    numberOfLines={4}
                                    textAlignVertical="top"
                                />
                            )}
                        />
                    </View>

                    {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                    <Button disabled={busy} onPress={handleSubmit(onSubmit as any)}>
                        {busy ? <ActivityIndicator color={colors.white} size="small" /> : "Create Task"}
                    </Button>
                </ScrollView>
            </KeyboardAvoidingView>
        </Screen>
    );
}

const styles = StyleSheet.create({
    content: { gap: spacing.md, paddingBottom: spacing.xxl },
    field: { gap: spacing.xs },
    label: { ...typography.label, color: colors.ink },
    error: { ...typography.caption, color: colors.danger },
    input: {
        height: 48,
        borderWidth: 1,
        borderColor: colors.border,
        borderRadius: radius.md,
        paddingHorizontal: spacing.md,
        ...typography.body,
        color: colors.ink,
        backgroundColor: colors.white,
        fontSize: 15,
    },
    inputError: { borderColor: colors.danger },
    textArea: { height: 100, paddingTop: spacing.md },
    chips: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
    chip: {
        paddingHorizontal: spacing.md,
        paddingVertical: spacing.xs + 2,
        borderRadius: radius.pill,
        borderWidth: 1,
        borderColor: colors.border,
        backgroundColor: colors.white,
    },
    chipSelected: { backgroundColor: colors.ink, borderColor: colors.ink },
    chipText: { ...typography.caption, color: colors.textSecondary, fontWeight: "600" },
    chipTextSelected: { color: colors.white },
});
