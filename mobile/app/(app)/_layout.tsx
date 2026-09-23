import { Redirect, Stack } from "expo-router";

import { useAuthStore } from "@/store/auth";

export default function AppLayout() {
    const { user, hydrated } = useAuthStore();
    if (!hydrated) return null;
    if (!user) return <Redirect href="/auth/login" />;
    return <Stack screenOptions={{ headerShown: false }} />;
}
