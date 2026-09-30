import { Alert, FlatList, Linking, Pressable, StyleSheet, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { MaterialCommunityIcons } from "@expo/vector-icons";

import { useStudent, useStudentParents } from "@/api/hooks";
import { Avatar, Badge, Button, Card, EmptyState, ErrorState, LoadingState, PageHeader, Screen } from "@/components";
import { colors, radius, spacing, typography } from "@/theme";

export default function StudentParentScreen() {
    const { studentId } = useLocalSearchParams<{ studentId: string }>();
    const studentQuery = useStudent(studentId);
    const parentsQuery = useStudentParents(studentId);

    if (studentQuery.isLoading || parentsQuery.isLoading) {
        return (
            <Screen>
                <LoadingState />
            </Screen>
        );
    }

    if (studentQuery.isError || !studentQuery.data) {
        return (
            <Screen>
                <ErrorState onRetry={() => {
                    void studentQuery.refetch();
                    void parentsQuery.refetch();
                }} />
            </Screen>
        );
    }

    const student = studentQuery.data;
    const name = `${student.first_name} ${student.last_name}`.trim();
    const parents = parentsQuery.data ?? [];

    const handleCall = (phone?: string) => {
        if (!phone) return;
        Linking.openURL(`tel:${phone}`).catch(() => {
            Alert.alert("Unable to call", `Could not place call to ${phone}`);
        });
    };

    const handleEmail = (email?: string) => {
        if (!email) return;
        Linking.openURL(`mailto:${email}`).catch(() => {
            Alert.alert("Unable to email", `Could not send email to ${email}`);
        });
    };

    const handleWhatsApp = (phone?: string) => {
        if (!phone) return;
        const clean = phone.replace(/[^0-9]/g, "");
        Linking.openURL(`https://wa.me/${clean}`).catch(() => {
            Alert.alert("Unable to open WhatsApp", "Make sure WhatsApp is installed.");
        });
    };

    return (
        <Screen>
            <FlatList
                contentContainerStyle={styles.content}
                data={parents}
                keyExtractor={(item) => item.id}
                showsVerticalScrollIndicator={false}
                ListHeaderComponent={
                    <View style={styles.headerWrap}>
                        <PageHeader
                            eyebrow="GUARDIAN CONTACT"
                            title={`${name}'s Parents`}
                            action={
                                <Button variant="secondary" size="sm" onPress={() => router.back()}>
                                    Back
                                </Button>
                            }
                        />
                        <Text style={styles.sectionTitle}>Linked Guardians ({parents.length})</Text>
                    </View>
                }
                ListEmptyComponent={
                    <EmptyState
                        icon="👨‍👩‍👧"
                        title="No parent linked"
                        message="There are no guardians or parents linked to this student yet."
                        action={<Button onPress={() => router.push("/(app)/parents" as never)}>View Parents</Button>}
                    />
                }
                renderItem={({ item }) => {
                    const parentName = item.name;
                    return (
                        <Card style={styles.parentCard}>
                            <Pressable
                                style={styles.parentHeader}
                                onPress={() => router.push(`/parents/${item.id}` as never)}
                            >
                                <Avatar name={parentName} size={44} />
                                <View style={styles.parentInfo}>
                                    <Text style={styles.parentName}>{parentName}</Text>
                                    <Text style={styles.parentRole}>
                                        {item.relationship ?? "Guardian"}
                                        {item.is_primary ? " · Primary Contact" : ""}
                                    </Text>
                                </View>
                                {item.is_primary && (
                                    <Badge tone="success">Primary</Badge>
                                )}
                            </Pressable>

                            <View style={styles.contactDetails}>
                                {Boolean(item.phone) && (
                                    <Text style={styles.detailText}>
                                        Phone: <Text style={styles.detailVal}>{item.phone}</Text>
                                    </Text>
                                )}
                                {Boolean(item.email) && (
                                    <Text style={styles.detailText}>
                                        Email: <Text style={styles.detailVal}>{item.email}</Text>
                                    </Text>
                                )}
                            </View>

                            <View style={styles.actionsRow}>
                                {Boolean(item.phone) && (
                                    <>
                                        <Button
                                            variant="secondary"
                                            size="sm"
                                            onPress={() => handleCall(item.phone ?? undefined)}
                                        >
                                            Call
                                        </Button>
                                        <Button
                                            variant="secondary"
                                            size="sm"
                                            onPress={() => handleWhatsApp(item.phone ?? undefined)}
                                        >
                                            WhatsApp
                                        </Button>
                                    </>
                                )}
                                {Boolean(item.email) && (
                                    <Button
                                        variant="secondary"
                                        size="sm"
                                        onPress={() => handleEmail(item.email ?? undefined)}
                                    >
                                        Email
                                    </Button>
                                )}
                                <Button
                                    size="sm"
                                    onPress={() => router.push(`/parents/${item.id}` as never)}
                                >
                                    Profile
                                </Button>
                            </View>
                        </Card>
                    );
                }}
            />
        </Screen>
    );
}

const styles = StyleSheet.create({
    content: {
        gap: spacing.sm,
        paddingBottom: spacing.xxl,
        paddingTop: spacing.xs,
    },
    headerWrap: {
        gap: spacing.md,
        marginBottom: spacing.xs,
    },
    sectionTitle: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 16,
    },
    parentCard: {
        gap: spacing.md,
        padding: spacing.md,
    },
    parentHeader: {
        alignItems: "center",
        flexDirection: "row",
        gap: spacing.md,
    },
    parentInfo: {
        flex: 1,
    },
    parentName: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 16,
    },
    parentRole: {
        ...typography.caption,
        marginTop: 2,
    },
    contactDetails: {
        borderTopColor: colors.line,
        borderTopWidth: 1,
        gap: 4,
        paddingTop: spacing.xs,
    },
    detailText: {
        ...typography.caption,
        color: colors.muted,
    },
    detailVal: {
        color: colors.ink,
        fontWeight: "600",
    },
    actionsRow: {
        flexDirection: "row",
        flexWrap: "wrap",
        gap: spacing.xs,
    },
});
