import { zodResolver } from "@hookform/resolvers/zod";
import { router } from "expo-router";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { z } from "zod";

import { useAuthStore } from "@/store/auth";
import { Button, TuiroInput } from "@/components";

const schema = z.object({ display_name: z.string().min(1), organization_name: z.string().min(1), email: z.string().email(), password: z.string().min(8) });
type FormData = z.infer<typeof schema>;

export default function RegisterScreen() {
    const register = useAuthStore((state) => state.register); const [error, setError] = useState("");
    const { control, handleSubmit, formState: { isSubmitting } } = useForm<FormData>({ resolver: zodResolver(schema), defaultValues: { display_name: "", organization_name: "", email: "", password: "" } });
    const submit = async (values: FormData) => { setError(""); try { await register(values); router.replace("/(app)/(tabs)"); } catch (cause) { const message = cause instanceof Error ? cause.message : "Unable to create the account. Please try again."; setError(message); } };
    const field = (name: keyof FormData, label: string, placeholder: string, secure = false) => <Controller control={control} name={name} render={({ field: { onChange, value } }) => <TuiroInput label={label} placeholder={placeholder} secureTextEntry={secure} onChangeText={onChange} value={value} />} />;
    // Registration can be opened directly from a URL, leaving no navigation history.
    // Replacing the route is valid on web and native in either case.
    const returnToLogin = () => router.replace("/auth/login");
    return <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : "height"} style={styles.page}><ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled"><Text style={styles.kicker}>TUIRO</Text><Text style={styles.title}>Start simply</Text><Text style={styles.copy}>Set up your centre in a minute.</Text>{field("display_name", "Your name", "Kesavan Munusamy")}{field("organization_name", "Centre name", "Your learning centre")}{field("email", "Email", "you@example.com")}{field("password", "Password", "At least 8 characters", true)}{!!error && <Text style={styles.error}>{error}</Text>}<View style={styles.action}>{isSubmitting ? <ActivityIndicator color="#3568d4" /> : <Button onPress={handleSubmit(submit)}>Create account</Button>}</View><Pressable onPress={returnToLogin}><Text style={styles.link}>Already have an account? Sign in</Text></Pressable></ScrollView></KeyboardAvoidingView>;
}
const styles = StyleSheet.create({ page: { flex: 1, backgroundColor: "#f7f5ef" }, scroll: { flexGrow: 1, justifyContent: "center", padding: 28 }, kicker: { color: "#3568d4", fontWeight: "800", letterSpacing: 2 }, title: { color: "#20283a", fontSize: 34, fontWeight: "700", marginTop: 12 }, copy: { color: "#52616b", marginBottom: 8, marginTop: 6 }, action: { marginTop: 20 }, link: { color: "#3568d4", fontWeight: "700", marginTop: 24, textAlign: "center" }, error: { color: "#b33a3a", marginTop: 10 } });
