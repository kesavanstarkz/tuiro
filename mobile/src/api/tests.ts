import apiClient from "./client";
import { resourceApi } from "./resources";
import type { AcademicTest } from "./types";

export interface TestDetail extends AcademicTest {
    class_name?: string;
    title?: string;
}

export interface StudentTestMark {
    id: string;
    test_id: string;
    test_name: string;
    test_title: string;
    subject?: string;
    test_date: string;
    marks: number;
    maximum_marks: number;
    percentage: number;
    grade?: string;
    remarks?: string;
}

export const testsApi = {
    list: () => resourceApi.list<AcademicTest>("/tests"),
    get: (id: string) => apiClient.get<TestDetail>(`/tests/${id}`).then((r) => r.data),
    create: (payload: Record<string, unknown>) => resourceApi.create<AcademicTest>("/tests", payload),
    update: (id: string, payload: Record<string, unknown>) => resourceApi.update<AcademicTest>("/tests", id, payload),
    remove: (id: string) => resourceApi.remove("/tests", id),
    marks: (id: string) => apiClient.get(`/tests/${id}/marks`).then((r) => r.data),
    saveMark: (id: string, payload: Record<string, unknown>) => apiClient.post(`/tests/${id}/marks`, payload).then((r) => r.data),
    studentMarks: (studentId: string) => apiClient.get<StudentTestMark[]>(`/students/${studentId}/tests`).then((r) => r.data),
};
