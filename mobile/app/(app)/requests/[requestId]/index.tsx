/**
 * Request Detail screen: view status, decision details, add comments, approve/reject/cancel.
 */
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { useState } from "react";
import {
    ActivityIndicator,
    Alert,
    Pressable,
    ScrollView,
    StyleSheet,
    Text,
    TextInput,
    View,
} from "react-native";

import { requestsApi } from "@/api/requests";
import { Button, Card, ErrorState, LoadingState, PageHeader, Screen, SectionHeader } from "@/components";
import { useAuthStore } from "@/store/auth";
import { colors, radius, shadow, spacing, typography } from "@/theme";

const STATUS_COLORS: Record<string, { bg: string; text: string }> = {
    PENDING: { bg: "#FEF3C7", text: "#92400E" },
    APPROVED: { bg: "#D1FAE5", text: "#065F46" },
    REJECTED: { bg: "#FEE2E2", text: "#991B1B" },
    CANCELLED: { bg: "#F3F4F6", text: "#4B5563" },
};

export default function RequestDetailScreen() {
    const { requestId } = useLocalSearchParams<{ requestId: string }>();
    const { user } = useAuthStore();
    const qc = useQueryClient();
    const [commentText, setCommentText] = useState("");

    const isApprover = user?.role === "OWNER" || user?.role === "ADMIN";

    const { data: request, isLoading, isError, refetch } = useQuery({
        queryKey: ["request", requestId],
        queryFn: () => requestsApi.get(requestId),
        enabled: !!requestId,
    });

    const decideMutation = useMutation({
        mutationFn: (data: { status: "APPROVED" | "REJECTED"; decision_reason?: string }) =>
            requestsApi.decide(requestId, data),
        onSuccess: () => {
            void qc.invalidateQueries({ queryKey: ["requests"] });
            void qc.invalidateQueries({ queryKey: ["request", requestId] });
        },
        onError: (e: unknown) => {
            Alert.alert("Error", e instanceof Error ? e.message : "Failed to decide request.");
        },
    });

    const cancelMutation = useMutation({
        mutationFn: () => requestsApi.cancel(requestId),
        onSuccess: () => {
            void qc.invalidateQueries({ queryKey: ["requests"] });
            void qc.invalidateQueries({ queryKey: ["request", requestId] });
        },
    });

    const commentMutation = useMutation({
        mutationFn: (text: string) => requestsApi.addComment(requestId, text),
        onSuccess: () => {
            setCommentText("");
            void qc.invalidateQueries({ queryKey: ["request", requestId] });
        },
    });

    const handleApprove = () => {
        Alert.alert("Approve Request", "Are you sure you want to approve this request?", [
            { text: "Cancel", style: "cancel" },
            { text: "Approve", onPress: () => decideMutation.mutate({ status: "APPROVED" }) },
        ]);
    };

    const handleReject = () => {
        Alert.prompt
            ? Alert.prompt(
                  "Reject Request",
                  "Enter reason for rejection (optional):",
                  (reason) => decideMutation.mutate({ status: "REJECTED", decision_reason: reason }),
              )
            : Alert.alert("Reject Request", "Are you sure you want to reject this request?", [
                  { text: "Cancel", style: "cancel" },
                  {
                      text: "Reject",
                      style: "destructive",
                      onPress: () => decideMutation.mutate({ status: "REJECTED" }),
                  },
              ]);
    };

    const handleCancel = () => {
        Alert.alert("Cancel Request", "Are you sure you want to cancel your request?", [
            { text: "Back", style: "cancel" },
            { text: "Cancel Request", style: "destructive", onPress: () => cancelMutation.mutate() },
        ]);
    };

    if (isLoading) return <Screen><LoadingState /></Screen>;
    if (isError || !request) return <Screen><ErrorState onRetry={() => void refetch()} /></Screen>;

    const statusStyle = STATUS_COLORS[request.status] || STATUS_COLORS.PENDING;
    const isOwnerOfRequest = request.requester_id === user?.id;
    const canDecide = isApprover && request.status === "PENDING";
    const canCancel = isOwnerOfRequest && request.status === "PENDING";

    return (
        <Screen>
            <PageHeader
                eyebrow={request.request_type.replace(/_/g, " ")}
                title={request.title}
            />

            <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.content}>
                {/* Status Hero */}
                <View style={styles.heroCard}>
                    <View style={[styles.statusBadge, { backgroundColor: statusStyle.bg }]}>
                        <Text style={[styles.statusText, { color: statusStyle.text }]}>{request.status}</Text>
                    </View>
                    <Text style={styles.requesterLabel}>
                        Requested by <Text style={{ fontWeight: "700" }}>{request.requester_name || "Member"}</Text>
                    </Text>
                </View>

                {/* Details Card */}
                <Card>
                    {request.start_date ? (
                        <View style={styles.infoRow}>
                            <Text style={styles.infoLabel}>Date Range</Text>
                            <Text style={styles.infoValue}>
                                {request.start_date} {request.end_date ? `→ ${request.end_date}` : ""}
                            </Text>
                        </View>
                    ) : null}
                    {request.description ? (
                        <View style={styles.infoRow}>
                            <Text style={styles.infoLabel}>Reason</Text>
                            <Text style={styles.infoValue}>{request.description}</Text>
                        </View>
                    ) : null}
                    {request.decision_reason ? (
                        <View style={styles.infoRow}>
                            <Text style={styles.infoLabel}>Decision Note</Text>
                            <Text style={styles.infoValue}>{request.decision_reason}</Text>
                        </View>
                    ) : null}
                    {request.decided_by_name ? (
                        <View style={styles.infoRow}>
                            <Text style={styles.infoLabel}>Reviewed By</Text>
                            <Text style={styles.infoValue}>{request.decided_by_name}</Text>
                        </View>
                    ) : null}
                </Card>

                {/* Approver Action Buttons */}
                {canDecide ? (
                    <View style={styles.decisionActions}>
                        <Pressable
                            onPress={handleApprove}
                            disabled={decideMutation.isPending}
                            style={[styles.actionBtn, styles.approveBtn]}
                        >
                            <MaterialCommunityIcons name="check" size={18} color={colors.white} />
                            <Text style={styles.actionBtnText}>Approve</Text>
                        </Pressable>
                        <Pressable
                            onPress={handleReject}
                            disabled={decideMutation.isPending}
                            style={[styles.actionBtn, styles.rejectBtn]}
                        >
                            <MaterialCommunityIcons name="close" size={18} color={colors.white} />
                            <Text style={styles.actionBtnText}>Reject</Text>
                        </Pressable>
                    </View>
                ) : null}

                {/* Cancel Action */}
                {canCancel ? (
                    <Pressable
                        onPress={handleCancel}
                        disabled={cancelMutation.isPending}
                        style={styles.cancelBtn}
                    >
                        <Text style={styles.cancelText}>Cancel This Request</Text>
                    </Pressable>
                ) : null}

                {/* Comments Section */}
                <SectionHeader title={`COMMENTS (${request.comments?.length || 0})`} />

                {request.comments?.map((c) => (
                    <View key={c.id} style={styles.commentCard}>
                        <View style={styles.commentHeader}>
                            <Text style={styles.commentAuthor}>{c.user_name}</Text>
                            {c.created_at ? (
                                <Text style={styles.commentTime}>{c.created_at.slice(0, 10)}</Text>
                            ) : null}
                        </View>
                        <Text style={styles.commentBody}>{c.comment}</Text>
                    </View>
                ))}

                {/* Add Comment Input */}
                <View style={styles.commentInputRow}>
                    <TextInput
                        placeholder="Add a comment..."
                        placeholderTextColor={colors.muted}
                        value={commentText}
                        onChangeText={setCommentText}
                        style={styles.commentInput}
                    />
                    <Pressable
                        onPress={() => commentText.trim() && commentMutation.mutate(commentText.trim())}
                        disabled={!commentText.trim() || commentMutation.isPending}
                        style={[styles.sendBtn, !commentText.trim() && { opacity: 0.5 }]}
                    >
                        <MaterialCommunityIcons name="send" size={18} color={colors.white} />
                    </Pressable>
                </View>
            </ScrollView>
        </Screen>
    );
}

const styles = StyleSheet.create({
    content: { gap: spacing.md, paddingBottom: spacing.xxl },
    heroCard: {
        alignItems: "center",
        backgroundColor: colors.white,
        borderRadius: radius.lg,
        padding: spacing.lg,
        gap: spacing.xs,
        ...shadow,
    },
    statusBadge: {
        borderRadius: radius.pill,
        paddingHorizontal: 12,
        paddingVertical: 4,
    },
    statusText: {
        ...typography.caption,
        fontWeight: "700",
        fontSize: 12,
    },
    requesterLabel: {
        ...typography.body,
        color: colors.textSecondary,
        fontSize: 14,
        marginTop: 4,
    },
    infoRow: {
        paddingVertical: spacing.xs + 2,
        borderBottomWidth: StyleSheet.hairlineWidth,
        borderBottomColor: colors.border,
        gap: 2,
    },
    infoLabel: {
        ...typography.caption,
        color: colors.textSecondary,
        fontSize: 11,
        textTransform: "uppercase",
        fontWeight: "600",
    },
    infoValue: {
        ...typography.body,
        color: colors.ink,
        fontSize: 14,
    },
    decisionActions: {
        flexDirection: "row",
        gap: spacing.md,
        marginTop: spacing.xs,
    },
    actionBtn: {
        flex: 1,
        flexDirection: "row",
        alignItems: "center",
        justifyContent: "center",
        gap: spacing.xs,
        height: 48,
        borderRadius: radius.md,
    },
    approveBtn: {
        backgroundColor: "#059669",
    },
    rejectBtn: {
        backgroundColor: colors.danger,
    },
    actionBtnText: {
        ...typography.body,
        color: colors.white,
        fontWeight: "700",
        fontSize: 15,
    },
    cancelBtn: {
        alignItems: "center",
        paddingVertical: spacing.md,
    },
    cancelText: {
        ...typography.caption,
        color: colors.danger,
        fontWeight: "600",
        fontSize: 13,
    },
    commentCard: {
        backgroundColor: colors.white,
        borderRadius: radius.md,
        padding: spacing.md,
        gap: 4,
        borderWidth: 1,
        borderColor: colors.border,
    },
    commentHeader: {
        flexDirection: "row",
        justifyContent: "space-between",
    },
    commentAuthor: {
        ...typography.caption,
        fontWeight: "700",
        color: colors.ink,
    },
    commentTime: {
        ...typography.caption,
        color: colors.textSecondary,
        fontSize: 11,
    },
    commentBody: {
        ...typography.body,
        color: colors.ink,
        fontSize: 13,
        lineHeight: 18,
    },
    commentInputRow: {
        flexDirection: "row",
        gap: spacing.sm,
        marginTop: spacing.xs,
    },
    commentInput: {
        flex: 1,
        height: 44,
        backgroundColor: colors.white,
        borderWidth: 1,
        borderColor: colors.border,
        borderRadius: radius.pill,
        paddingHorizontal: spacing.md,
        ...typography.body,
        fontSize: 14,
        color: colors.ink,
    },
    sendBtn: {
        width: 44,
        height: 44,
        borderRadius: 22,
        backgroundColor: colors.primary,
        alignItems: "center",
        justifyContent: "center",
    },
});
