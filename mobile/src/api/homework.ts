import apiClient from "./client";
import { resourceApi } from "./resources";
import type { Homework } from "./types";

export interface HomeworkDetail extends Homework {
    class_name?: string;
}

export const homeworkApi = {
    list: () => resourceApi.list<Homework>("/homework"),
    get: (id: string) => apiClient.get<HomeworkDetail>(`/homework/${id}`).then((r) => r.data),
    create: (payload: Record<string, unknown>) => resourceApi.create<Homework>("/homework", payload),
    update: (id: string, payload: Record<string, unknown>) => resourceApi.update<Homework>("/homework", id, payload),
    remove: (id: string) => resourceApi.remove("/homework", id),
};
