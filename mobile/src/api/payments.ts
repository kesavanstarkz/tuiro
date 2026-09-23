import apiClient from "./client";
import type { Payment } from "./types";
export const paymentsApi = { list: () => apiClient.get<Payment[]>("/payments").then((r) => r.data), create: (payload: Record<string, unknown>) => apiClient.post("/payments", payload).then((r) => r.data) };
