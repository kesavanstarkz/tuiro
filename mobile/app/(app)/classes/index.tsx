import { useMemo, useState } from "react";
import { Alert, FlatList, Modal, Pressable, StyleSheet, Text, View } from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { groupsApi } from "@/api/groups";
import { useGroups } from "@/api/hooks";
import { Button, Card, EmptyState, ErrorState, IconButton, LoadingState, PageHeader, Screen, SearchBar, TuiroInput } from "@/components";
import { colors, radius, spacing, typography } from "@/theme";

export default function ClassesScreen() {
    const queryClient = useQueryClient();
    const [open, setOpen] = useState(false);
    const [name, setName] = useState("");
    const [search, setSearch] = useState("");

    const groups = useGroups();
    const create = useMutation({
        mutationFn: groupsApi.create,
        onSuccess: () => {
            void queryClient.invalidateQueries({ queryKey: ["groups"] });
            void queryClient.invalidateQueries({ queryKey: ["classes"] });
            void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
            setName("");
            setOpen(false);
        },
    });

    const submit = async () => {
        if (!name.trim()) {
            return Alert.alert("Name required", "Enter a name for this class or batch.");
        }
        try {
            await create.mutateAsync(name.trim());
        } catch {
            Alert.alert("Unable to create class", "Please try again.");
        }
    };

    const data = groups.data ?? [];
    const filtered = useMemo(() => {
        if (!search.trim()) return data;
        return data.filter((item) => item.name.toLowerCase().includes(search.trim().toLowerCase()));
    }, [data, search]);

    if (groups.isLoading) return <Screen><LoadingState /></Screen>;
    if (groups.isError) return <Screen><ErrorState onRetry={() => void groups.refetch()} /></Screen>;

    return (
        <Screen>
            <PageHeader
                eyebrow="PEOPLE"
                title="Classes"
                right={
                    <IconButton
                        label="Create class"
                        tone="primary"
                        onPress={() => setOpen(true)}
                        icon={<MaterialCommunityIcons name="plus" size={22} color="#fff" />}
                    />
                }
            />

            <View style={styles.overview}>
                <Text style={styles.overviewNumber}>{data.length}</Text>
                <View style={styles.overviewCopyBox}>
                    <Text style={styles.overviewTitle}>active learning batches</Text>
                    <Text style={styles.overviewCopy}>Rosters, fees, attendance and homework live here.</Text>
                </View>
            </View>

            {data.length > 0 && (
                <View style={styles.searchWrap}>
                    <SearchBar value={search} onChangeText={setSearch} placeholder="Search classes or batches..." />
                </View>
            )}

            <FlatList
                contentContainerStyle={styles.list}
                data={filtered}
                keyExtractor={(item) => item.id}
                showsVerticalScrollIndicator={false}
                ListEmptyComponent={
                    data.length === 0 ? (
                        <EmptyState
                            icon="🏫"
                            title="No classes yet"
                            message="Create your first batch to get started."
                            action={<Button onPress={() => setOpen(true)}>Create first class</Button>}
                        />
                    ) : (
                        <EmptyState
                            icon="🔍"
                            title="No matching classes"
                            message="Try adjusting your search query."
                        />
                    )
                }
                renderItem={({ item, index }) => (
                    <Pressable onPress={() => router.push(`/classes/${item.id}` as never)}>
                        <Card style={[styles.card, index === 0 && styles.cardLead]}>
                            <View style={[styles.iconWrap, index === 0 && styles.iconWrapLead]}>
                                <MaterialCommunityIcons
                                    name="school-outline"
                                    size={index === 0 ? 26 : 22}
                                    color={index === 0 ? colors.white : colors.primary}
                                />
                            </View>
                            <View style={styles.cardCopy}>
                                <Text style={styles.className}>{item.name}</Text>
                                <Text style={styles.classMeta}>
                                    {item.student_count} student{item.student_count === 1 ? "" : "s"}
                                    {item.next_class ? ` · Next ${item.next_class.start_time}` : " · Set schedule"}
                                </Text>
                            </View>
                            <MaterialCommunityIcons
                                name="chevron-right"
                                size={22}
                                color={index === 0 ? colors.primary : colors.muted}
                            />
                        </Card>
                    </Pressable>
                )}
            />

            <Modal transparent visible={open} animationType="slide" onRequestClose={() => setOpen(false)}>
                <View style={styles.modalOverlay}>
                    <View style={styles.sheet}>
                        <Text style={styles.modalTitle}>Add Class</Text>
                        <Text style={styles.modalSubtitle}>Create a batch to organize students, homework and fees.</Text>
                        <TuiroInput
                            autoFocus
                            label="Class / Batch name"
                            placeholder="Grade 12 – Evening Batch"
                            value={name}
                            onChangeText={setName}
                        />
                        <View style={styles.modalActions}>
                            <Button variant="secondary" onPress={() => setOpen(false)}>Cancel</Button>
                            <Button disabled={create.isPending} onPress={() => void submit()}>
                                {create.isPending ? "Creating..." : "Create class"}
                            </Button>
                        </View>
                    </View>
                </View>
            </Modal>
        </Screen>
    );
}

const styles = StyleSheet.create({
    overview: {
        alignItems: "center",
        borderBottomColor: colors.line,
        borderBottomWidth: 1,
        flexDirection: "row",
        gap: spacing.md,
        paddingBottom: spacing.lg,
    },
    overviewNumber: {
        ...typography.display,
        color: colors.primary,
        fontSize: 38,
        fontWeight: "800",
    },
    overviewCopyBox: {
        flex: 1,
    },
    overviewTitle: {
        ...typography.heading,
        fontSize: 16,
        color: colors.ink,
    },
    overviewCopy: {
        ...typography.caption,
        marginTop: 2,
    },
    searchWrap: {
        marginTop: spacing.md,
    },
    list: {
        gap: spacing.sm,
        paddingVertical: spacing.md,
        flexGrow: 1,
    },
    card: {
        alignItems: "center",
        flexDirection: "row",
        padding: spacing.md,
    },
    cardLead: {
        borderLeftColor: colors.primary,
        borderLeftWidth: 4,
    },
    iconWrap: {
        alignItems: "center",
        backgroundColor: colors.coralSoft,
        borderRadius: radius.md,
        height: 44,
        justifyContent: "center",
        width: 44,
    },
    iconWrapLead: {
        backgroundColor: colors.primary,
    },
    cardCopy: {
        flex: 1,
        marginHorizontal: spacing.md,
    },
    className: {
        ...typography.heading,
        fontSize: 16,
    },
    classMeta: {
        ...typography.caption,
        marginTop: 3,
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
        padding: spacing.xl,
    },
    modalTitle: {
        ...typography.display,
        fontSize: 24,
    },
    modalSubtitle: {
        ...typography.caption,
        marginBottom: spacing.md,
        marginTop: 4,
    },
    modalActions: {
        flexDirection: "row",
        gap: spacing.sm,
        justifyContent: "flex-end",
        marginTop: spacing.lg,
    },
});
