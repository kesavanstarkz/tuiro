/**
 * Create / Edit employee screen — React Hook Form + Zod validation.
 * When personId is in the URL it's an edit; otherwise it's a create.
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

import { employeesApi, type EmployeeInput } from "@/api/platformPeople";
import { Button, PageHeader, Screen } from "@/components";
import { colors, radius, spacing, typography } from "@/theme";

const EMPLOYMENT_TYPES = ["FULL_TIME", "PART_TIME", "CONTRACT", "INTERN"] as const;

// Use a schema without transforms so RHF types work cleanly.
// We handle the null conversion manually before API calls.
const schema = z.object({
    employee_number: z.string().min(1, "Required").max(80),
    first_name: z.string().min(1, "Required").max(100),
    last_name: z.string().max(100).default(""),
    email: z.string().max(200).default(""),
    phone: z.string().max(30).default(""),
    employment_type: z.enum(EMPLOYMENT_TYPES).default("FULL_TIME"),
    start_date: z.string().default(""),
});

type FormValues = z.infer<typeof schema>;

function toApiPayload(values: FormValues): EmployeeInput {
    return {
        employee_number: values.employee_number,
        first_name: values.first_name,
        last_name: values.last_name || undefined,
        email: values.email || null,
        phone: values.phone || null,
        employment_type: values.employment_type,
        start_date: values.start_date || null,
    };
}

function Field({
    label,
    error,
    required,
    children,
}: {
    label: string;
    error?: string;
    required?: boolean;
    children: React.ReactNode;
}) {
    return (
        <View style={styles.field}>
            <Text style={styles.label}>
                {label}
                {required ? <Text style={{ color: colors.danger }}> *</Text> : null}
            </Text>
            {children}
            {error ? <Text style={styles.error}>{error}</Text> : null}
        </View>
    );
}

export default function CreateEmployeeScreen() {
    const { personId } = useLocalSearchParams<{ personId?: string }>();
    const isEdit = !!personId;
    const qc = useQueryClient();

    const { data: existing } = useQuery({
        queryKey: ["employee", personId],
        queryFn: () => employeesApi.get(personId!),
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
        defaultValues: {
            employee_number: "",
            first_name: "",
            last_name: "",
            email: "",
            phone: "",
            employment_type: "FULL_TIME",
            start_date: "",
        },
    });

    useEffect(() => {
        if (existing) {
            reset({
                employee_number: existing.employee_number,
                first_name: existing.first_name,
                last_name: existing.last_name ?? "",
                email: existing.email ?? "",
                phone: existing.phone ?? "",
                employment_type: (EMPLOYMENT_TYPES.includes(existing.employment_type as typeof EMPLOYMENT_TYPES[number])
                    ? existing.employment_type
                    : "FULL_TIME") as typeof EMPLOYMENT_TYPES[number],
                start_date: existing.start_date ?? "",
            });
        }
    }, [existing, reset]);

    const createMutation = useMutation({
        mutationFn: (values: FormValues) => employeesApi.create(toApiPayload(values)),
        onSuccess: (employee) => {
            void qc.invalidateQueries({ queryKey: ["employees"] });
            router.replace(`/people/${employee.id}` as never);
        },
        onError: (e: unknown) => {
            Alert.alert("Error", e instanceof Error ? e.message : "Failed to create employee.");
        },
    });

    const patchMutation = useMutation({
        mutationFn: (values: FormValues) => employeesApi.patch(personId!, toApiPayload(values)),
        onSuccess: () => {
            void qc.invalidateQueries({ queryKey: ["employees"] });
            void qc.invalidateQueries({ queryKey: ["employee", personId] });
            router.back();
        },
        onError: (e: unknown) => {
            Alert.alert("Error", e instanceof Error ? e.message : "Failed to update employee.");
        },
    });

    const onSubmit = (values: FormValues) => {
        if (isEdit) patchMutation.mutate(values);
        else createMutation.mutate(values);
    };

    const busy = isSubmitting || createMutation.isPending || patchMutation.isPending;

    return (
        <Screen>
            <PageHeader eyebrow={isEdit ? "EDIT" : "NEW"} title={isEdit ? "Edit Employee" : "Add Employee"} />
            <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1 }}>
                <ScrollView
                    showsVerticalScrollIndicator={false}
                    contentContainerStyle={styles.content}
                    keyboardShouldPersistTaps="handled"
                >
                    <Field label="Employee Number" error={errors.employee_number?.message} required>
                        <Controller
                            control={control}
                            name="employee_number"
                            render={({ field }) => (
                                <TextInput
                                    placeholder="EMP-001"
                                    value={field.value}
                                    onChangeText={field.onChange}
                                    onBlur={field.onBlur}
                                    style={[styles.input, !!errors.employee_number && styles.inputError]}
                                    placeholderTextColor={colors.muted}
                                    autoCapitalize="characters"
                                />
                            )}
                        />
                    </Field>

                    <Field label="First Name" error={errors.first_name?.message} required>
                        <Controller
                            control={control}
                            name="first_name"
                            render={({ field }) => (
                                <TextInput
                                    placeholder="First name"
                                    value={field.value}
                                    onChangeText={field.onChange}
                                    onBlur={field.onBlur}
                                    style={[styles.input, !!errors.first_name && styles.inputError]}
                                    placeholderTextColor={colors.muted}
                                    autoCapitalize="words"
                                />
                            )}
                        />
                    </Field>

                    <Field label="Last Name" error={errors.last_name?.message}>
                        <Controller
                            control={control}
                            name="last_name"
                            render={({ field }) => (
                                <TextInput
                                    placeholder="Last name"
                                    value={field.value}
                                    onChangeText={field.onChange}
                                    onBlur={field.onBlur}
                                    style={styles.input}
                                    placeholderTextColor={colors.muted}
                                    autoCapitalize="words"
                                />
                            )}
                        />
                    </Field>

                    <Field label="Email" error={errors.email?.message}>
                        <Controller
                            control={control}
                            name="email"
                            render={({ field }) => (
                                <TextInput
                                    placeholder="email@example.com"
                                    value={field.value}
                                    onChangeText={field.onChange}
                                    onBlur={field.onBlur}
                                    style={[styles.input, !!errors.email && styles.inputError]}
                                    placeholderTextColor={colors.muted}
                                    keyboardType="email-address"
                                    autoCapitalize="none"
                                />
                            )}
                        />
                    </Field>

                    <Field label="Phone" error={errors.phone?.message}>
                        <Controller
                            control={control}
                            name="phone"
                            render={({ field }) => (
                                <TextInput
                                    placeholder="+91 98765 43210"
                                    value={field.value}
                                    onChangeText={field.onChange}
                                    onBlur={field.onBlur}
                                    style={styles.input}
                                    placeholderTextColor={colors.muted}
                                    keyboardType="phone-pad"
                                />
                            )}
                        />
                    </Field>

                    <Field label="Start Date" error={errors.start_date?.message}>
                        <Controller
                            control={control}
                            name="start_date"
                            render={({ field }) => (
                                <TextInput
                                    placeholder="YYYY-MM-DD"
                                    value={field.value}
                                    onChangeText={field.onChange}
                                    onBlur={field.onBlur}
                                    style={[styles.input, !!errors.start_date && styles.inputError]}
                                    placeholderTextColor={colors.muted}
                                    keyboardType="numeric"
                                />
                            )}
                        />
                    </Field>

                    <Field label="Employment Type" error={errors.employment_type?.message}>
                        <Controller
                            control={control}
                            name="employment_type"
                            render={({ field }) => (
                                <View style={styles.chips}>
                                    {EMPLOYMENT_TYPES.map((type) => (
                                        <Pressable
                                            key={type}
                                            onPress={() => field.onChange(type)}
                                            style={[styles.chip, field.value === type && styles.chipSelected]}
                                        >
                                            <Text style={[styles.chipText, field.value === type && styles.chipTextSelected]}>
                                                {type.replace("_", " ")}
                                            </Text>
                                        </Pressable>
                                    ))}
                                </View>
                            )}
                        />
                    </Field>

                    {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                    <Button disabled={busy} onPress={handleSubmit(onSubmit as any)}>
                        {busy ? <ActivityIndicator color={colors.white} size="small" /> : isEdit ? "Save Changes" : "Add Employee"}
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
    error: { ...typography.caption, color: colors.danger, fontSize: 12 },
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
    chipText: { ...typography.caption, color: colors.textSecondary, fontWeight: "600" },
    chipTextSelected: { color: colors.white },
});
