import apiClient from "./client";

export const resourceApi = {
    request: <T>(path: string) => apiClient.get<T>(path).then((response) => response.data),
    list: <T>(path: string, params?: Record<string, string | undefined>) => apiClient.get<T[]>(path, { params }).then((response) => response.data),
    get: <T>(path: string, id: string) => apiClient.get<T>(`${path}/${id}`).then((response) => response.data),
    create: <T>(path: string, payload: Record<string, unknown>) => apiClient.post<T>(path, payload).then((response) => response.data),
    update: <T>(path: string, id: string, payload: Record<string, unknown>) => apiClient.patch<T>(`${path}/${id}`, payload).then((response) => response.data),
    remove: (path: string, id: string) => apiClient.delete(`${path}/${id}`),
};
