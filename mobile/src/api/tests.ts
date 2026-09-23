import apiClient from "./client";
import { resourceApi } from "./resources";
import type { AcademicTest } from "./types";
export const testsApi = { list: () => resourceApi.list<AcademicTest>("/tests"), create: (payload: Record<string, unknown>) => resourceApi.create<AcademicTest>("/tests", payload), update: (id: string, payload: Record<string, unknown>) => resourceApi.update<AcademicTest>("/tests", id, payload), remove: (id: string) => resourceApi.remove("/tests", id), marks: (id: string) => apiClient.get(`/tests/${id}/marks`).then((r) => r.data), saveMark: (id: string, payload: Record<string, unknown>) => apiClient.post(`/tests/${id}/marks`, payload).then((r) => r.data) };
