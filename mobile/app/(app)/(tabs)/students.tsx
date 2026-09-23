import { useState } from "react";
import { Alert, FlatList, Modal, Pressable, StyleSheet, Text, View } from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { router, useLocalSearchParams } from "expo-router";

import { useCreateStudent, useStudents } from "@/api/hooks";
import { apiErrorMessage } from "@/api/client";
import { Avatar, Badge, Button, EmptyState, ErrorState, IconButton, LoadingState, PageHeader, Screen, SearchBar, TuiroInput } from "@/components";
import { colors, spacing, typography } from "@/theme";

type Student = { id: string; first_name: string; last_name: string; student_number: string; grade?: string; status: string };

export default function StudentsScreen() {
    const { new: openNew } = useLocalSearchParams<{ new?: string }>();
    const [search, setSearch] = useState("");
    const [showForm, setShowForm] = useState(openNew === "1");
    const [firstName, setFirstName] = useState("");
    const [studentNumber, setStudentNumber] = useState("");
    const [grade, setGrade] = useState("");
    const query = useStudents(search);
    const createStudent = useCreateStudent();
    const submit = async () => {
        if (!firstName.trim() || !studentNumber.trim()) { Alert.alert("Missing details", "Enter a student name and student number."); return; }
        try { await createStudent.mutateAsync({ first_name: firstName.trim(), last_name: "", student_number: studentNumber.trim(), grade: grade.trim() || null }); setFirstName(""); setStudentNumber(""); setGrade(""); setShowForm(false); }
        catch (error) { Alert.alert("Unable to add student", apiErrorMessage(error, "Please check the student details and try again.")); }
    };
    if (query.isLoading) return <Screen><LoadingState /></Screen>;
    if (query.isError) return <Screen><ErrorState onRetry={() => void query.refetch()} /></Screen>;
    return <Screen><PageHeader eyebrow="DIRECTORY" title="Students" right={<IconButton label="Add student" onPress={() => setShowForm(true)} icon={<MaterialCommunityIcons name="plus" color="#fff" size={22} />} tone="primary" />} /><Text style={styles.count}>{query.data?.length ?? 0} active students</Text><SearchBar value={search} onChangeText={setSearch} placeholder="Search students" /><FlatList showsVerticalScrollIndicator={false} contentContainerStyle={styles.list} data={query.data} keyExtractor={(item) => item.id} keyboardShouldPersistTaps="handled" refreshing={query.isRefetching} onRefresh={() => void query.refetch()} ListEmptyComponent={<EmptyState icon="👨‍🎓" title={search ? "No matches" : "No students yet"} message={search ? "Try a different name or student number." : "Add your first student to get started."} />} renderItem={({ item }) => <Pressable onPress={() => router.push(`/students/${item.id}` as never)} style={styles.row}><Avatar name={`${item.first_name} ${item.last_name}`} /><View style={styles.copy}><Text style={styles.name}>{item.first_name} {item.last_name}</Text><Text style={styles.meta}>{item.grade ?? "Student"} · {item.student_number}</Text></View><View style={styles.trailing}><Badge tone={item.status === "ACTIVE" ? "success" : "neutral"}>{item.status}</Badge><MaterialCommunityIcons name="chevron-right" color={colors.muted} size={20} /></View></Pressable>} /><Modal visible={showForm} transparent animationType="slide" onRequestClose={() => setShowForm(false)}><View style={styles.modal}><View style={styles.sheet}><Text style={styles.formTitle}>Add student</Text><TuiroInput label="Student name" value={firstName} onChangeText={setFirstName} autoFocus /><TuiroInput label="Student number" value={studentNumber} onChangeText={setStudentNumber} /><TuiroInput label="Grade (optional)" value={grade} onChangeText={setGrade} /><View style={styles.formActions}><Button variant="ghost" onPress={() => setShowForm(false)}>Cancel</Button><Button disabled={createStudent.isPending} onPress={() => void submit()}>{createStudent.isPending ? "Saving..." : "Save student"}</Button></View></View></View></Modal></Screen>;
}

const styles = StyleSheet.create({ count: { ...typography.body, marginBottom: spacing.md, marginTop: -spacing.lg }, list: { paddingTop: spacing.lg, paddingBottom: spacing.xxl, gap: spacing.sm, flexGrow: 1 }, row: { alignItems: "center", backgroundColor: colors.white, borderRadius: 12, flexDirection: "row", padding: spacing.md }, copy: { flex: 1, marginHorizontal: spacing.md }, name: { ...typography.heading, fontSize: 16 }, meta: { ...typography.body, fontSize: 13, marginTop: 3 }, trailing: { alignItems: "flex-end", gap: spacing.xs }, modal: { backgroundColor: "rgba(20,28,40,0.35)", flex: 1, justifyContent: "flex-end" }, sheet: { backgroundColor: colors.paper, borderTopLeftRadius: 28, borderTopRightRadius: 28, padding: spacing.xl }, formTitle: { ...typography.display, fontSize: 24 }, formActions: { flexDirection: "row", gap: spacing.sm, justifyContent: "flex-end", marginTop: spacing.xl } });
