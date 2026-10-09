/**
 * Create / Edit group form — React Hook Form + Zod, no transforms.
 */
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { useEffect } from "react";
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

import { v2GroupsApi, type GroupCreateInput } from "@/api/v2Groups";
import { Button, PageHeader, Screen } from "@/components";
import { colors, radius, spacing, typography } from "@/theme";

const GROUP_KINDS = ["team", "department", "class", "batch"] as const;

const schema = z.object({
    name: z.string().min(1, "Required").max(160),
    kind: z.enum(GROUP_KINDS).default("team"),
    description: z.string().max(5000).default(""),
});

type FormValues = z.infer<typeof schema>;

function toApiPayload(values: FormValues): GroupCreateInput {
    return {
        name: values.name,
        kind: values.kind,
        description: values.description || null,
    };
}

export default function CreateGroupScreen() {
    const { groupId } = useLocalSearchParams<{ groupId?: string }>();
    const isEdit = !!groupId;
    const qc = useQueryClient();

    const { data: existing } = useQuery({
        queryKey: ["v2group", groupId],
        queryFn: () => v2GroupsApi.get(groupId!),
        enabled: isEdit,
    });

    const {
        control,
        handleSubmit,
        reset,
        formState: { errors, isSubmitting },
    } = useForm<FormValues>({
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        resolver: zodResolver(schema) as any,
        defaultValues: { name: "", kind: "team", description: "" },
    });

    useEffect(() => {
        if (existing) {
            reset({
                name: existing.name,
                kind: (GROUP_KINDS.includes(existing.kind as typeof GROUP_KINDS[number])
                    ? existing.kind
                    : "team") as typeof GROUP_KINDS[number],
                description: existing.description ?? "",
            });
        }
    }, [existing, reset]);

    const createMutation = useMutation({
        mutationFn: (values: FormValues) => v2GroupsApi.create(toApiPayload(values)),
        onSuccess: (group) => {
            void qc.invalidateQueries({ queryKey: ["v2groups"] });
            router.replace(`/groups/${group.id}` as never);
        },
        onError: (e: unknown) => {
            Alert.alert("Error", e instanceof Error ? e.message : "Failed to create group.");
        },
    });

    const patchMutation = useMutation({
        mutationFn: (values: FormValues) => v2GroupsApi.patch(groupId!, toApiPayload(values)),
        onSuccess: () => {
            void qc.invalidateQueries({ queryKey: ["v2groups"] });
            void qc.invalidateQueries({ queryKey: ["v2group", groupId] });
            router.back();
        },
        onError: (e: unknown) => {
            Alert.alert("Error", e instanceof Error ? e.message : "Failed to update group.");
        },
    });

    const onSubmit = (values: FormValues) => {
        if (isEdit) patchMutation.mutate(values);
        else createMutation.mutate(values);
    };

    const busy = isSubmitting || createMutation.isPending || patchMutation.isPending;

    return (
        <Screen>
            <PageHeader eyebrow={isEdit ? "EDIT" : "NEW"} title={isEdit ? "Edit Group" : "Create Group"} />
            <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1 }}>
                <ScrollView
                    showsVerticalScrollIndicator={false}
                    contentContainerStyle={styles.content}
                    keyboardShouldPersistTaps="handled"
                >
                    <View style={styles.field}>
                        <Text style={styles.label}>
                            Group Name <Text style={{ color: colors.danger }}>*</Text>
                        </Text>
                        <Controller
                            control={control}
                            name="name"
                            render={({ field }) => (
                                <TextInput
                                    placeholder="e.g. Engineering Team, Grade 10A"
                                    value={field.value}
                                    onChangeText={field.onChange}
                                    onBlur={field.onBlur}
                                    style={[styles.input, !!errors.name && styles.inputError]}
                                    placeholderTextColor={colors.muted}
                                    autoCapitalize="words"
                                />
                            )}
                        />
                        {errors.name ? <Text style={styles.error}>{errors.name.message}</Text> : null}
                    </View>

                    <View style={styles.field}>
                        <Text style={styles.label}>Kind</Text>
                        <Controller
                            control={control}
                            name="kind"
                            render={({ field }) => (
                                <View style={styles.chips}>
                                    {GROUP_KINDS.map((kind) => (
                                        <Pressable
                                            key={kind}
                                            onPress={() => field.onChange(kind)}
                                            style={[styles.chip, field.value === kind && styles.chipSelected]}
                                        >
                                            <Text style={[styles.chipText, field.value === kind && styles.chipTextSelected]}>
                                                {kind}
                                            </Text>
                                        </Pressable>
                                    ))}
                                </View>
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
                                    placeholder="What does this group do?"
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
                        {busy ? <ActivityIndicator color={colors.white} size="small" /> : isEdit ? "Save Changes" : "Create Group"}
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
    chipText: { ...typography.caption, color: colors.textSecondary, fontWeight: "600", textTransform: "capitalize" },
    chipTextSelected: { color: colors.white },
});
