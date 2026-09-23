import { ScrollView, StyleSheet, Text } from "react-native";
import { useLocalSearchParams } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { groupsApi } from "@/api/groups";
import { Card, ErrorState, LoadingState, PageHeader, Screen } from "@/components";
import { spacing, typography } from "@/theme";
export default function StudentAttendanceScreen() { const { studentId } = useLocalSearchParams<{ studentId: string }>(); const query = useQuery({ queryKey: ["student-group-attendance", studentId], queryFn: () => groupsApi.studentAttendance(studentId), enabled: Boolean(studentId) }); if (query.isLoading) return <Screen><LoadingState /></Screen>; if (query.isError) return <Screen><ErrorState onRetry={() => void query.refetch()} /></Screen>; return <Screen><ScrollView contentContainerStyle={styles.content}><PageHeader eyebrow="STUDENT" title="Attendance history" />{query.data?.map((item: { id: string; status: string }) => <Card key={item.id}><Text style={styles.title}>{item.status}</Text><Text style={styles.meta}>Group attendance record</Text></Card>)}</ScrollView></Screen>; }
const styles = StyleSheet.create({ content: { gap: spacing.sm, paddingTop: spacing.lg }, title: typography.heading, meta: { ...typography.body, marginTop: spacing.xs } });
