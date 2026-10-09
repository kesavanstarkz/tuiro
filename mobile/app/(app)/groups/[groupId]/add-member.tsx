/**
 * Add Member to Group Screen
 */
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
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

import { v2GroupsApi, type MembershipCreateInput } from "@/api/v2Groups";
import { Button, PageHeader, Screen } from "@/components";
import { colors, radius, spacing, typography } from "@/theme";

const MEMBER_TYPES = ["student", "teacher", "employee", "user"] as const;
const MEMBER_ROLES = ["member", "admin", "coordinator"] as const;

const schema = z.object({
    member_id: z.string().uuid("Must be a valid UUID"),
    member_type: z.enum(MEMBER_TYPES).default("student"),
    member_role: z.enum(MEMBER_ROLES).default("member"),
});

type FormValues = z.infer<typeof schema>;

export default function AddMemberScreen() {
    const { groupId } = useLocalSearchParams<{ groupId: string }>();
    const qc = useQueryClient();

    const {
        control,
        handleSubmit,
        formState: { errors, isSubmitting },
    } = useForm<FormValues>({
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        resolver: zodResolver(schema) as any,
        defaultValues: {
            member_id: "",
            member_type: "student",
            member_role: "member",
        },
    });

    const addMemberMutation = useMutation({
        mutationFn: (values: FormValues) =>
            v2GroupsApi.addMember(groupId, values as MembershipCreateInput),
        onSuccess: () => {
            void qc.invalidateQueries({ queryKey: ["v2group-members", groupId] });
            router.back();
        },
        onError: (e: unknown) => {
            Alert.alert("Error", e instanceof Error ? e.message : "Failed to add member to group.");
        },
    });

    const onSubmit = (values: FormValues) => {
        addMemberMutation.mutate(values);
    };

    const busy = isSubmitting || addMemberMutation.isPending;

    return (
        <Screen>
            <PageHeader eyebrow="GROUP" title="Add Member" />
            <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1 }}>
                <ScrollView
                    showsVerticalScrollIndicator={false}
                    contentContainerStyle={styles.content}
                    keyboardShouldPersistTaps="handled"
                >
                    <View style={styles.field}>
                        <Text style={styles.label}>Member Type</Text>
                        <Controller
                            control={control}
                            name="member_type"
                            render={({ field }) => (
                                <View style={styles.chips}>
                                    {MEMBER_TYPES.map((type) => (
                                        <Pressable
                                            key={type}
                                            onPress={() => field.onChange(type)}
                                            style={[styles.chip, field.value === type && styles.chipSelected]}
                                        >
                                            <Text
                                                style={[
                                                    styles.chipText,
                                                    field.value === type && styles.chipTextSelected,
                                                ]}
                                            >
                                                {type}
                                            </Text>
                                        </Pressable>
                                    ))}
                                </View>
                            )}
                        />
                    </View>

                    <View style={styles.field}>
                        <Text style={styles.label}>
                            Member ID (UUID) <Text style={{ color: colors.danger }}>*</Text>
                        </Text>
                        <Controller
                            control={control}
                            name="member_id"
                            render={({ field }) => (
                                <TextInput
                                    placeholder="e.g. 123e4567-e89b-12d3-a456-426614174000"
                                    value={field.value}
                                    onChangeText={field.onChange}
                                    onBlur={field.onBlur}
                                    style={[styles.input, !!errors.member_id && styles.inputError]}
                                    placeholderTextColor={colors.muted}
                                    autoCapitalize="none"
                                />
                            )}
                        />
                        {errors.member_id ? <Text style={styles.error}>{errors.member_id.message}</Text> : null}
                    </View>

                    <View style={styles.field}>
                        <Text style={styles.label}>Member Role</Text>
                        <Controller
                            control={control}
                            name="member_role"
                            render={({ field }) => (
                                <View style={styles.chips}>
                                    {MEMBER_ROLES.map((role) => (
                                        <Pressable
                                            key={role}
                                            onPress={() => field.onChange(role)}
                                            style={[styles.chip, field.value === role && styles.chipSelected]}
                                        >
                                            <Text
                                                style={[
                                                    styles.chipText,
                                                    field.value === role && styles.chipTextSelected,
                                                ]}
                                            >
                                                {role}
                                            </Text>
                                        </Pressable>
                                    ))}
                                </View>
                            )}
                        />
                    </View>

                    {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                    <Button disabled={busy} onPress={handleSubmit(onSubmit as any)}>
                        {busy ? <ActivityIndicator color={colors.white} size="small" /> : "Add Member"}
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
