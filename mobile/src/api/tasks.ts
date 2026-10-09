/**
 * Tasks API Client for mobile app
 */
import apiClient from "./client";

export type TaskItem = {
    id: string;
    title: string;
    description: string | null;
    status: "TODO" | "IN_PROGRESS" | "REVIEW" | "DONE";
    priority: "LOW" | "MEDIUM" | "HIGH" | "URGENT";
    group_id: string | null;
    group_name: string | null;
    assignee_id: string | null;
    assignee_name: string | null;
    created_by: string;
    created_by_name: string | null;
    due_date: string | null;
    metadata: Record<string, unknown>;
    created_at: string | null;
    updated_at: string | null;
    checklist?: Array<{
        id: string;
        title: string;
        is_completed: boolean;
    }>;
};

export type TaskCreateInput = {
    title: string;
    description?: string | null;
    priority?: "LOW" | "MEDIUM" | "HIGH" | "URGENT";
    status?: "TODO" | "IN_PROGRESS" | "REVIEW" | "DONE";
    group_id?: string | null;
    assignee_id?: string | null;
    due_date?: string | null;
    metadata?: Record<string, unknown>;
};

export const tasksApi = {
    list: (params?: { status?: string; priority?: string; group_id?: string; scope?: "all" | "my" }) =>
        apiClient.get<TaskItem[]>("/tasks", { params }).then((r) => r.data),

    get: (id: string) =>
        apiClient.get<TaskItem>(`/tasks/${id}`).then((r) => r.data),

    create: (data: TaskCreateInput) =>
        apiClient.post<TaskItem>("/tasks", data).then((r) => r.data),

    patch: (id: string, data: Partial<TaskCreateInput>) =>
        apiClient.patch<TaskItem>(`/tasks/${id}`, data).then((r) => r.data),

    delete: (id: string) =>
        apiClient.delete(`/tasks/${id}`),

    addChecklistItem: (id: string, title: string) =>
        apiClient.post<{ id: string; title: string; is_completed: boolean }>(`/tasks/${id}/checklist`, { title }).then((r) => r.data),

    toggleChecklistItem: (taskId: string, itemId: string) =>
        apiClient.post<{ id: string; title: string; is_completed: boolean }>(`/tasks/${taskId}/checklist/${itemId}/toggle`).then((r) => r.data),
};
