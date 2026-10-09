/**
 * Submit Request Screen — leave, attendance correction, work-from-home, permissions.
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

import { requestsApi, type RequestCreateInput } from "@/api/requests";
import { Button, PageHeader, Screen } from "@/components";
import { colors, radius, spacing, typography } from "@/theme";

const REQUEST_TYPES = [
    { key: "LEAVE", label: "Leave" },
    { key: "ATTENDANCE_CORRECTION", label: "Attendance Correction" },
    { key: "WORK_FROM_HOME", label: "Work From Home" },
    { key: "PERMISSION", label: "Permission" },
] as const;

const schema = z.object({
    request_type: z.string().min(1),
    title: z.string().min(1, "Required").max(200),
    description: z.string().max(5000).default(""),
    start_date: z.string().default(""),
    end_date: z.string().default(""),
});

type FormValues = z.infer<typeof schema>;

export default function CreateRequestScreen() {
    const qc = useQueryClient();

    const {
        control,
        handleSubmit,
        formState: { errors, isSubmitting },
    } = useForm<FormValues>({
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        resolver: zodResolver(schema) as any,
        defaultValues: {
            request_type: "LEAVE",
            title: "",
            description: "",
            start_date: "",
            end_date: "",
        },
    });

    const createMutation = useMutation({
        mutationFn: (values: FormValues) => {
            const payload: RequestCreateInput = {
                request_type: values.request_type,
                title: values.title,
                description: values.description || null,
                start_date: values.start_date || null,
                end_date: values.end_date || null,
            };
            return requestsApi.create(payload);
        },
        onSuccess: (req) => {
            void qc.invalidateQueries({ queryKey: ["requests"] });
            router.replace(`/requests/${req.id}` as never);
        },
        onError: (e: unknown) => {
            Alert.alert("Error", e instanceof Error ? e.message : "Failed to submit request.");
        },
    });

    const onSubmit = (values: FormValues) => {
        createMutation.mutate(values);
    };

    const busy = isSubmitting || createMutation.isPending;

    return (
        <Screen>
            <PageHeader eyebrow="WORKFLOWS" title="New Request" />
            <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1 }}>
                <ScrollView
                    showsVerticalScrollIndicator={false}
                    contentContainerStyle={styles.content}
                    keyboardShouldPersistTaps="handled"
                >
                    <View style={styles.field}>
                        <Text style={styles.label}>Request Type</Text>
                        <Controller
                            control={control}
                            name="request_type"
                            render={({ field }) => (
                                <View style={styles.chips}>
                                    {REQUEST_TYPES.map((t) => (
                                        <Pressable
                                            key={t.key}
                                            onPress={() => field.onChange(t.key)}
                                            style={[styles.chip, field.value === t.key && styles.chipSelected]}
                                        >
                                            <Text
                                                style={[
                                                    styles.chipText,
                                                    field.value === t.key && styles.chipTextSelected,
                                                ]}
                                            >
                                                {t.label}
                                            </Text>
                                        </Pressable>
                                    ))}
                                </View>
                            )}
                        />
                    </View>

                    <View style={styles.field}>
                        <Text style={styles.label}>
                            Title <Text style={{ color: colors.danger }}>*</Text>
                        </Text>
                        <Controller
                            control={control}
                            name="title"
                            render={({ field }) => (
                                <TextInput
                                    placeholder="e.g. Vacation / Missed morning punch"
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

                    <View style={styles.rowFields}>
                        <View style={[styles.field, { flex: 1 }]}>
                            <Text style={styles.label}>Start Date</Text>
                            <Controller
                                control={control}
                                name="start_date"
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
                        <View style={[styles.field, { flex: 1 }]}>
                            <Text style={styles.label}>End Date</Text>
                            <Controller
                                control={control}
                                name="end_date"
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
                    </View>

                    <View style={styles.field}>
                        <Text style={styles.label}>Reason / Details</Text>
                        <Controller
                            control={control}
                            name="description"
                            render={({ field }) => (
                                <TextInput
                                    placeholder="Explain your request or specify missing attendance time..."
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
                        {busy ? <ActivityIndicator color={colors.white} size="small" /> : "Submit Request"}
                    </Button>
                </ScrollView>
            </KeyboardAvoidingView>
        </Screen>
    );
}

const styles = StyleSheet.create({
    content: { gap: spacing.md, paddingBottom: spacing.xxl },
    field: { gap: spacing.xs },
    rowFields: { flexDirection: "row", gap: spacing.md },
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
