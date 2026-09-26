import { Platform } from "react-native";

// Tuiro Production Design System (§6)
// Brand personality: warm, trustworthy, calm — an admin tool a teacher opens dozens of times a day.
export const colors = {
    // Primary: terracotta/orange — primary actions, active states
    primary: "#C1622D",
    primaryHover: "#A8501F",
    primaryDark: "#A8501F",
    primaryLight: "#FCEFE7",

    // Ink: deep forest / near-black green — headings, nav active bg
    ink: "#1E2A23",
    inkSoft: "#3E4A42",

    // Surface / Background
    paper: "#FAF8F4",
    surface: "#FAF8F4",
    white: "#FFFFFF",
    surfaceCard: "#FFFFFF",
    line: "#E7E2D9",
    border: "#E7E2D9",

    // Functional Statuses
    success: "#2F7D52",
    warning: "#C1622D",
    danger: "#B3261E",
    red: "#B3261E",
    redSoft: "#FBE8E9",
    sage: "#2F7D52",
    sageSoft: "#E7F3EC",
    amber: "#C1622D",
    amberSoft: "#FCEFE7",
    coral: "#C1622D",
    coralSoft: "#FCEFE7",
    accent: "#C1622D",
    accentSoft: "#FCEFE7",

    // Typography Colors
    textPrimary: "#1E2A23",
    textSecondary: "#6B6459",
    muted: "#6B6459",

    // Badges & Accents
    badgeActiveBg: "#E7F3EC",
    badgeActiveText: "#2F7D52",
    featureBlue: "#F1EBE1",
    featurePurple: "#F4EFE6",
    featureMint: "#E7F3EC",
    featureYellow: "#FCEFE7",
};

// 8px base spacing unit
export const spacing = { xs: 4, sm: 8, md: 12, lg: 16, xl: 20, xxl: 24, xxxl: 32, huge: 40 };

// Corner radius: Card radius 16px, inputs/buttons 12px
export const radius = { sm: 8, md: 12, lg: 16, xl: 24, pill: 999 };

const fontFallback = '-apple-system, "Segoe UI", Roboto, sans-serif';
const displayFamily = Platform.select({
    ios: "Avenir Next, " + fontFallback,
    android: "sans-serif-medium",
    web: "Inter, " + fontFallback,
    default: fontFallback,
});
const bodyFamily = Platform.select({
    ios: "Avenir Next, " + fontFallback,
    android: "sans-serif",
    web: "Inter, " + fontFallback,
    default: fontFallback,
});

export const typography = {
    // 28 / 22 / 17 / 15 / 13px scale
    display: { fontFamily: displayFamily, fontSize: 28, lineHeight: 34, fontWeight: "600" as const, color: colors.ink, letterSpacing: -0.5 },
    heading: { fontFamily: displayFamily, fontSize: 22, lineHeight: 28, fontWeight: "600" as const, color: colors.ink, letterSpacing: -0.3 },
    bodyLg: { fontFamily: bodyFamily, fontSize: 17, lineHeight: 24, fontWeight: "400" as const, color: colors.inkSoft },
    body: { fontFamily: bodyFamily, fontSize: 15, lineHeight: 22, fontWeight: "400" as const, color: colors.inkSoft },
    caption: { fontFamily: bodyFamily, fontSize: 13, lineHeight: 18, fontWeight: "400" as const, color: colors.muted },
    label: { fontFamily: bodyFamily, fontSize: 11, lineHeight: 15, fontWeight: "600" as const, color: colors.muted, letterSpacing: 1.1, textTransform: "uppercase" as const },
};

export const shadow = Platform.select({
    ios: { shadowColor: colors.ink, shadowOpacity: 0.05, shadowRadius: 10, shadowOffset: { width: 0, height: 4 } },
    android: { elevation: 2 },
    web: { boxShadow: "0 2px 8px rgba(30, 42, 35, 0.05)" },
    default: {},
});

export const modalShadow = Platform.select({
    ios: { shadowColor: colors.ink, shadowOpacity: 0.16, shadowRadius: 24, shadowOffset: { width: 0, height: 10 } },
    android: { elevation: 10 },
    web: { boxShadow: "0 16px 40px rgba(30, 42, 35, 0.16)" },
    default: {},
});
