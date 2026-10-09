/**
 * v2 Canonical Groups API client
 * Replaces the education-only class/group split with a unified group model.
 * The v1 groups.ts is still used for education-specific attendance/fee flows.
 */
import apiClient from "./client";

// ─── Types ──────────────────────────────────────────────────────────────────

export type CanonicalGroup = {
    id: string;
    name: string;
    kind: string;
    description: string | null;
    status: string;
    parent_group_id: string | null;
    metadata: Record<string, string>;
};

export type GroupMembershipRecord = {
    id: string;
    member_type: string;
    member_id: string;
    member_role: string;
    joined_at: string;
    removed_at: string | null;
};

export type GroupCreateInput = {
    name: string;
    kind?: string;
    description?: string | null;
    parent_group_id?: string | null;
    metadata?: Record<string, string>;
};

export type MembershipCreateInput = {
    member_type: "student" | "teacher" | "employee" | "user";
    member_id: string;
    member_role?: "member" | "admin" | "coordinator";
};

// ─── v2 Groups ────────────────────────────────────────────────────────────────

function v2Base(baseURL: string | undefined): string {
    return (baseURL ?? "").replace("/api/v1", "/api/v2");
}

export const v2GroupsApi = {
    list: (params?: { kind?: string; include_archived?: boolean }) =>
        apiClient
            .get<CanonicalGroup[]>("/groups", { params, baseURL: v2Base(apiClient.defaults.baseURL) })
            .then((r) => r.data),

    get: (id: string) =>
        apiClient
            .get<CanonicalGroup>(`/groups/${id}`, { baseURL: v2Base(apiClient.defaults.baseURL) })
            .then((r) => r.data),

    create: (data: GroupCreateInput) =>
        apiClient
            .post<CanonicalGroup>("/groups", data, { baseURL: v2Base(apiClient.defaults.baseURL) })
            .then((r) => r.data),

    patch: (id: string, data: Partial<GroupCreateInput> & { status?: string }) =>
        apiClient
            .patch<CanonicalGroup>(`/groups/${id}`, data, { baseURL: v2Base(apiClient.defaults.baseURL) })
            .then((r) => r.data),

    archive: (id: string) =>
        v2GroupsApi.patch(id, { status: "ARCHIVED" }),

    listMembers: (id: string, includeRemoved = false) =>
        apiClient
            .get<GroupMembershipRecord[]>(`/groups/${id}/members`, {
                params: { include_removed: includeRemoved },
                baseURL: v2Base(apiClient.defaults.baseURL),
            })
            .then((r) => r.data),

    addMember: (id: string, data: MembershipCreateInput) =>
        apiClient
            .post<GroupMembershipRecord>(`/groups/${id}/members`, data, { baseURL: v2Base(apiClient.defaults.baseURL) })
            .then((r) => r.data),

    removeMember: (groupId: string, membershipId: string) =>
        apiClient
            .delete(`/groups/${groupId}/members/${membershipId}`, { baseURL: v2Base(apiClient.defaults.baseURL) }),
};
