import { router } from "expo-router";
import { ScrollView, StyleSheet, Text, View } from "react-native";

import { Button, Card, FeatureCard, PageHeader, Screen } from "./ui";
import { colors, spacing, typography } from "@/theme";

export function ClassHub({ classId }: { classId: string }) {
    const destinations = [
        ["Students", "Class roster", `/classes/${classId}/students`],
        ["Attendance", "Mark or review", `/classes/${classId}/attendance`],
        ["Homework", "Assignments", `/classes/${classId}/homework`],
        ["Tests", "Assessments", `/classes/${classId}/tests`],
        ["Schedule", "Class times", `/classes/${classId}/schedule`],
    ] as const;
    return <Screen><ScrollView contentContainerStyle={styles.content}><PageHeader eyebrow="CLASS" title="Class details" /><Card><Text style={styles.copy}>Use this class as the hub for its roster, daily register, and academic work.</Text></Card><View style={styles.grid}>{destinations.map(([title, subtitle, href]) => <FeatureCard key={title} title={title} subtitle={subtitle} icon="→" color={colors.featureBlue} onPress={() => router.push(href as never)} />)}</View></ScrollView></Screen>;
}

export function StudentHub({ studentId }: { studentId: string }) {
    const destinations = [
        ["Attendance", `/students/${studentId}/attendance`], ["Fees", `/students/${studentId}/fees`], ["Homework", `/students/${studentId}/homework`], ["Tests", `/students/${studentId}/tests`], ["Parent", `/students/${studentId}/parent`],
    ] as const;
    return <Screen><ScrollView contentContainerStyle={styles.content}><PageHeader eyebrow="STUDENT" title="Student details" /><Card><Text style={styles.copy}>Student-specific attendance, billing, and academic records are grouped here.</Text></Card><View style={styles.grid}>{destinations.map(([title, href]) => <FeatureCard key={title} title={title} icon="→" color={colors.featureBlue} onPress={() => router.push(href as never)} />)}</View></ScrollView></Screen>;
}

export function ContextScreen({ title, eyebrow = "DETAIL" }: { title: string; eyebrow?: string }) {
    return <Screen><ScrollView contentContainerStyle={styles.content}><PageHeader eyebrow={eyebrow} title={title} /><Card><Text style={styles.copy}>This route is ready for its contextual view. Existing centre-wide workflows remain available from their primary screens while their class- and student-specific views are introduced.</Text></Card><Button variant="secondary" onPress={() => router.back()}>Back</Button></ScrollView></Screen>;
}

const styles = StyleSheet.create({ content: { gap: spacing.md, paddingBottom: spacing.xxl, paddingTop: spacing.lg }, copy: { ...typography.body, lineHeight: 21 }, grid: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm } });
