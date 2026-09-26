import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { attendanceApi } from "./attendance";
import { classesApi } from "./classes";
import { feesApi } from "./fees";
import { homeworkApi } from "./homework";
import { notificationsApi } from "./notifications";
import { parentsApi } from "./parents";
import { paymentsApi } from "./payments";
import { reportsApi } from "./reports";
import { receiptsApi } from "./receipts";
import { schedulesApi } from "./schedules";
import { settingsApi } from "./settings";
import { studentsApi } from "./students";
import { subscriptionApi } from "./subscription";
import { teachersApi } from "./teachers";
import { testsApi } from "./tests";
import { groupsApi } from "./groups";
export type { AttendanceSessionResponse, AttendanceStatus, ClassItem, Fee, Student } from "./types";

const invalidate = (client: ReturnType<typeof useQueryClient>, keys: string[][]) => keys.forEach((queryKey) => void client.invalidateQueries({ queryKey }));
export function useDashboard() { return useQuery({ queryKey: ["dashboard"], queryFn: reportsApi.dashboard, refetchOnReconnect: true }); }
export function useStudents(search?: string) { return useQuery({ queryKey: ["students", search ?? ""], queryFn: () => studentsApi.list(search), refetchOnReconnect: true }); }
export function useStudent(id?: string) { return useQuery({ queryKey: ["student", id], queryFn: () => studentsApi.get(id!), enabled: Boolean(id) }); }
export function useParents(search?: string) { return useQuery({ queryKey: ["parents", search ?? ""], queryFn: () => parentsApi.list(search) }); }
export function useTeachers() { return useQuery({ queryKey: ["teachers"], queryFn: teachersApi.list }); }
export function useClasses() { return useQuery({ queryKey: ["classes"], queryFn: classesApi.list, refetchOnReconnect: true }); }
export function useGroups() { return useQuery({ queryKey: ["groups"], queryFn: groupsApi.list, refetchOnReconnect: true }); }
export function useGroup(id?: string) { return useQuery({ queryKey: ["group", id], queryFn: () => groupsApi.list().then((items) => items.find((item) => item.id === id)), enabled: Boolean(id) }); }
export function useGroupMembers(id?: string) { return useQuery({ queryKey: ["group-members", id], queryFn: () => groupsApi.members(id!), enabled: Boolean(id) }); }
export function useGroupAttendance(id?: string, date?: string) { return useQuery({ queryKey: ["group-attendance", id, date], queryFn: () => groupsApi.attendance(id!, date!), enabled: Boolean(id && date) }); }
export function useGroupFeeAttention() { return useQuery({ queryKey: ["group-fee-attention"], queryFn: groupsApi.needsAttention, refetchOnReconnect: true }); }
export function useClassStudents(classId?: string) { return useQuery({ queryKey: ["class-students", classId], queryFn: () => classesApi.students(classId!), enabled: Boolean(classId) }); }
export function useClassTeachers(classId?: string) { return useQuery({ queryKey: ["class-teachers", classId], queryFn: () => classesApi.teachers(classId!), enabled: Boolean(classId) }); }
export function useStudentParents(studentId?: string) { return useQuery({ queryKey: ["student-parents", studentId], queryFn: () => parentsApi.studentParents(studentId!), enabled: Boolean(studentId) }); }
export function useParentStudents(parentId?: string) { return useQuery({ queryKey: ["parent-students", parentId], queryFn: () => parentsApi.students(parentId!), enabled: Boolean(parentId) }); }
export function useAttendanceHistory(sessionDate?: string) { return useQuery({ queryKey: ["attendance-history", sessionDate ?? ""], queryFn: () => attendanceApi.list(sessionDate) }); }
export function useAttendanceSession(classId?: string, sessionDate?: string) { return useQuery({ queryKey: ["attendance-session", classId, sessionDate], queryFn: () => attendanceApi.session(classId!, sessionDate!), enabled: Boolean(classId && sessionDate) }); }
export function useFees() { return useQuery({ queryKey: ["fees"], queryFn: feesApi.list }); }
export function usePendingFees() { return useQuery({ queryKey: ["pending-fees"], queryFn: feesApi.pending, refetchOnReconnect: true }); }
export function usePayments() { return useQuery({ queryKey: ["payments"], queryFn: paymentsApi.list, refetchOnReconnect: true }); }
export function useHomework() { return useQuery({ queryKey: ["homework"], queryFn: homeworkApi.list }); }
export function useTests() { return useQuery({ queryKey: ["tests"], queryFn: testsApi.list }); }
export function useTestMarks(testId?: string) { return useQuery({ queryKey: ["test-marks", testId], queryFn: () => testsApi.marks(testId!), enabled: Boolean(testId) }); }
export function useSchedules() { return useQuery({ queryKey: ["schedule"], queryFn: schedulesApi.list }); }
export function useNotifications() { return useQuery({ queryKey: ["notifications"], queryFn: notificationsApi.list }); }
export function useSettings() { return useQuery({ queryKey: ["settings"], queryFn: settingsApi.get }); }
export function useSubscription() { return useQuery({ queryKey: ["subscription"], queryFn: subscriptionApi.status }); }
export function useSubscriptionPlans() { return useQuery({ queryKey: ["subscription-plans"], queryFn: subscriptionApi.plans }); }
export function useCreateStudent() { const c = useQueryClient(); return useMutation({ mutationFn: studentsApi.create, onSuccess: () => invalidate(c, [["students"], ["dashboard"]]) }); }
export function useUpdateStudent() { const c = useQueryClient(); return useMutation({ mutationFn: ({ id, payload }: { id: string; payload: Record<string, unknown> }) => studentsApi.update(id, payload), onSuccess: () => invalidate(c, [["students"], ["student"], ["dashboard"]]) }); }
export function useDeleteStudent() { const c = useQueryClient(); return useMutation({ mutationFn: studentsApi.remove, onSuccess: () => invalidate(c, [["students"], ["dashboard"], ["class-students"]]) }); }
export function useSaveAttendance() { const c = useQueryClient(); return useMutation({ mutationFn: attendanceApi.save, onSuccess: (_result, payload) => invalidate(c, [["attendance-session", payload.class_id, payload.session_date], ["dashboard"]]) }); }
export function useAddGroupMember() { const c = useQueryClient(); return useMutation({ mutationFn: ({ groupId, studentId }: { groupId: string; studentId: string }) => groupsApi.addMember(groupId, studentId), onSuccess: (_r, v) => invalidate(c, [["group-members", v.groupId], ["groups"], ["group", v.groupId]]) }); }
export function useRemoveGroupMember() { const c = useQueryClient(); return useMutation({ mutationFn: ({ groupId, studentId }: { groupId: string; studentId: string }) => groupsApi.removeMember(groupId, studentId), onSuccess: (_r, v) => invalidate(c, [["group-members", v.groupId], ["groups"], ["group", v.groupId]]) }); }
export function useSaveGroupAttendance() { const c = useQueryClient(); return useMutation({ mutationFn: ({ groupId, payload }: { groupId: string; payload: { session_date: string; records: Array<{ student_id: string; status: string }> } }) => groupsApi.saveAttendance(groupId, payload), onSuccess: (_r, v) => invalidate(c, [["group-attendance", v.groupId, v.payload.session_date], ["dashboard"]]) }); }
export function useCreateGroupFee() { const c = useQueryClient(); return useMutation({ mutationFn: groupsApi.createFee, onSuccess: () => invalidate(c, [["group-fee-attention"], ["dashboard"]]) }); }
export function usePayGroupFee() { const c = useQueryClient(); return useMutation({ mutationFn: ({ feeId, ...payload }: { feeId: string; student_id: string; amount_paid: number; paid_on?: string }) => groupsApi.payFee(feeId, payload), onSuccess: () => invalidate(c, [["group-fee-attention"], ["dashboard"]]) }); }
export function useCreateGroupAssignment() { const c = useQueryClient(); return useMutation({ mutationFn: groupsApi.createAssignment, onSuccess: () => invalidate(c, [["student"], ["groups"], ["assignments"]]) }); }
export function useAssignments(type?: "assignment" | "test") { return useQuery({ queryKey: ["assignments", type ?? "all"], queryFn: () => groupsApi.listAssignments(type), refetchOnReconnect: true }); }
export function useDeleteAssignment() { const c = useQueryClient(); return useMutation({ mutationFn: (id: string) => groupsApi.deleteAssignment(id), onSuccess: () => invalidate(c, [["assignments"], ["student"], ["groups"]]) }); }
export function useCreatePayment() { const c = useQueryClient(); return useMutation({ mutationFn: paymentsApi.create, onSuccess: () => invalidate(c, [["payments"], ["fees"], ["pending-fees"], ["dashboard"], ["receipts"]]) }); }
export function useGenerateFees() { const c = useQueryClient(); return useMutation({ mutationFn: feesApi.generate, onSuccess: () => invalidate(c, [["fees"], ["pending-fees"], ["dashboard"]]) }); }
export function useCreateSchedule() { const c = useQueryClient(); return useMutation({ mutationFn: schedulesApi.create, onSuccess: () => invalidate(c, [["schedule"], ["dashboard"]]) }); }
export function useAssignStudentToClass() { const c = useQueryClient(); return useMutation({ mutationFn: ({ classId, studentId }: { classId: string; studentId: string }) => classesApi.assignStudent(classId, studentId), onSuccess: (_r, variables) => invalidate(c, [["class-students", variables.classId], ["dashboard"]]) }); }
export function useRemoveStudentFromClass() { const c = useQueryClient(); return useMutation({ mutationFn: ({ classId, studentId }: { classId: string; studentId: string }) => classesApi.removeStudent(classId, studentId), onSuccess: (_r, variables) => invalidate(c, [["class-students", variables.classId], ["dashboard"]]) }); }
export function useAssignTeacherToClass() { const c = useQueryClient(); return useMutation({ mutationFn: ({ classId, teacherId }: { classId: string; teacherId: string }) => classesApi.assignTeacher(classId, teacherId), onSuccess: (_r, variables) => invalidate(c, [["class-teachers", variables.classId], ["dashboard"]]) }); }
export function useRemoveTeacherFromClass() { const c = useQueryClient(); return useMutation({ mutationFn: ({ classId, teacherId }: { classId: string; teacherId: string }) => classesApi.removeTeacher(classId, teacherId), onSuccess: (_r, variables) => invalidate(c, [["class-teachers", variables.classId], ["dashboard"]]) }); }
export function useLinkParent() { const c = useQueryClient(); return useMutation({ mutationFn: ({ studentId, parentId, isPrimary }: { studentId: string; parentId: string; isPrimary?: boolean }) => parentsApi.linkStudent(studentId, parentId, isPrimary), onSuccess: (_r, variables) => invalidate(c, [["student-parents", variables.studentId], ["parent-students", variables.parentId]]) }); }
export function useUnlinkParent() { const c = useQueryClient(); return useMutation({ mutationFn: ({ studentId, parentId }: { studentId: string; parentId: string }) => parentsApi.unlinkStudent(studentId, parentId), onSuccess: (_r, variables) => invalidate(c, [["student-parents", variables.studentId], ["parent-students", variables.parentId]]) }); }
export function useUpdateSettings() { const c = useQueryClient(); return useMutation({ mutationFn: settingsApi.update, onSuccess: () => invalidate(c, [["settings"], ["dashboard"]]) }); }
export function useSaveTestMark() { const c = useQueryClient(); return useMutation({ mutationFn: ({ testId, payload }: { testId: string; payload: Record<string, unknown> }) => testsApi.saveMark(testId, payload), onSuccess: (_r, variables) => invalidate(c, [["test-marks", variables.testId], ["tests"]]) }); }
export function useCreateFeeReminder() { const c = useQueryClient(); return useMutation({ mutationFn: notificationsApi.feeReminder, onSuccess: () => invalidate(c, [["notifications"]]) }); }
export function useSendReceipt() { const c = useQueryClient(); return useMutation({ mutationFn: receiptsApi.send, onSuccess: () => invalidate(c, [["receipts"]]) }); }
