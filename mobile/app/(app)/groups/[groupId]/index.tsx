/**
 * Group detail screen — shows members, and lets admins add/remove members.
 */
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { Alert, FlatList, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { v2GroupsApi, type GroupMembershipRecord } from "@/api/v2Groups";
import { Card, ErrorState, LoadingState, PageHeader, Screen, SectionHeader } from "@/components";
import { colors, radius, shadow, spacing, typography } from "@/theme";

function MemberRow({
    member,
    onRemove,
}: {
    member: GroupMembershipRecord;
    onRemove: () => void;
}) {
    const initial = member.member_type[0]?.toUpperCase() ?? "M";
    return (
        <View style={styles.memberRow}>
            <View style={styles.memberAvatar}>
                <Text style={styles.memberAvatarText}>{initial}</Text>
            </View>
            <View style={styles.memberInfo}>
                <Text style={styles.memberType}>{member.member_type}</Text>
                <Text style={styles.memberId} numberOfLines={1}>
                    {member.member_id}
                </Text>
                <Text style={styles.memberRole}>{member.member_role}</Text>
            </View>
            <Pressable onPress={onRemove} style={styles.removeBtn} accessibilityLabel="Remove member">
                <MaterialCommunityIcons name="account-remove-outline" size={18} color={colors.danger} />
            </Pressable>
        </View>
    );
}

export default function GroupDetailScreen() {
    const { groupId } = useLocalSearchParams<{ groupId: string }>();
    const qc = useQueryClient();

    const { data: group, isLoading: gLoading, isError: gError, refetch: gRefetch } = useQuery({
        queryKey: ["v2group", groupId],
        queryFn: () => v2GroupsApi.get(groupId),
        enabled: !!groupId,
    });

    const { data: members, isLoading: mLoading, refetch: mRefetch } = useQuery({
        queryKey: ["v2group-members", groupId],
        queryFn: () => v2GroupsApi.listMembers(groupId),
        enabled: !!groupId,
    });

    const removeMember = useMutation({
        mutationFn: (membershipId: string) => v2GroupsApi.removeMember(groupId, membershipId),
        onSuccess: () => {
            void qc.invalidateQueries({ queryKey: ["v2group-members", groupId] });
        },
    });

    const archiveGroup = useMutation({
        mutationFn: () => v2GroupsApi.archive(groupId),
        onSuccess: () => {
            void qc.invalidateQueries({ queryKey: ["v2groups"] });
            router.back();
        },
    });

    const handleRemove = (membership: GroupMembershipRecord) => {
        Alert.alert("Remove Member", "Remove this member from the group?", [
            { text: "Cancel", style: "cancel" },
            { text: "Remove", style: "destructive", onPress: () => removeMember.mutate(membership.id) },
        ]);
    };

    const handleArchive = () => {
        Alert.alert("Archive Group", "Archive this group? Members will no longer see it.", [
            { text: "Cancel", style: "cancel" },
            { text: "Archive", style: "destructive", onPress: () => archiveGroup.mutate() },
        ]);
    };

    if (gLoading) return <Screen><LoadingState /></Screen>;
    if (gError || !group) return <Screen><ErrorState onRetry={() => void gRefetch()} /></Screen>;

    const memberList = members ?? [];

    return (
        <Screen>
            <PageHeader
                eyebrow={group.kind.toUpperCase()}
                title={group.name}
                right={
                    <Pressable
                        onPress={() => router.push(`/groups/${groupId}/edit` as never)}
                        style={styles.editBtn}
                        accessibilityLabel="Edit group"
                    >
                        <MaterialCommunityIcons name="pencil-outline" size={18} color={colors.ink} />
                    </Pressable>
                }
            />

            <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.content}>
                {group.description && (
                    <Card>
                        <Text style={styles.description}>{group.description}</Text>
                    </Card>
                )}

                <SectionHeader
                    title={`MEMBERS (${memberList.length})`}
                    action={
                        <Pressable onPress={() => router.push(`/groups/${groupId}/add-member` as never)} style={styles.addMemberBtn}>
                            <MaterialCommunityIcons name="account-plus-outline" size={16} color={colors.primary} />
                            <Text style={styles.addMemberText}>Add</Text>
                        </Pressable>
                    }
                />

                {mLoading && <LoadingState />}
                {!mLoading && memberList.length === 0 && (
                    <Card>
                        <Text style={styles.emptyText}>No members yet. Add members to this group.</Text>
                    </Card>
                )}
                {!mLoading && memberList.map((m) => (
                    <MemberRow key={m.id} member={m} onRemove={() => handleRemove(m)} />
                ))}

                {group.status === "ACTIVE" && (
                    <Pressable onPress={handleArchive} style={styles.archiveBtn} accessibilityRole="button">
                        <MaterialCommunityIcons name="archive-outline" size={18} color={colors.danger} />
                        <Text style={styles.archiveText}>Archive Group</Text>
                    </Pressable>
                )}
            </ScrollView>
        </Screen>
    );
}

const styles = StyleSheet.create({
    content: { gap: spacing.md, paddingBottom: spacing.xxl },
    description: { ...typography.body, color: colors.textSecondary, lineHeight: 22 },
    memberRow: {
        flexDirection: "row",
        alignItems: "center",
        backgroundColor: colors.white,
        borderRadius: radius.lg,
        padding: spacing.md,
        gap: spacing.md,
        ...shadow,
    },
    memberAvatar: {
        width: 40,
        height: 40,
        borderRadius: 20,
        backgroundColor: colors.primaryLight,
        alignItems: "center",
        justifyContent: "center",
    },
    memberAvatarText: { color: colors.primary, fontWeight: "700", fontSize: 16 },
    memberInfo: { flex: 1 },
    memberType: { ...typography.caption, color: colors.primary, fontWeight: "700", textTransform: "uppercase", fontSize: 10 },
    memberId: { ...typography.body, color: colors.ink, fontWeight: "500", fontSize: 12 },
    memberRole: { ...typography.caption, color: colors.textSecondary },
    removeBtn: { padding: spacing.sm },
    editBtn: {
        width: 40,
        height: 40,
        borderRadius: 20,
        backgroundColor: colors.surface,
        alignItems: "center",
        justifyContent: "center",
        borderWidth: 1,
        borderColor: colors.border,
    },
    addMemberBtn: { flexDirection: "row", alignItems: "center", gap: 4 },
    addMemberText: { color: colors.primary, fontWeight: "600", fontSize: 13 },
    archiveBtn: {
        flexDirection: "row",
        alignItems: "center",
        justifyContent: "center",
        gap: spacing.sm,
        paddingVertical: spacing.md,
        marginTop: spacing.md,
        borderRadius: radius.lg,
        borderWidth: 1,
        borderColor: colors.danger,
    },
    archiveText: { color: colors.danger, fontWeight: "600", fontSize: 15 },
    emptyText: { ...typography.body, color: colors.textSecondary, textAlign: "center", paddingVertical: spacing.md },
});
