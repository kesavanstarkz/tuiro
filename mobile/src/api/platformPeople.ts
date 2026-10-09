/**
 * v2 Platform People API client
 * Corporate: employees, departments, job titles
 * Education: students, teachers, parents (still served by v1 endpoints in groups.ts / people APIs)
 */
import apiClient from "./client";

// ─── Types ──────────────────────────────────────────────────────────────────

export type Department = {
    id: string;
    name: string;
    description: string | null;
};

export type JobTitle = {
    id: string;
    name: string;
    description: string | null;
};

export type Employee = {
    id: string;
    employee_number: string;
    first_name: string;
    last_name: string;
    email: string | null;
    phone: string | null;
    department_id: string | null;
    job_title_id: string | null;
    manager_id: string | null;
    employment_type: string;
    start_date: string | null;
    status: string;
};

export type EmployeeInput = {
    employee_number: string;
    first_name: string;
    last_name?: string;
    email?: string | null;
    phone?: string | null;
    department_id?: string | null;
    job_title_id?: string | null;
    manager_id?: string | null;
    employment_type?: string;
    start_date?: string | null;
    status?: string;
};

export type EmployeePatch = Partial<EmployeeInput>;

// ─── Departments ─────────────────────────────────────────────────────────────

export const departmentsApi = {
    list: () =>
        apiClient.get<Department[]>("/people/departments", { baseURL: apiClient.defaults.baseURL?.replace("/api/v1", "/api/v2") }).then((r) => r.data),
    create: (data: { name: string; description?: string }) =>
        apiClient.post<Department>("/people/departments", data, { baseURL: apiClient.defaults.baseURL?.replace("/api/v1", "/api/v2") }).then((r) => r.data),
};

// ─── Job Titles ───────────────────────────────────────────────────────────────

export const jobTitlesApi = {
    list: () =>
        apiClient.get<JobTitle[]>("/people/job-titles", { baseURL: apiClient.defaults.baseURL?.replace("/api/v1", "/api/v2") }).then((r) => r.data),
    create: (data: { name: string; description?: string }) =>
        apiClient.post<JobTitle>("/people/job-titles", data, { baseURL: apiClient.defaults.baseURL?.replace("/api/v1", "/api/v2") }).then((r) => r.data),
};

// ─── Employees ────────────────────────────────────────────────────────────────

export const employeesApi = {
    list: (params?: { search?: string; status?: string; department_id?: string }) =>
        apiClient.get<Employee[]>("/people/employees", { params, baseURL: apiClient.defaults.baseURL?.replace("/api/v1", "/api/v2") }).then((r) => r.data),
    get: (id: string) =>
        apiClient.get<Employee>(`/people/employees/${id}`, { baseURL: apiClient.defaults.baseURL?.replace("/api/v1", "/api/v2") }).then((r) => r.data),
    create: (data: EmployeeInput) =>
        apiClient.post<Employee>("/people/employees", data, { baseURL: apiClient.defaults.baseURL?.replace("/api/v1", "/api/v2") }).then((r) => r.data),
    patch: (id: string, data: EmployeePatch) =>
        apiClient.patch<Employee>(`/people/employees/${id}`, data, { baseURL: apiClient.defaults.baseURL?.replace("/api/v1", "/api/v2") }).then((r) => r.data),
    archive: (id: string) =>
        apiClient.patch<Employee>(`/people/employees/${id}`, { status: "ARCHIVED" }, { baseURL: apiClient.defaults.baseURL?.replace("/api/v1", "/api/v2") }).then((r) => r.data),
};
