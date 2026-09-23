import axios from "axios";
import Constants from "expo-constants";
import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";

const expoHost = Constants.expoConfig?.hostUri?.split(":")[0];
// A phone cannot reach the development machine through localhost. Configure a LAN URL
// in mobile/.env; Expo's host is only a convenient development fallback.
// Web runs on the same development machine as FastAPI, while native devices
// must use EXPO_PUBLIC_API_URL with the machine's LAN address.
const apiBaseUrl = process.env.EXPO_PUBLIC_API_URL ?? (expoHost ? `http://${expoHost}:8000/api/v1` : Platform.OS === "web" ? "http://127.0.0.1:8000/api/v1" : undefined);

const apiClient = axios.create({
    baseURL: apiBaseUrl,
    timeout: 10000,
    headers: { "Content-Type": "application/json" },
});

let accessToken: string | null = null;
let refreshToken: string | null = null;
let onRefreshFailure: (() => void) | null = null;
let refreshInFlight: Promise<{ access_token: string; refresh_token: string }> | null = null;

async function readToken(key: string) {
    if (Platform.OS === "web") return globalThis.localStorage?.getItem(key) ?? null;
    return SecureStore.getItemAsync(key);
}

async function writeToken(key: string, value: string) {
    if (Platform.OS === "web") {
        globalThis.localStorage?.setItem(key, value);
        return;
    }
    await SecureStore.setItemAsync(key, value);
}

async function removeToken(key: string) {
    if (Platform.OS === "web") {
        globalThis.localStorage?.removeItem(key);
        return;
    }
    await SecureStore.deleteItemAsync(key);
}

export async function loadTokens() {
    accessToken = await readToken("tuiro_access_token");
    refreshToken = await readToken("tuiro_refresh_token");
    return { accessToken, refreshToken };
}

export async function saveTokens(nextAccessToken: string, nextRefreshToken: string) {
    accessToken = nextAccessToken;
    refreshToken = nextRefreshToken;
    await writeToken("tuiro_access_token", nextAccessToken);
    await writeToken("tuiro_refresh_token", nextRefreshToken);
}

export async function clearTokens() {
    accessToken = null;
    refreshToken = null;
    await removeToken("tuiro_access_token");
    await removeToken("tuiro_refresh_token");
}

export function setRefreshFailureHandler(handler: () => void) {
    onRefreshFailure = handler;
}

export function apiErrorMessage(error: unknown, fallback = "Something went wrong. Please try again.") {
    if (axios.isAxiosError(error)) {
        const data = error.response?.data as { error?: { message?: string }; detail?: string | Array<{ msg?: string }> } | undefined;
        if (data?.error?.message) return data.error.message;
        if (typeof data?.detail === "string") return data.detail;
        if (Array.isArray(data?.detail)) return data.detail.map((item) => item.msg).filter(Boolean).join(" ") || fallback;
        if (error.code === "ECONNABORTED") return "The request timed out. Please try again.";
        if (!error.response) return "Unable to reach Tuiro. Check your connection and try again.";
    }
    return error instanceof Error && error.message === "API_URL_NOT_CONFIGURED" ? "The app API address is not configured." : fallback;
}

async function refreshAccessToken() {
    if (!refreshToken) throw new Error("REFRESH_TOKEN_UNAVAILABLE");
    if (!refreshInFlight) {
        const tokenToRefresh = refreshToken;
        refreshInFlight = axios.post<{ access_token: string; refresh_token: string }>(`${apiClient.defaults.baseURL}/auth/refresh`, { refresh_token: tokenToRefresh })
            .then(async (response) => {
                await saveTokens(response.data.access_token, response.data.refresh_token);
                return response.data;
            })
            .finally(() => { refreshInFlight = null; });
    }
    return refreshInFlight;
}

apiClient.interceptors.request.use((config) => {
    if (!apiClient.defaults.baseURL) return Promise.reject(new Error("API_URL_NOT_CONFIGURED"));
    if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`;
    return config;
});

apiClient.interceptors.response.use(
    (response) => response,
    async (error) => {
        const original = error.config;
        if (error.response?.status !== 401 || original?._retry || !refreshToken || original?.url?.includes("/auth/")) {
            return Promise.reject(error);
        }
        original._retry = true;
        try {
            const tokens = await refreshAccessToken();
            original.headers.Authorization = `Bearer ${tokens.access_token}`;
            return apiClient(original);
        } catch (refreshError) {
            await clearTokens();
            onRefreshFailure?.();
            return Promise.reject(refreshError);
        }
    },
);

export default apiClient;
