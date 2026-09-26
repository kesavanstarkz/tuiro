import { Stack } from "expo-router";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { Platform, StatusBar } from "react-native";

import { AppProvider } from "@/providers/AppProvider";

export default function RootLayout() {
    return (
        <SafeAreaProvider>
            <StatusBar barStyle="dark-content" />
            {Platform.OS === "web" && (
                <style
                    // eslint-disable-next-line react/no-danger
                    dangerouslySetInnerHTML={{
                        __html: `
                            * {
                                -webkit-tap-highlight-color: transparent !important;
                            }
                            [role="tab"], [role="tab"]:focus, [role="tab"]:focus-visible, [role="tab"]:active {
                                outline: none !important;
                                box-shadow: none !important;
                            }
                            button:focus, button:focus-visible, [role="button"]:focus, [role="button"]:focus-visible {
                                outline: none !important;
                            }
                        `,
                    }}
                />
            )}
            <AppProvider>
                <Stack screenOptions={{ headerShown: false }} />
            </AppProvider>
        </SafeAreaProvider>
    );
}

