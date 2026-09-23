import { resourceApi } from "./resources";
import type { Student } from "./types";
export const studentsApi = { list: (search?: string) => resourceApi.list<Student>("/students", { search }), get: (id: string) => resourceApi.get<Student>("/students", id), create: (payload: Record<string, unknown>) => resourceApi.create<Student>("/students", payload), update: (id: string, payload: Record<string, unknown>) => resourceApi.update<Student>("/students", id, payload), remove: (id: string) => resourceApi.remove("/students", id) };
