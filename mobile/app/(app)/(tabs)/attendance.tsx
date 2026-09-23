import { useMemo, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { useLocalSearchParams } from "expo-router";

import { useGroupAttendance, useGroupMembers, useGroups, useSaveGroupAttendance } from "@/api/hooks";
import { Avatar, Badge, Button, Card, ErrorState, LoadingState, PageHeader, Screen, SectionHeader } from "@/components";
import { colors, spacing, typography } from "@/theme";

type Student = { id: string; first_name: string; last_name: string };
type Status = "PRESENT" | "ABSENT" | "LATE" | "EXCUSED";
const statuses: Status[] = ["PRESENT", "ABSENT", "LATE", "EXCUSED"];
const statusMeta: Record<Status, { icon: string; tone: "success" | "danger" | "warning" | "neutral" }> = { PRESENT: { icon: "✓", tone: "success" }, ABSENT: { icon: "×", tone: "danger" }, LATE: { icon: "◷", tone: "warning" }, EXCUSED: { icon: "!", tone: "neutral" } };

export default function AttendanceScreen() {
    const { groupId, date: dateParam } = useLocalSearchParams<{ groupId?: string; date?: string }>();
    const [selectedGroup, setSelectedGroup] = useState<string | undefined>(groupId);
    const [date] = useState(dateParam ?? new Date().toISOString().slice(0, 10));
    const [statusesByStudent, setStatuses] = useState<Record<string, Status>>({});
    const [saving, setSaving] = useState(false);
    const [saved, setSaved] = useState(false);
    const groups = useGroups(); const students = useGroupMembers(selectedGroup); const existing = useGroupAttendance(selectedGroup, date); const saveAttendance = useSaveGroupAttendance();
    const roster = students.data ?? [];
    const savedStatuses = existing.data?.records.reduce<Record<string, Status>>((result, record) => { result[record.student_id] = record.status; return result; }, {}) ?? {};
    const currentStatuses = Object.keys(statusesByStudent).length ? statusesByStudent : savedStatuses;
    const allPresent = useMemo(() => roster.length > 0 && roster.every((student) => currentStatuses[student.id] === "PRESENT"), [roster, currentStatuses]);
    const markAll = () => setStatuses(Object.fromEntries(roster.map((student) => [student.id, "PRESENT"])));
    const cycle = (studentId: string) => { const current = currentStatuses[studentId] ?? "PRESENT"; const next = statuses[(statuses.indexOf(current) + 1) % statuses.length]; setStatuses((value) => ({ ...value, [studentId]: next })); setSaved(false); };
    const save = async () => { if (!selectedGroup) return; setSaving(true); setSaved(false); try { await saveAttendance.mutateAsync({ groupId: selectedGroup, payload: { session_date: date, records: roster.map((student) => ({ student_id: student.id, status: currentStatuses[student.id] ?? "PRESENT" })) } }); setSaved(true); } finally { setSaving(false); } };
    if (groups.isLoading) return <Screen><LoadingState /></Screen>;
    if (groups.isError) return <Screen><ErrorState onRetry={() => void groups.refetch()} /></Screen>;
    return <Screen><ScrollView contentContainerStyle={styles.page}><PageHeader eyebrow="DAILY RHYTHM" title="Attendance" /><Text style={styles.date}>{date}</Text><SectionHeader title="Pick a group" /><ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.classRow}>{groups.data?.map((item) => <Pressable key={item.id} onPress={() => { setSelectedGroup(item.id); setStatuses({}); setSaved(false); }} style={[styles.classChip, selectedGroup === item.id && styles.classChipSelected]}><Text style={[styles.className, selectedGroup === item.id && styles.classNameSelected]}>{item.name}</Text><Text style={[styles.classSubject, selectedGroup === item.id && styles.classNameSelected]}>{item.student_count} active students</Text></Pressable>)}</ScrollView>{!selectedGroup ? <Card><Text style={styles.prompt}>Select a group to load its active roster.</Text></Card> : students.isLoading || existing.isLoading ? <LoadingState /> : students.isError || existing.isError ? <ErrorState onRetry={() => { void students.refetch(); void existing.refetch(); }} /> : <><View style={styles.toolbar}><Text style={styles.rosterTitle}>{roster.length} students</Text><Button variant="secondary" onPress={markAll}>{allPresent ? "All present" : "Mark all present"}</Button></View>{roster.map((student) => { const status = currentStatuses[student.id] ?? "PRESENT"; const meta = statusMeta[status]; return <Pressable key={student.id} onPress={() => cycle(student.id)}><View style={styles.studentRow}><Avatar name={`${student.first_name} ${student.last_name}`} size={40} /><View style={styles.studentCopy}><Text style={styles.studentName}>{student.first_name} {student.last_name}</Text><Text style={styles.tapHint}>Tap to change status</Text></View><Badge tone={meta.tone}>{meta.icon} {status}</Badge></View></Pressable>; })}<Button onPress={() => void save()} disabled={saving}>{saving ? "Saving..." : saved ? "Saved ✓" : "Save attendance"}</Button>{saved && <Text style={styles.success}>Attendance saved for {date}.</Text>}</>}</ScrollView></Screen>;
}
const styles = StyleSheet.create({ page: { paddingBottom: spacing.xxl, gap: spacing.md }, date: { ...typography.body, marginTop: -spacing.sm }, classRow: { gap: spacing.sm, paddingBottom: spacing.sm }, classChip: { backgroundColor: colors.white, borderRadius: 12, minWidth: 130, padding: spacing.md, ...{ borderColor: colors.line, borderWidth: 1 } }, classChipSelected: { backgroundColor: colors.ink, borderColor: colors.ink }, className: { ...typography.heading, fontSize: 15 }, classSubject: { ...typography.body, fontSize: 12, marginTop: 3 }, classNameSelected: { color: colors.white }, prompt: { ...typography.body }, toolbar: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", marginTop: spacing.md }, rosterTitle: typography.heading, studentRow: { alignItems: "center", backgroundColor: colors.white, borderRadius: 12, flexDirection: "row", marginBottom: spacing.sm, padding: spacing.md }, studentCopy: { flex: 1, marginHorizontal: spacing.md }, studentName: { ...typography.heading, fontSize: 15 }, tapHint: { ...typography.body, fontSize: 11, marginTop: 2 }, success: { color: colors.sage, fontWeight: "700", textAlign: "center" } });
