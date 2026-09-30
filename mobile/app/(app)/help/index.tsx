import { useState } from "react";
import { Alert, Linking, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import { MaterialCommunityIcons } from "@expo/vector-icons";

import { Button, Card, PageHeader, Screen } from "@/components";
import { colors, radius, spacing, typography } from "@/theme";

interface FAQItem {
    question: string;
    answer: string;
}

const FAQS: FAQItem[] = [
    {
        question: "How do I create and manage classes?",
        answer: "Go to the More tab or Classes screen and tap 'Create a class'. You can set the batch name, subject, and standard monthly fee. From the class hub, you can enroll students and assign teachers.",
    },
    {
        question: "How does daily attendance work?",
        answer: "Open the Attendance tab. Select the batch and date, then mark each student as Present, Absent, or Late. Tap 'Save attendance' to record the register. Attendance records immediately update dashboard stats.",
    },
    {
        question: "How do I generate and collect fees?",
        answer: "Navigate to Fees → Create fee. You can generate fees for an entire batch or record an individual student invoice. When a student or parent pays, open the fee row and record cash, UPI, or card payment to instantly issue a numbered receipt.",
    },
    {
        question: "How do I assign homework and record test marks?",
        answer: "Use the Homework and Tests screens under Academics in the More menu. Create assignments with due dates and test schedules with maximum marks. Tap on any test to enter and track individual scores and grades.",
    },
    {
        question: "How do parents and students access Tuiro?",
        answer: "Link parent phone numbers or email addresses in People → Parents. Once registered with their email, parents and students log in to see their specific batches, attendance history, assignments, and outstanding fee invoices.",
    },
];

export default function HelpScreen() {
    const [openIndex, setOpenIndex] = useState<number | null>(null);

    const toggleFaq = (index: number) => {
        setOpenIndex(openIndex === index ? null : index);
    };

    const handleEmailSupport = () => {
        Linking.openURL("mailto:support@tuiro.app?subject=Tuiro%20Support%20Request").catch(() => {
            Alert.alert("Contact Support", "Please email us at support@tuiro.app");
        });
    };

    return (
        <Screen>
            <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
                <PageHeader
                    eyebrow="SUPPORT"
                    title="Help & Support"
                    action={
                        <Button variant="secondary" size="sm" onPress={() => router.back()}>
                            Back
                        </Button>
                    }
                />

                <Card style={styles.contactCard}>
                    <View style={styles.iconBox}>
                        <MaterialCommunityIcons name="headset" size={28} color={colors.primary} />
                    </View>
                    <View style={styles.contactInfo}>
                        <Text style={styles.contactTitle}>Need assistance?</Text>
                        <Text style={styles.contactDesc}>
                            Our support team is here to help tuition center administrators, teachers, and parents.
                        </Text>
                    </View>
                    <Button size="sm" onPress={handleEmailSupport}>
                        Email Support
                    </Button>
                </Card>

                <Text style={styles.sectionTitle}>Frequently Asked Questions</Text>

                <View style={styles.faqList}>
                    {FAQS.map((faq, index) => {
                        const isOpen = openIndex === index;
                        return (
                            <Card key={index} style={styles.faqCard}>
                                <Pressable
                                    onPress={() => toggleFaq(index)}
                                    style={styles.faqHeader}
                                    accessibilityRole="button"
                                >
                                    <Text style={styles.faqQuestion}>{faq.question}</Text>
                                    <MaterialCommunityIcons
                                        name={isOpen ? "chevron-up" : "chevron-down"}
                                        size={22}
                                        color={colors.muted}
                                    />
                                </Pressable>
                                {isOpen && (
                                    <View style={styles.faqAnswerWrap}>
                                        <Text style={styles.faqAnswer}>{faq.answer}</Text>
                                    </View>
                                )}
                            </Card>
                        );
                    })}
                </View>

                <Card style={styles.versionCard}>
                    <Text style={styles.versionText}>Tuiro Management Platform</Text>
                    <Text style={styles.versionSub}>Version 1.0.0 · Production SaaS Build</Text>
                </Card>
            </ScrollView>
        </Screen>
    );
}

const styles = StyleSheet.create({
    content: {
        gap: spacing.md,
        paddingBottom: spacing.xxl,
        paddingTop: spacing.xs,
    },
    contactCard: {
        alignItems: "center",
        backgroundColor: colors.coralSoft,
        flexDirection: "row",
        gap: spacing.md,
        padding: spacing.md,
    },
    iconBox: {
        alignItems: "center",
        backgroundColor: colors.white,
        borderRadius: radius.md,
        height: 48,
        justifyContent: "center",
        width: 48,
    },
    contactInfo: {
        flex: 1,
    },
    contactTitle: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 16,
    },
    contactDesc: {
        ...typography.caption,
        color: colors.ink,
        marginTop: 2,
    },
    sectionTitle: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 17,
        marginTop: spacing.xs,
    },
    faqList: {
        gap: spacing.xs,
    },
    faqCard: {
        padding: spacing.md,
    },
    faqHeader: {
        alignItems: "center",
        flexDirection: "row",
        justifyContent: "space-between",
    },
    faqQuestion: {
        ...typography.heading,
        color: colors.ink,
        flex: 1,
        fontSize: 15,
        marginRight: spacing.sm,
    },
    faqAnswerWrap: {
        borderTopColor: colors.line,
        borderTopWidth: 1,
        marginTop: spacing.sm,
        paddingTop: spacing.sm,
    },
    faqAnswer: {
        ...typography.body,
        color: colors.muted,
        fontSize: 14,
        lineHeight: 20,
    },
    versionCard: {
        alignItems: "center",
        backgroundColor: colors.surface,
        marginTop: spacing.md,
        padding: spacing.md,
    },
    versionText: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 14,
    },
    versionSub: {
        ...typography.caption,
        color: colors.muted,
        marginTop: 2,
    },
});
