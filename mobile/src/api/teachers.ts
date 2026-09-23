import { resourceApi } from "./resources";
import type { Teacher } from "./types";
export const teachersApi = { list: () => resourceApi.list<Teacher>("/teachers"), create: (payload: Record<string, unknown>) => resourceApi.create<Teacher>("/teachers", payload), update: (id: string, payload: Record<string, unknown>) => resourceApi.update<Teacher>("/teachers", id, payload), remove: (id: string) => resourceApi.remove("/teachers", id) };
