import { resourceApi } from "./resources";
import type { Homework } from "./types";
export const homeworkApi = { list: () => resourceApi.list<Homework>("/homework"), create: (payload: Record<string, unknown>) => resourceApi.create<Homework>("/homework", payload), update: (id: string, payload: Record<string, unknown>) => resourceApi.update<Homework>("/homework", id, payload), remove: (id: string) => resourceApi.remove("/homework", id) };
