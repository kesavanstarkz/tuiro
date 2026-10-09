/**
 * Requests and Approval Engine API Client
 */
import apiClient from "./client";

export type ApprovalRequest = {
    id: string;
    request_type: string;
    title: string;
    description: string | null;
    start_date: string | null;
    end_date: string | null;
    status: "PENDING" | "APPROVED" | "REJECTED" | "CANCELLED";
    decision_reason: string | null;
    decided_by: string | null;
    decided_by_name: string | null;
    decided_at: string | null;
    requester_id: string;
    requester_name: string | null;
    requester_email: string | null;
    metadata: Record<string, unknown>;
    created_at: string | null;
    updated_at: string | null;
    comments?: Array<{
        id: string;
        user_id: string;
        user_name: string;
        comment: string;
        created_at: string | null;
    }>;
};

export type RequestCreateInput = {
    request_type: string;
    title: string;
    description?: string | null;
    start_date?: string | null;
    end_date?: string | null;
    metadata?: Record<string, unknown>;
};

export const requestsApi = {
    list: (params?: { scope?: "my" | "pending" | "all"; status?: string; request_type?: string }) =>
        apiClient.get<ApprovalRequest[]>("/requests", { params }).then((r) => r.data),

    get: (id: string) =>
        apiClient.get<ApprovalRequest>(`/requests/${id}`).then((r) => r.data),

    create: (data: RequestCreateInput) =>
        apiClient.post<ApprovalRequest>("/requests", data).then((r) => r.data),

    decide: (id: string, data: { status: "APPROVED" | "REJECTED"; decision_reason?: string | null }) =>
        apiClient.post<ApprovalRequest>(`/requests/${id}/decide`, data).then((r) => r.data),

    cancel: (id: string) =>
        apiClient.post<ApprovalRequest>(`/requests/${id}/cancel`).then((r) => r.data),

    addComment: (id: string, comment: string) =>
        apiClient.post<{ id: string; user_id: string; user_name: string; comment: string; created_at: string | null }>(
            `/requests/${id}/comments`,
            { comment }
        ).then((r) => r.data),
};
