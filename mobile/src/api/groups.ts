import apiClient from "./client";

export type Group = { id: string; name: string; student_count: number; created_at: string; next_class: { day_of_week: number; start_time: string; end_time: string; subject?: string } | null };
export type GroupMember = { id: string; first_name: string; last_name: string; grade?: string | null; student_number?: string | null };
export type GroupFeeRow = { fee_id: string; student_id: string; student_name: string; group_id?: string | null; amount: string | number; amount_paid: string | number; outstanding_amount: string | number; due_date: string; status: "PAID" | "PENDING" | "OVERDUE"; source: "Group" | "Individual" };
export type StudentView = { assignments: Array<{ id: string; title: string; description?: string | null; due_date?: string; type: string; source: "Group" | "Individual"; group_name?: string | null }>; fees: Array<{ id: string; amount: string; due_date: string; status: string; source: "Group" | "Individual" }>; schedule: Array<{ id: string; day_of_week: number; start_time: string; end_time: string; subject?: string }> };

export type AssignmentItem = { id: string; title: string; description?: string | null; due_date?: string | null; type: string; group_id?: string | null; student_id?: string | null; target_name: string; source: "Group" | "Individual"; created_at?: string };

export const groupsApi = {
  list: () => apiClient.get<Group[]>("/groups").then((r) => r.data),
  create: (name: string) => apiClient.post<Group>("/groups", { name }).then((r) => r.data),
  members: (id: string) => apiClient.get<GroupMember[]>(`/groups/${id}/members`).then((r) => r.data),
  addMember: (id: string, studentId: string) => apiClient.post(`/groups/${id}/members/${studentId}`).then((r) => r.data),
  removeMember: (id: string, studentId: string) => apiClient.delete(`/groups/${id}/members/${studentId}`),
  attendance: (id: string, sessionDate: string) => apiClient.get<{ session: { id: string } | null; records: Array<{ student_id: string; status: "PRESENT" | "ABSENT" | "LATE" | "EXCUSED" }> }>(`/groups/${id}/attendance`, { params: { session_date: sessionDate } }).then((r) => r.data),
  saveAttendance: (id: string, payload: { session_date: string; records: Array<{ student_id: string; status: string }> }) => apiClient.post(`/groups/${id}/attendance`, payload).then((r) => r.data),
  attendanceHistory: (id: string) => apiClient.get(`/groups/${id}/attendance/history`).then((r) => r.data),
  studentAttendance: (id: string) => apiClient.get(`/groups/students/${id}/attendance`).then((r) => r.data),
  createFee: (payload: { group_id?: string; student_id?: string; amount: number; due_date: string }) => apiClient.post("/groups/fees", payload).then((r) => r.data),
  needsAttention: () => apiClient.get<GroupFeeRow[]>("/groups/fees/needs-attention").then((r) => r.data),
  payFee: (feeId: string, payload: { student_id: string; amount_paid: number; paid_on?: string }) => apiClient.post(`/groups/fees/${feeId}/payments`, payload).then((r) => r.data),
  createAssignment: (payload: { group_id?: string; student_id?: string; title: string; description?: string; due_date?: string; type: "assignment" | "test" }) => apiClient.post("/groups/assignments", payload).then((r) => r.data),
  listAssignments: (type?: "assignment" | "test") => apiClient.get<AssignmentItem[]>("/groups/assignments", { params: type ? { type } : undefined }).then((r) => r.data),
  deleteAssignment: (assignmentId: string) => apiClient.delete(`/groups/assignments/${assignmentId}`),
  studentView: (studentId: string) => apiClient.get<StudentView>(`/groups/students/${studentId}/view`).then((r) => r.data),
};
