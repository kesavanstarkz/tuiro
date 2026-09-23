import { useEffect, useState } from "react";
import { Alert, ScrollView, StyleSheet, Text, View } from "react-native";
import { useSettings, useUpdateSettings } from "@/api/hooks";
import { Button, Card, ErrorState, LoadingState, PageHeader, Screen, TuiroInput } from "@/components";
import { colors, spacing, typography } from "@/theme";

export default function SettingsScreen() {
    const query = useSettings(); const update = useUpdateSettings();
    const [name, setName] = useState(""); const [currency, setCurrency] = useState(""); const [timezone, setTimezone] = useState("");
    useEffect(() => { if (query.data) { setName(query.data.name); setCurrency(query.data.currency_code); setTimezone(query.data.timezone); } }, [query.data]);
    if (query.isLoading) return <Screen><LoadingState /></Screen>;
    if (query.isError) return <Screen><ErrorState onRetry={() => void query.refetch()} /></Screen>;
    const save = async () => { if (!name.trim() || currency.trim().length !== 3 || !timezone.trim()) { Alert.alert("Check your settings", "Enter a centre name, a three-letter currency code and a timezone."); return; } try { await update.mutateAsync({ name: name.trim(), currency_code: currency.trim().toUpperCase(), timezone: timezone.trim() }); Alert.alert("Settings saved", "Your centre preferences are up to date."); } catch { Alert.alert("Unable to save", "Please try again in a moment."); } };
    return <Screen><ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled"><PageHeader eyebrow="WORKSPACE" title="Settings" /><Card style={styles.intro}><Text style={styles.introTitle}>Centre preferences</Text><Text style={styles.introCopy}>These details personalise your dashboard, currency formatting and class schedule.</Text></Card><TuiroInput label="Centre name" value={name} onChangeText={setName} /><TuiroInput label="Currency code" value={currency} onChangeText={setCurrency} autoCapitalize="characters" maxLength={3} placeholder="INR" /><TuiroInput label="Timezone" value={timezone} onChangeText={setTimezone} placeholder="Asia/Kolkata" /><Card style={styles.info}><Text style={styles.infoTitle}>Region</Text><Text style={styles.infoCopy}>{query.data?.country_code} · Language: {query.data?.locale}</Text></Card><Button disabled={update.isPending} onPress={() => void save()}>{update.isPending ? "Saving…" : "Save settings"}</Button></ScrollView></Screen>;
}
const styles = StyleSheet.create({ content: { gap: spacing.md, paddingBottom: spacing.xxl, paddingTop: spacing.lg }, intro: { backgroundColor: colors.featureBlue }, introTitle: { ...typography.heading, fontSize: 17 }, introCopy: { ...typography.body, fontSize: 13, marginTop: spacing.xs }, info: { borderColor: colors.line, borderWidth: 1 }, infoTitle: { ...typography.label, color: colors.muted }, infoCopy: { ...typography.body, marginTop: spacing.xs }, });
