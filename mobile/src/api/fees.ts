import apiClient from "./client";
import type { Fee } from "./types";

export const feesApi = {
    list: (status?: string, studentId?: string) =>
        apiClient.get<Fee[]>("/fees", { params: { status, student_id: studentId } }).then((r) => r.data),
    get: (id: string) => apiClient.get<Fee>(`/fees/${id}`).then((r) => r.data),
    pending: () => apiClient.get<Fee[]>("/fees/pending").then((r) => r.data),
    create: (payload: Record<string, unknown>) => apiClient.post<Fee>("/fees", payload).then((r) => r.data),
    generate: (payload: Record<string, unknown>) => apiClient.post("/fees/generate", payload).then((r) => r.data),
};
