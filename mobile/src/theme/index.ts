import { Platform } from "react-native";

export const colors = {
    primary: "#3b63d1",
    primaryLight: "#eaf0ff",
    primaryDark: "#27469e",
    ink: "#18233a",
    inkSoft: "#59677c",
    paper: "#f6f7fb",
    white: "#ffffff",
    coral: "#df8067",
    coralSoft: "#fff0ec",
    sage: "#387a62",
    sageSoft: "#e6f4ed",
    amber: "#a86628",
    amberSoft: "#fff1dc",
    red: "#bd4551",
    redSoft: "#ffeaec",
    info: "#4b78d8",
    line: "#e6e9f1",
    muted: "#8993a4",
    featureBlue: "#edf2ff",
    featurePurple: "#f3efff",
    featureMint: "#eaf8f1",
    featureYellow: "#fff6df",
};

export const spacing = { xs: 4, sm: 8, md: 12, lg: 16, xl: 20, xxl: 24, xxxl: 32, huge: 40 };
export const radius = { sm: 10, md: 14, lg: 20, xl: 28, pill: 999 };
export const typography = {
    display: { fontSize: 30, lineHeight: 37, fontWeight: "800" as const, color: colors.ink, letterSpacing: -0.7 },
    heading: { fontSize: 20, lineHeight: 26, fontWeight: "700" as const, color: colors.ink, letterSpacing: -0.25 },
    body: { fontSize: 15, lineHeight: 22, color: colors.inkSoft },
    caption: { fontSize: 12, lineHeight: 17, color: colors.muted },
    label: { fontSize: 11, lineHeight: 15, fontWeight: "800" as const, color: colors.inkSoft, letterSpacing: 0.45 },
};
export const shadow = Platform.select({
    ios: { shadowColor: colors.ink, shadowOpacity: 0.07, shadowRadius: 16, shadowOffset: { width: 0, height: 5 } },
    android: { elevation: 2 },
    web: { boxShadow: "0 8px 24px rgba(24, 35, 58, 0.065)" },
    default: {},
});
