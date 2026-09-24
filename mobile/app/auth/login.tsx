import { zodResolver } from "@hookform/resolvers/zod";
import { Link, router } from "expo-router";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { z } from "zod";

import { useAuthStore } from "@/store/auth";
import { Button, TuiroInput } from "@/components";
import { apiErrorMessage } from "@/api/client";

const schema = z.object({ email: z.string().email(), password: z.string().min(8) });
type FormData = z.infer<typeof schema>;

export default function LoginScreen() {
    const signIn = useAuthStore((state) => state.signIn);
    const [error, setError] = useState("");
    const { control, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({ resolver: zodResolver(schema), defaultValues: { email: "", password: "" } });
    const submit = async (values: FormData) => { setError(""); try { await signIn(values.email, values.password); router.replace("/(app)/(tabs)"); } catch (cause) { setError(apiErrorMessage(cause, "Unable to sign in. Check your details and try again.")); } };
    return <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : "height"} style={styles.page}><ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled"><Text style={styles.kicker}>TUIRO</Text><Text style={styles.title}>Welcome back 👋</Text><Text style={styles.copy}>Keep your centre moving.</Text>
        <Controller control={control} name="email" render={({ field: { onChange, value } }) => <TuiroInput label="Email" autoCapitalize="none" keyboardType="email-address" placeholder="you@example.com" onChangeText={onChange} value={value} error={errors.email ? "Enter a valid email." : undefined} />} />
        <Controller control={control} name="password" render={({ field: { onChange, value } }) => <TuiroInput label="Password" secureTextEntry placeholder="Your password" onChangeText={onChange} value={value} error={errors.password ? "Use at least 8 characters." : undefined} />} />
        {!!error && <Text style={styles.error}>{error}</Text>}
        <View style={styles.action}>{isSubmitting ? <ActivityIndicator color="#3568d4" /> : <Button onPress={handleSubmit(submit)}>Sign in</Button>}</View>
        <Link href="/auth/register" style={styles.link}>Create an account</Link><Text style={styles.muted}>Forgot password? Contact your centre administrator.</Text>
    </ScrollView></KeyboardAvoidingView>;
}
const styles = StyleSheet.create({ page: { flex: 1, backgroundColor: "#f7f5ef" }, scroll: { flexGrow: 1, justifyContent: "center", padding: 28 }, kicker: { color: "#3568d4", fontWeight: "800", letterSpacing: 2 }, title: { color: "#20283a", fontSize: 34, fontWeight: "700", marginTop: 12 }, copy: { color: "#52616b", marginBottom: 18, marginTop: 6 }, action: { marginTop: 20 }, link: { color: "#3568d4", fontWeight: "700", marginTop: 24, textAlign: "center" }, muted: { color: "#8a9296", fontSize: 12, marginTop: 30, textAlign: "center" }, error: { color: "#b33a3a", marginTop: 6, fontSize: 12 } });
