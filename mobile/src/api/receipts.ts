import apiClient from "./client";
import { resourceApi } from "./resources";
export const receiptsApi = { list: () => resourceApi.list<Record<string, unknown>>("/receipts"), get: (id: string) => resourceApi.get<Record<string, unknown>>("/receipts", id), pdf: (id: string) => apiClient.get(`/receipts/${id}/pdf`, { responseType: "arraybuffer" }).then((r) => r.data), send: (id: string) => apiClient.post(`/receipts/${id}/send`).then((r) => r.data) };
