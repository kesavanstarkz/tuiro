import { useState } from "react";
import { Alert, FlatList, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { router } from "expo-router";

import { useAssignments, useCreateGroupAssignment, useDeleteAssignment, useGroups, useStudents } from "@/api/hooks";
import { Badge, Button, Card, EmptyState, ErrorState, LoadingState, PageHeader, Screen, TuiroInput } from "@/components";
import { colors, radius, spacing, typography } from "@/theme";

export default function HomeworkScreen() {
    const [tab, setTab] = useState<"add" | "list">("add");
    const [individual, setIndividual] = useState(false);
    const [target, setTarget] = useState("");
    const [title, setTitle] = useState("");
    const [description, setDescription] = useState("");
    const [dueDate, setDueDate] = useState("");

    const groups = useGroups();
    const students = useStudents();
    const assignments = useAssignments("assignment");
    const create = useCreateGroupAssignment();
    const remove = useDeleteAssignment();

    if (groups.isLoading || students.isLoading || assignments.isLoading) {
        return <Screen><LoadingState /></Screen>;
    }
    if (groups.isError || students.isError) {
        return (
            <Screen>
                <ErrorState
                    onRetry={() => {
                        void groups.refetch();
                        void students.refetch();
                        void assignments.refetch();
                    }}
                />
            </Screen>
        );
    }

    const groupList = groups.data ?? [];
    const studentList = students.data ?? [];
    const assignmentList = assignments.data ?? [];

    const submit = async () => {
        if (!target || !title.trim()) {
            return Alert.alert("Complete the assignment", "Choose a group or student and enter a title.");
        }
        try {
            await create.mutateAsync(
                individual
                    ? { student_id: target, title: title.trim(), description: description.trim() || undefined, due_date: dueDate || undefined, type: "assignment" }
                    : { group_id: target, title: title.trim(), description: description.trim() || undefined, due_date: dueDate || undefined, type: "assignment" }
            );
            Alert.alert("Homework added", "The assignment has been successfully recorded.");
            setTarget("");
            setTitle("");
            setDescription("");
            setDueDate("");
            setTab("list");
        } catch {
            Alert.alert("Could not add homework", "Please try again.");
        }
    };

    const confirmDelete = (id: string, itemTitle: string) => {
        Alert.alert(
            "Delete assignment?",
            `Are you sure you want to remove "${itemTitle}"?`,
            [
                { text: "Cancel", style: "cancel" },
                {
                    text: "Delete",
                    style: "destructive",
                    onPress: () => void remove.mutateAsync(id),
                },
            ]
        );
    };

    const choices = individual ? studentList : groupList;

    return (
        <Screen>
            <PageHeader eyebrow="ACADEMICS" title="Homework" />

            {/* Segmented Tab */}
            <View style={styles.segmentContainer}>
                <Pressable
                    style={[styles.segmentBtn, tab === "add" && styles.segmentBtnActive]}
                    onPress={() => setTab("add")}
                >
                    <Text style={[styles.segmentText, tab === "add" && styles.segmentTextActive]}>
                        + Add Work
                    </Text>
                </Pressable>
                <Pressable
                    style={[styles.segmentBtn, tab === "list" && styles.segmentBtnActive]}
                    onPress={() => setTab("list")}
                >
                    <Text style={[styles.segmentText, tab === "list" && styles.segmentTextActive]}>
                        Assignments ({assignmentList.length})
                    </Text>
                </Pressable>
            </View>

            {tab === "add" ? (
                <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
                    {/* Step 1 */}
                    <View style={styles.stepHeader}>
                        <Text style={styles.stepNumber}>01</Text>
                        <View style={styles.stepCopy}>
                            <Text style={styles.stepTitle}>Pick who this work is for</Text>
                            <Text style={styles.stepHint}>Batches are the default. Use individual only for an exception.</Text>
                        </View>
                    </View>

                    <View style={styles.modeRow}>
                        <Button
                            variant={individual ? "secondary" : "primary"}
                            onPress={() => {
                                setIndividual(false);
                                setTarget("");
                            }}
                        >
                            Group batch
                        </Button>
                        <Button
                            variant={individual ? "primary" : "secondary"}
                            onPress={() => {
                                setIndividual(true);
                                setTarget("");
                            }}
                        >
                            Individual student
                        </Button>
                    </View>

                    {!individual && groupList.length === 0 ? (
                        <EmptyState
                            icon="🏫"
                            title="Create a class first"
                            message="Homework needs a class roster. Add your first batch before creating work."
                            action={<Button onPress={() => router.push("/(app)/classes")}>Create a class</Button>}
                        />
                    ) : (
                        <>
                            <Text style={styles.label}>{individual ? "Choose student" : "Choose class batch"}</Text>
                            <View style={styles.choicesWrap}>
                                {choices.map((item) => {
                                    const isSelected = target === item.id;
                                    const itemTitle = "name" in item ? item.name : `${item.first_name} ${item.last_name}`;
                                    const meta = "student_count" in item ? `${item.student_count} active students` : item.grade ?? "Student";

                                    return (
                                        <Pressable key={item.id} onPress={() => setTarget(item.id)}>
                                            <Card style={[styles.choiceCard, isSelected && styles.choiceSelected]}>
                                                <View style={styles.choiceCopy}>
                                                    <Text style={[styles.choiceName, isSelected && styles.choiceNameSelected]}>
                                                        {itemTitle}
                                                    </Text>
                                                    <Text style={styles.choiceMeta}>{meta}</Text>
                                                </View>
                                                <View style={[styles.radio, isSelected && styles.radioActive]}>
                                                    {isSelected && <View style={styles.radioInner} />}
                                                </View>
                                            </Card>
                                        </Pressable>
                                    );
                                })}
                            </View>

                            {/* Step 2 */}
                            <View style={styles.stepHeader}>
                                <Text style={styles.stepNumber}>02</Text>
                                <View style={styles.stepCopy}>
                                    <Text style={styles.stepTitle}>The work</Text>
                                    <Text style={styles.stepHint}>Title, instructions, and target due date.</Text>
                                </View>
                            </View>

                            <TuiroInput
                                label="Title"
                                value={title}
                                onChangeText={setTitle}
                                placeholder="Trigonometry Chapter 4 Revision"
                            />
                            <TuiroInput
                                label="Description"
                                value={description}
                                onChangeText={setDescription}
                                placeholder="Complete exercise problems 1 to 20 in notebook"
                                multiline
                            />
                            <TuiroInput
                                label="Due date (YYYY-MM-DD)"
                                value={dueDate}
                                onChangeText={setDueDate}
                                placeholder="2026-10-01"
                            />

                            <Button disabled={create.isPending || !target || !title.trim()} onPress={() => void submit()}>
                                {create.isPending ? "Adding..." : "Add work"}
                            </Button>
                        </>
                    )}
                </ScrollView>
            ) : (
                <FlatList
                    contentContainerStyle={styles.listContainer}
                    data={assignmentList}
                    keyExtractor={(item) => item.id}
                    showsVerticalScrollIndicator={false}
                    ListEmptyComponent={
                        <EmptyState
                            icon="📖"
                            title="No homework assigned yet"
                            message="Switch to Add Work above to give assignments to your students."
                            action={<Button onPress={() => setTab("add")}>+ Add Work</Button>}
                        />
                    }
                    renderItem={({ item }) => (
                        <Card style={styles.hwCard}>
                            <View style={styles.hwHeader}>
                                <View style={styles.hwInfo}>
                                    <Text style={styles.hwTitle}>{item.title}</Text>
                                    <Text style={styles.hwTarget}>
                                        {item.source === "Group" ? `Batch: ${item.target_name}` : `Student: ${item.target_name}`}
                                        {item.due_date ? ` · Due ${item.due_date}` : ""}
                                    </Text>
                                </View>
                                <Pressable
                                    onPress={() => confirmDelete(item.id, item.title)}
                                    style={styles.deleteBtn}
                                    accessibilityRole="button"
                                >
                                    <MaterialCommunityIcons name="trash-can-outline" size={20} color={colors.red} />
                                </Pressable>
                            </View>
                            {Boolean(item.description) && (
                                <Text style={styles.hwDescription}>{item.description}</Text>
                            )}
                        </Card>
                    )}
                />
            )}
        </Screen>
    );
}

const styles = StyleSheet.create({
    segmentContainer: {
        backgroundColor: colors.white,
        borderColor: colors.line,
        borderRadius: radius.md,
        borderWidth: 1,
        flexDirection: "row",
        marginBottom: spacing.md,
        padding: 4,
    },
    segmentBtn: {
        alignItems: "center",
        borderRadius: radius.sm,
        flex: 1,
        paddingVertical: 10,
    },
    segmentBtnActive: {
        backgroundColor: colors.ink,
    },
    segmentText: {
        color: colors.ink,
        fontSize: 14,
        fontWeight: "700",
    },
    segmentTextActive: {
        color: colors.white,
    },
    content: {
        gap: spacing.md,
        paddingBottom: spacing.xxl,
    },
    stepHeader: {
        alignItems: "center",
        backgroundColor: colors.coralSoft,
        borderRadius: radius.md,
        flexDirection: "row",
        gap: spacing.md,
        marginTop: spacing.xs,
        padding: spacing.md,
    },
    stepNumber: {
        color: colors.primary,
        fontFamily: typography.display.fontFamily,
        fontSize: 26,
        fontWeight: "800",
    },
    stepCopy: {
        flex: 1,
    },
    stepTitle: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 16,
    },
    stepHint: {
        ...typography.caption,
        marginTop: 2,
    },
    modeRow: {
        flexDirection: "row",
        gap: spacing.sm,
    },
    label: {
        ...typography.label,
        color: colors.ink,
        marginTop: spacing.xs,
    },
    choicesWrap: {
        gap: spacing.xs,
    },
    choiceCard: {
        alignItems: "center",
        flexDirection: "row",
        padding: spacing.md,
    },
    choiceSelected: {
        borderColor: colors.primary,
        borderWidth: 2,
    },
    choiceCopy: {
        flex: 1,
    },
    choiceName: {
        ...typography.heading,
        fontSize: 15,
        color: colors.ink,
    },
    choiceNameSelected: {
        color: colors.primary,
    },
    choiceMeta: {
        ...typography.caption,
        marginTop: 2,
    },
    radio: {
        alignItems: "center",
        borderColor: colors.line,
        borderRadius: 12,
        borderWidth: 2,
        height: 22,
        justifyContent: "center",
        width: 22,
    },
    radioActive: {
        borderColor: colors.primary,
    },
    radioInner: {
        backgroundColor: colors.primary,
        borderRadius: 6,
        height: 12,
        width: 12,
    },
    listContainer: {
        gap: spacing.sm,
        paddingBottom: spacing.xxl,
    },
    hwCard: {
        padding: spacing.md,
    },
    hwHeader: {
        alignItems: "flex-start",
        flexDirection: "row",
        justifyContent: "space-between",
    },
    hwInfo: {
        flex: 1,
        marginRight: spacing.sm,
    },
    hwTitle: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 16,
    },
    hwTarget: {
        ...typography.caption,
        color: colors.primary,
        fontWeight: "600",
        marginTop: 3,
    },
    hwDescription: {
        ...typography.body,
        color: colors.ink,
        marginTop: spacing.sm,
    },
    deleteBtn: {
        padding: 4,
    },
});
