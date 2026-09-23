import { ScrollView, StyleSheet, Text } from "react-native";
import { useLocalSearchParams } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { groupsApi } from "@/api/groups";
import { Card, ErrorState, LoadingState, PageHeader, Screen } from "@/components";
import { spacing, typography } from "@/theme";
export default function StudentHomeworkScreen() { const { studentId } = useLocalSearchParams<{ studentId: string }>(); const query = useQuery({ queryKey: ["student-group-view", studentId], queryFn: () => groupsApi.studentView(studentId), enabled: Boolean(studentId) }); if (query.isLoading) return <Screen><LoadingState /></Screen>; if (query.isError) return <Screen><ErrorState onRetry={() => void query.refetch()} /></Screen>; return <Screen><ScrollView contentContainerStyle={styles.content}><PageHeader eyebrow="STUDENT" title="Homework" />{query.data?.assignments.map((item) => <Card key={item.id}><Text style={styles.title}>{item.title}</Text><Text style={styles.meta}>{item.source === "Group" ? `From: ${item.group_name ?? "Group"}` : "Individual"}{item.due_date ? ` · Due ${item.due_date}` : ""}</Text><Text style={styles.meta}>{item.description}</Text></Card>)}</ScrollView></Screen>; }
const styles = StyleSheet.create({ content: { gap: spacing.sm, paddingTop: spacing.lg }, title: { ...typography.heading }, meta: { ...typography.body, marginTop: spacing.xs } });
