import { resourceApi } from "./resources";
export const notificationsApi = { list: () => resourceApi.list<Record<string, unknown>>("/notifications"), create: (payload: Record<string, unknown>) => resourceApi.create("/notifications", payload), feeReminder: (feeId: string) => resourceApi.create(`/notifications/fee-reminder/${feeId}`, {}) };
