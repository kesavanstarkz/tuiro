import { MaterialCommunityIcons } from "@expo/vector-icons";
import { router } from "expo-router";
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { useDashboard, useGroups } from "@/api/hooks";
import { Avatar, Badge, Card, EmptyState, ErrorState, IconButton, LoadingState, Screen, SectionHeader } from "@/components";
import { useAuthStore } from "@/store/auth";
import { colors, radius, spacing, typography } from "@/theme";

type Dashboard = {
    students: number;
    classes_today: number;
    attendance_percentage: number;
    pending_fees: string | number;
    currency_code: string;
    next_class: {
        class_id?: string;
        class_name: string;
        subject?: string;
        start_time: string;
        end_time: string;
        student_count: number;
    } | null;
    pending_fee_items: Array<{
        id: string;
        student_name: string;
        billing_period: string;
        amount: string | number;
        due_date: string;
        status: string;
    }>;
    recent_payments: Array<{
        id: string;
        student_name: string;
        amount: string | number;
        payment_method: string;
        payment_date: string;
    }>;
};

const icon = (name: keyof typeof MaterialCommunityIcons.glyphMap, color: string, size = 21) => (
    <MaterialCommunityIcons name={name} color={color} size={size} />
);

const money = (value: string | number, currency = "INR") =>
    new Intl.NumberFormat("en-IN", { style: "currency", currency, maximumFractionDigits: 0 }).format(Number(value) || 0);

export default function DashboardScreen() {
    const user = useAuthStore((state) => state.user);
    const query = useDashboard();
    const groups = useGroups();

    if (query.isLoading || groups.isLoading) return <Screen><LoadingState /></Screen>;
    if (query.isError) return <Screen><ErrorState onRetry={() => { void query.refetch(); void groups.refetch(); }} /></Screen>;

    const data = query.data as Dashboard;
    const hasClasses = (groups.data?.length ?? 0) > 0;
    const firstName = user?.display_name?.split(" ")[0] ?? "there";
    const date = new Intl.DateTimeFormat(undefined, { weekday: "long", month: "short", day: "numeric" }).format(new Date());
    const progress = Math.min(100, Math.max(0, Math.round(data.attendance_percentage || 0)));

    const handleAttendancePress = () => {
        if (!hasClasses) {
            Alert.alert(
                "Create a class first",
                "Attendance requires at least one class roster. Create a class to get started.",
                [
                    { text: "Cancel", style: "cancel" },
                    { text: "Create class", onPress: () => router.push("/(app)/classes") },
                ]
            );
            return;
        }
        router.push("/(app)/(tabs)/attendance");
    };

    return (
        <Screen>
            <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.content}>
                {/* Greeting Header */}
                <View style={styles.top}>
                    <View>
                        <Text style={styles.greeting}>Hello, {firstName}</Text>
                        <Text style={styles.date}>{date}</Text>
                    </View>
                    <View style={styles.topRight}>
                        <IconButton
                            label="Notifications"
                            onPress={() => router.push("/(app)/notifications")}
                            icon={icon("bell-outline", colors.ink, 22)}
                        />
                        <Avatar name={user?.display_name ?? "Tuiro"} size={44} />
                    </View>
                </View>

                {/* Day status pill */}
                <View style={styles.status}>
                    <View style={styles.statusDot} />
                    <Text style={styles.statusCopy}>
                        {data.classes_today ? `${data.classes_today} class${data.classes_today === 1 ? "" : "es"} on your schedule` : "Your day is clear"}
                    </Text>
                    <Pressable onPress={() => router.push("/(app)/schedule")}>
                        <Text style={styles.statusLink}>View schedule</Text>
                    </Pressable>
                </View>

                {/* Attendance Hero Card */}
                <View style={styles.attendanceHero}>
                    <View style={styles.heroCopy}>
                        <Text style={styles.heroLabel}>TODAY’S ATTENDANCE</Text>
                        <Text style={styles.heroValue}>{progress}%</Text>
                        <Text style={styles.heroText}>
                            {progress > 0 ? "Register is in progress" : "Ready when you are"}
                        </Text>
                        <Pressable onPress={handleAttendancePress}>
                            <Text style={styles.heroAction}>Mark attendance →</Text>
                        </Pressable>
                    </View>
                    <View style={styles.ringOuter}>
                        <View style={styles.ringInner}>
                            <Text style={styles.ringValue}>{progress}%</Text>
                            <Text style={styles.ringLabel}>DONE</Text>
                        </View>
                    </View>
                </View>

                {/* Stat Tiles */}
                <View style={styles.secondaryStats}>
                    <View style={styles.stat}>
                        <Text style={styles.statValue}>{data.students}</Text>
                        <Text style={styles.statLabel}>active students</Text>
                    </View>
                    <View style={styles.statDivider} />
                    <View style={styles.stat}>
                        <Text style={styles.statValue}>{data.classes_today}</Text>
                        <Text style={styles.statLabel}>classes today</Text>
                    </View>
                </View>

                {/* Start Here Card */}
                <SectionHeader title="Start here" />
                <View style={styles.primaryActions}>
                    <Pressable
                        style={[styles.attendanceAction, !hasClasses && styles.actionDisabled]}
                        onPress={handleAttendancePress}
                        accessibilityRole="button"
                    >
                        <View>
                            <Text style={styles.actionOverline}>DAILY REGISTER</Text>
                            <Text style={styles.actionTitle}>Mark today’s{"\n"}attendance</Text>
                        </View>
                        {icon("calendar-check", colors.white, 32)}
                    </Pressable>

                    <Pressable
                        style={styles.groupAction}
                        onPress={() => router.push("/(app)/classes")}
                        accessibilityRole="button"
                    >
                        <MaterialCommunityIcons name="google-classroom" color={colors.primary} size={36} />
                        <Text style={styles.groupTitle}>Classes</Text>
                        <Text style={styles.groupText}>Batches & rosters</Text>
                    </Pressable>
                </View>

                {/* Quick Actions Row */}
                <View style={styles.utilityActions}>
                    <Pressable
                        style={styles.utilityBtn}
                        onPress={() => router.push("/(app)/homework")}
                        accessibilityRole="button"
                    >
                        <MaterialCommunityIcons name="book-plus-outline" size={18} color={colors.primary} />
                        <Text style={styles.utilityText}>+ Add homework</Text>
                    </Pressable>
                    <Pressable
                        style={styles.utilityBtn}
                        onPress={() => router.push("/(app)/fees/collect")}
                        accessibilityRole="button"
                    >
                        <MaterialCommunityIcons name="currency-inr" size={18} color={colors.primary} />
                        <Text style={styles.utilityText}>₹ Create fee</Text>
                    </Pressable>
                </View>

                {/* Up Next Panel */}
                <SectionHeader
                    title="Up next"
                    action={
                        <Pressable onPress={() => router.push("/(app)/schedule")}>
                            <Text style={styles.link}>Full schedule</Text>
                        </Pressable>
                    }
                />
                {data.next_class ? (
                    <Pressable onPress={() => router.push("/(app)/schedule")}>
                        <Card style={styles.nextCard}>
                            <View style={styles.timeBox}>
                                <Text style={styles.timeValue}>{data.next_class.start_time}</Text>
                                <Text style={styles.timeEnd}>{data.next_class.end_time}</Text>
                            </View>
                            <View style={styles.nextCopy}>
                                <Text style={styles.nextTitle}>{data.next_class.subject ?? data.next_class.class_name}</Text>
                                <Text style={styles.nextMeta}>
                                    {data.next_class.class_name} · {data.next_class.student_count} students
                                </Text>
                            </View>
                            {icon("arrow-top-right", colors.primary, 20)}
                        </Card>
                    </Pressable>
                ) : (
                    <View style={styles.inlineEmpty}>
                        {icon("calendar-blank-outline", colors.muted, 20)}
                        <Text style={styles.inlineEmptyText}>No classes coming up</Text>
                        <Pressable onPress={() => router.push("/(app)/schedule")}>
                            <Text style={styles.link}>Add schedule</Text>
                        </Pressable>
                    </View>
                )}

                {/* Fee Follow-up Panel */}
                <SectionHeader
                    title="Fee follow-up"
                    action={
                        <Pressable onPress={() => router.push("/(app)/(tabs)/fees")}>
                            <Text style={styles.link}>View all</Text>
                        </Pressable>
                    }
                />
                {data.pending_fee_items?.length ? (
                    <Card style={styles.feeBlock}>
                        <Text style={styles.feeTotal}>{money(data.pending_fees, data.currency_code || "INR")}</Text>
                        <Text style={styles.feeHint}>
                            {data.pending_fee_items.length} student payment{data.pending_fee_items.length === 1 ? "" : "s"} need attention
                        </Text>
                        {data.pending_fee_items.slice(0, 3).map((fee) => (
                            <View key={fee.id} style={styles.feeRow}>
                                <Avatar name={fee.student_name} size={34} />
                                <View style={styles.feeInfo}>
                                    <Text style={styles.feeName}>{fee.student_name}</Text>
                                    <Text style={styles.feeDue}>Due {fee.due_date}</Text>
                                </View>
                                <Badge tone={fee.status === "OVERDUE" ? "danger" : "warning"}>{fee.status}</Badge>
                            </View>
                        ))}
                    </Card>
                ) : (
                    <EmptyState icon="✓" title="Fees are settled" message="No follow-up is needed right now." />
                )}
            </ScrollView>
        </Screen>
    );
}

const styles = StyleSheet.create({
    content: {
        gap: spacing.lg,
        paddingBottom: spacing.xxl,
    },
    top: {
        alignItems: "center",
        flexDirection: "row",
        justifyContent: "space-between",
        paddingTop: spacing.md,
    },
    greeting: {
        ...typography.display,
        fontSize: 28,
        color: colors.ink,
    },
    date: {
        ...typography.caption,
        marginTop: 2,
    },
    topRight: {
        alignItems: "center",
        flexDirection: "row",
        gap: spacing.sm,
    },
    status: {
        alignItems: "center",
        backgroundColor: colors.surfaceCard,
        borderColor: colors.line,
        borderRadius: radius.pill,
        borderWidth: 1,
        flexDirection: "row",
        gap: spacing.sm,
        paddingHorizontal: spacing.md,
        paddingVertical: 10,
    },
    statusDot: {
        backgroundColor: colors.sage,
        borderRadius: 4,
        height: 8,
        width: 8,
    },
    statusCopy: {
        ...typography.caption,
        color: colors.ink,
        flex: 1,
        fontWeight: "600",
    },
    statusLink: {
        color: colors.primary,
        fontSize: 12,
        fontWeight: "700",
    },
    attendanceHero: {
        backgroundColor: colors.primary,
        borderRadius: radius.xl,
        flexDirection: "row",
        justifyContent: "space-between",
        padding: spacing.xl,
    },
    heroCopy: {
        flex: 1,
        justifyContent: "space-between",
    },
    heroLabel: {
        color: "rgba(255,255,255,0.75)",
        fontSize: 11,
        fontWeight: "800",
        letterSpacing: 1.2,
    },
    heroValue: {
        ...typography.display,
        color: colors.white,
        fontSize: 48,
        fontWeight: "800",
        letterSpacing: -1,
        marginTop: spacing.xs,
    },
    heroText: {
        color: "rgba(255,255,255,0.9)",
        fontSize: 13,
        marginTop: 4,
    },
    heroAction: {
        color: colors.white,
        fontSize: 14,
        fontWeight: "800",
        marginTop: spacing.lg,
    },
    ringOuter: {
        alignItems: "center",
        backgroundColor: "rgba(255,255,255,0.2)",
        borderRadius: 54,
        height: 104,
        justifyContent: "center",
        width: 104,
    },
    ringInner: {
        alignItems: "center",
        backgroundColor: colors.ink,
        borderRadius: 44,
        height: 84,
        justifyContent: "center",
        width: 84,
    },
    ringValue: {
        color: colors.white,
        fontSize: 20,
        fontWeight: "800",
    },
    ringLabel: {
        color: colors.primary,
        fontSize: 9,
        fontWeight: "800",
        letterSpacing: 0.8,
        marginTop: 2,
    },
    secondaryStats: {
        alignItems: "center",
        backgroundColor: colors.white,
        borderColor: colors.line,
        borderRadius: radius.lg,
        borderWidth: 1,
        flexDirection: "row",
        paddingVertical: spacing.md,
    },
    stat: {
        alignItems: "center",
        flex: 1,
        paddingHorizontal: spacing.md,
    },
    statValue: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 26,
    },
    statLabel: {
        ...typography.caption,
        marginTop: 2,
    },
    statDivider: {
        backgroundColor: colors.line,
        height: 36,
        width: 1,
    },
    primaryActions: {
        flexDirection: "row",
        gap: spacing.sm,
    },
    attendanceAction: {
        backgroundColor: colors.ink,
        borderRadius: radius.lg,
        flex: 1.4,
        justifyContent: "space-between",
        minHeight: 140,
        padding: spacing.lg,
    },
    actionDisabled: {
        opacity: 0.65,
    },
    actionOverline: {
        color: colors.primary,
        fontSize: 10,
        fontWeight: "800",
        letterSpacing: 1,
    },
    actionTitle: {
        color: colors.white,
        fontFamily: typography.display.fontFamily,
        fontSize: 20,
        fontWeight: "800",
        lineHeight: 24,
        marginTop: spacing.xs,
    },
    groupAction: {
        backgroundColor: colors.white,
        borderColor: colors.line,
        borderRadius: radius.lg,
        borderWidth: 1,
        flex: 1,
        justifyContent: "flex-end",
        minHeight: 140,
        padding: spacing.lg,
    },
    groupTitle: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 17,
        marginTop: spacing.sm,
    },
    groupText: {
        ...typography.caption,
        marginTop: 2,
    },
    utilityActions: {
        flexDirection: "row",
        gap: spacing.sm,
    },
    utilityBtn: {
        alignItems: "center",
        backgroundColor: colors.white,
        borderColor: colors.line,
        borderRadius: radius.md,
        borderWidth: 1,
        flex: 1,
        flexDirection: "row",
        gap: 6,
        justifyContent: "center",
        minHeight: 46,
        paddingHorizontal: spacing.md,
    },
    utilityText: {
        color: colors.primary,
        fontSize: 13,
        fontWeight: "700",
    },
    link: {
        color: colors.primary,
        fontSize: 13,
        fontWeight: "700",
    },
    nextCard: {
        alignItems: "center",
        flexDirection: "row",
        padding: spacing.md,
    },
    timeBox: {
        borderRightColor: colors.line,
        borderRightWidth: 1,
        minWidth: 64,
        paddingRight: spacing.md,
    },
    timeValue: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 16,
    },
    timeEnd: {
        ...typography.caption,
        marginTop: 1,
    },
    nextCopy: {
        flex: 1,
        marginHorizontal: spacing.md,
    },
    nextTitle: {
        ...typography.heading,
        fontSize: 15,
    },
    nextMeta: {
        ...typography.caption,
        marginTop: 2,
    },
    inlineEmpty: {
        alignItems: "center",
        backgroundColor: colors.white,
        borderColor: colors.line,
        borderRadius: radius.md,
        borderWidth: 1,
        flexDirection: "row",
        gap: spacing.sm,
        padding: spacing.md,
    },
    inlineEmptyText: {
        ...typography.body,
        color: colors.muted,
        flex: 1,
        fontSize: 14,
    },
    feeBlock: {
        padding: spacing.lg,
    },
    feeTotal: {
        ...typography.display,
        color: colors.primary,
        fontSize: 28,
        fontWeight: "800",
    },
    feeHint: {
        ...typography.caption,
        marginTop: 2,
    },
    feeRow: {
        alignItems: "center",
        borderTopColor: colors.line,
        borderTopWidth: 1,
        flexDirection: "row",
        gap: spacing.sm,
        marginTop: spacing.md,
        paddingTop: spacing.md,
    },
    feeInfo: {
        flex: 1,
        marginHorizontal: spacing.xs,
    },
    feeName: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 14,
    },
    feeDue: {
        ...typography.caption,
        fontSize: 11,
        marginTop: 1,
    },
});
