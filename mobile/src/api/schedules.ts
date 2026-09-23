import { resourceApi } from "./resources";
import type { Schedule } from "./types";
export const schedulesApi = { list: () => resourceApi.list<Schedule>("/schedule"), create: (payload: Record<string, unknown>) => resourceApi.create<Schedule>("/schedule", payload), update: (id: string, payload: Record<string, unknown>) => resourceApi.update<Schedule>("/schedule", id, payload), remove: (id: string) => resourceApi.remove("/schedule", id) };
