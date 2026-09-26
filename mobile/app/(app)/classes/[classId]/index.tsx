import { useMemo, useState } from "react";
import { Alert, Modal, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { router, useLocalSearchParams } from "expo-router";

import { useAddGroupMember, useGroup, useGroupMembers, useRemoveGroupMember, useStudents } from "@/api/hooks";
import { Avatar, Badge, Button, Card, EmptyState, ErrorState, IconButton, LoadingState, PageHeader, Screen, SearchBar, SectionHeader } from "@/components";
import { colors, radius, spacing, typography } from "@/theme";

export default function ClassDetailScreen() {
    const params = useLocalSearchParams<{ classId?: string; groupId?: string }>();
    const classId = params.classId || params.groupId || "";
    const group = useGroup(classId);
    const members = useGroupMembers(classId);
    const students = useStudents();
    const add = useAddGroupMember();
    const remove = useRemoveGroupMember();

    const [open, setOpen] = useState(false);
    const [search, setSearch] = useState("");
    const [selected, setSelected] = useState<string[]>([]);

    const memberList = members.data ?? [];
    const memberIds = useMemo(() => new Set(memberList.map((s) => s.id)), [memberList]);
    const candidates = useMemo(() => {
        return (students.data ?? []).filter(
            (s) =>
                !memberIds.has(s.id) &&
                `${s.first_name} ${s.last_name}`.toLowerCase().includes(search.toLowerCase())
        );
    }, [students.data, memberIds, search]);

    const confirmAdd = async () => {
        if (!selected.length || !classId) return;
        try {
            await Promise.all(selected.map((studentId) => add.mutateAsync({ groupId: classId, studentId })));
            setSelected([]);
            setOpen(false);
        } catch {
            Alert.alert("Could not add students", "Please try again.");
        }
    };

    const confirmRemove = (studentId: string, studentName: string) => {
        Alert.alert(
            `Remove ${studentName}?`,
            "Their attendance and fee records stay intact. They will no longer be listed in this batch.",
            [
                { text: "Cancel", style: "cancel" },
                {
                    text: "Remove",
                    style: "destructive",
                    onPress: () => {
                        if (classId) {
                            void remove.mutateAsync({ groupId: classId, studentId });
                        }
                    },
                },
            ]
        );
    };

    if (group.isLoading || members.isLoading || students.isLoading) {
        return <Screen><LoadingState /></Screen>;
    }

    if (group.isError || members.isError || students.isError || !group.data) {
        return (
            <Screen>
                <ErrorState
                    onRetry={() => {
                        void group.refetch();
                        void members.refetch();
                        void students.refetch();
                    }}
                />
            </Screen>
        );
    }

    return (
        <Screen>
            <PageHeader
                eyebrow="CLASS / BATCH"
                title={group.data.name}
                right={
                    <IconButton
                        label="Back"
                        onPress={() => router.back()}
                        icon={<MaterialCommunityIcons name="arrow-left" size={22} color={colors.ink} />}
                    />
                }
            />

            <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
                {/* Hero card */}
                <View style={styles.heroCard}>
                    <View>
                        <Text style={styles.heroKicker}>ACTIVE ROSTER</Text>
                        <Text style={styles.heroNumber}>{memberList.length}</Text>
                        <Text style={styles.heroLabel}>
                            {memberList.length === 1 ? "student enrolled" : "students learning together"}
                        </Text>
                    </View>
                    <View style={styles.quickNavRow}>
                        <Pressable
                            style={styles.quickNavChip}
                            onPress={() => router.push({ pathname: "/(app)/(tabs)/attendance", params: { groupId: classId } } as never)}
                        >
                            <MaterialCommunityIcons name="calendar-check" size={16} color={colors.white} />
                            <Text style={styles.quickNavText}>Mark Attendance</Text>
                        </Pressable>
                    </View>
                </View>

                {/* Section Header */}
                <SectionHeader
                    title="Students in batch"
                    action={
                        <Button variant="ghost" onPress={() => setOpen(true)}>
                            + Add Student
                        </Button>
                    }
                />

                {/* Member list */}
                {memberList.length > 0 ? (
                    <View style={styles.rosterCard}>
                        {memberList.map((student, idx) => (
                            <View
                                key={student.id}
                                style={[styles.memberRow, idx === memberList.length - 1 && styles.memberRowLast]}
                            >
                                <Avatar name={`${student.first_name} ${student.last_name}`} size={42} />
                                <View style={styles.memberInfo}>
                                    <Text style={styles.memberName}>
                                        {student.first_name} {student.last_name}
                                    </Text>
                                    <Text style={styles.memberMeta}>
                                        {student.grade ? student.grade : "Student"}
                                        {student.student_number ? ` · #${student.student_number}` : ""}
                                    </Text>
                                </View>
                                <Pressable
                                    onPress={() => confirmRemove(student.id, `${student.first_name} ${student.last_name}`)}
                                    style={styles.removeBtn}
                                    accessibilityRole="button"
                                >
                                    <Text style={styles.removeText}>Remove</Text>
                                </Pressable>
                            </View>
                        ))}
                    </View>
                ) : (
                    <EmptyState
                        icon="👥"
                        title="No students yet"
                        message="Add students from your centre to start sharing work and fees."
                        action={<Button onPress={() => setOpen(true)}>+ Add Student</Button>}
                    />
                )}
            </ScrollView>

            {/* Searchable Add Students Modal */}
            <Modal visible={open} transparent animationType="slide" onRequestClose={() => setOpen(false)}>
                <View style={styles.modalOverlay}>
                    <View style={styles.sheet}>
                        <View style={styles.sheetHeader}>
                            <Text style={styles.sheetTitle}>Add students to batch</Text>
                            <Pressable onPress={() => setOpen(false)}>
                                <MaterialCommunityIcons name="close" size={24} color={colors.ink} />
                            </Pressable>
                        </View>

                        <SearchBar
                            value={search}
                            onChangeText={setSearch}
                            placeholder="Search students by name..."
                        />

                        <ScrollView contentContainerStyle={styles.candidateList} showsVerticalScrollIndicator={false}>
                            {candidates.length > 0 ? (
                                candidates.map((student) => {
                                    const checked = selected.includes(student.id);
                                    return (
                                        <Pressable
                                            key={student.id}
                                            onPress={() =>
                                                setSelected((prev) =>
                                                    checked ? prev.filter((id) => id !== student.id) : [...prev, student.id]
                                                )
                                            }
                                        >
                                            <Card style={[styles.candidateCard, checked && styles.candidateSelected]}>
                                                <Avatar name={`${student.first_name} ${student.last_name}`} size={38} />
                                                <View style={styles.candidateInfo}>
                                                    <Text style={styles.memberName}>
                                                        {student.first_name} {student.last_name}
                                                    </Text>
                                                    <Text style={styles.memberMeta}>
                                                        {student.grade ?? "Student"}
                                                        {student.student_number ? ` · #${student.student_number}` : ""}
                                                    </Text>
                                                </View>
                                                <View style={[styles.checkbox, checked && styles.checkboxActive]}>
                                                    {checked ? (
                                                        <MaterialCommunityIcons name="check" size={16} color={colors.white} />
                                                    ) : (
                                                        <MaterialCommunityIcons name="plus" size={16} color={colors.muted} />
                                                    )}
                                                </View>
                                            </Card>
                                        </Pressable>
                                    );
                                })
                            ) : (
                                <Text style={styles.noCandidatesText}>
                                    {search.trim() ? "No matching students found." : "All registered students are already in this batch."}
                                </Text>
                            )}
                        </ScrollView>

                        <View style={styles.modalActions}>
                            <Button variant="secondary" onPress={() => setOpen(false)}>Cancel</Button>
                            <Button
                                disabled={!selected.length || add.isPending}
                                onPress={() => void confirmAdd()}
                            >
                                {add.isPending
                                    ? "Adding..."
                                    : `Add ${selected.length} student${selected.length === 1 ? "" : "s"}`}
                            </Button>
                        </View>
                    </View>
                </View>
            </Modal>
        </Screen>
    );
}

const styles = StyleSheet.create({
    content: {
        gap: spacing.lg,
        paddingBottom: spacing.xxl,
        paddingTop: spacing.xs,
    },
    heroCard: {
        backgroundColor: colors.ink,
        borderRadius: radius.lg,
        padding: spacing.xl,
        position: "relative",
    },
    heroKicker: {
        color: colors.primary,
        fontSize: 11,
        fontWeight: "800",
        letterSpacing: 1.2,
    },
    heroNumber: {
        ...typography.display,
        color: colors.white,
        fontSize: 48,
        fontWeight: "800",
        marginTop: spacing.xs,
    },
    heroLabel: {
        color: "#C5D0C9",
        fontSize: 14,
        fontWeight: "500",
        marginTop: 2,
    },
    quickNavRow: {
        flexDirection: "row",
        gap: spacing.sm,
        marginTop: spacing.lg,
    },
    quickNavChip: {
        alignItems: "center",
        backgroundColor: colors.primary,
        borderRadius: radius.md,
        flexDirection: "row",
        gap: 6,
        paddingHorizontal: spacing.md,
        paddingVertical: 8,
    },
    quickNavText: {
        color: colors.white,
        fontSize: 13,
        fontWeight: "700",
    },
    rosterCard: {
        backgroundColor: colors.white,
        borderColor: colors.line,
        borderRadius: radius.md,
        borderWidth: 1,
        overflow: "hidden",
    },
    memberRow: {
        alignItems: "center",
        borderBottomColor: colors.line,
        borderBottomWidth: 1,
        flexDirection: "row",
        paddingHorizontal: spacing.md,
        paddingVertical: spacing.md,
    },
    memberRowLast: {
        borderBottomWidth: 0,
    },
    memberInfo: {
        flex: 1,
        marginHorizontal: spacing.md,
    },
    memberName: {
        ...typography.heading,
        fontSize: 15,
        color: colors.ink,
    },
    memberMeta: {
        ...typography.caption,
        marginTop: 2,
    },
    removeBtn: {
        paddingHorizontal: spacing.sm,
        paddingVertical: 6,
    },
    removeText: {
        color: colors.red,
        fontSize: 13,
        fontWeight: "700",
    },
    modalOverlay: {
        backgroundColor: "rgba(20,28,40,.45)",
        flex: 1,
        justifyContent: "flex-end",
    },
    sheet: {
        backgroundColor: colors.paper,
        borderTopLeftRadius: 28,
        borderTopRightRadius: 28,
        maxHeight: "85%",
        padding: spacing.xl,
    },
    sheetHeader: {
        alignItems: "center",
        flexDirection: "row",
        justifyContent: "space-between",
        marginBottom: spacing.md,
    },
    sheetTitle: {
        ...typography.display,
        fontSize: 22,
    },
    candidateList: {
        gap: spacing.xs,
        paddingVertical: spacing.md,
    },
    candidateCard: {
        alignItems: "center",
        flexDirection: "row",
        padding: spacing.md,
    },
    candidateSelected: {
        borderColor: colors.primary,
        borderWidth: 2,
    },
    candidateInfo: {
        flex: 1,
        marginHorizontal: spacing.md,
    },
    checkbox: {
        alignItems: "center",
        borderColor: colors.line,
        borderRadius: 18,
        borderWidth: 2,
        height: 28,
        justifyContent: "center",
        width: 28,
    },
    checkboxActive: {
        backgroundColor: colors.primary,
        borderColor: colors.primary,
    },
    noCandidatesText: {
        ...typography.caption,
        paddingVertical: spacing.xl,
        textAlign: "center",
    },
    modalActions: {
        flexDirection: "row",
        gap: spacing.sm,
        justifyContent: "flex-end",
        marginTop: spacing.md,
    },
});
