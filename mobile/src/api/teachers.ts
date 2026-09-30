import { resourceApi } from "./resources";
import type { Teacher } from "./types";

export interface TeacherDetail extends Teacher {
    name?: string;
    display_name?: string;
    email?: string;
    phone?: string;
}

export const teachersApi = {
    list: () => resourceApi.list<Teacher>("/teachers"),
    get: (id: string) => resourceApi.get<TeacherDetail>("/teachers", id),
    create: (payload: Record<string, unknown>) => resourceApi.create<Teacher>("/teachers", payload),
    update: (id: string, payload: Record<string, unknown>) => resourceApi.update<Teacher>("/teachers", id, payload),
    remove: (id: string) => resourceApi.remove("/teachers", id),
};
