import { Platform } from "react-native";

// Atelier: inky evergreen, warm stone, and a single saffron action accent.
export const colors = {
    primary: "#173F3A", primaryDark: "#0B2925", primaryLight: "#E5F0EA", accent: "#D66A3D", accentSoft: "#FBE9E0",
    ink: "#162522", inkSoft: "#52605B", paper: "#F7F5F0", white: "#FFFDF9", coral: "#D66A3D", coralSoft: "#FBE9E0",
    sage: "#39735C", sageSoft: "#E5F2EB", amber: "#A96717", amberSoft: "#FFF1D8", red: "#B7444E", redSoft: "#FBE8E9",
    info: "#286B62", line: "#E5E3DC", muted: "#7C8781", featureBlue: "#E5F0EA", featurePurple: "#F2EEE6", featureMint: "#E5F2EB", featureYellow: "#FFF1D8",
};
export const spacing = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32, xxxl: 40, huge: 48 };
export const radius = { sm: 10, md: 14, lg: 18, xl: 26, pill: 999 };
const displayFamily = Platform.select({ ios: "Avenir Next Condensed", android: "sans-serif-condensed", web: "Arial Narrow, Avenir Next, sans-serif", default: "sans-serif" });
const bodyFamily = Platform.select({ ios: "Avenir Next", android: "sans-serif", web: "Avenir Next, Inter, sans-serif", default: "sans-serif" });
export const typography = {
    display: { fontFamily: displayFamily, fontSize: 32, lineHeight: 38, fontWeight: "800" as const, color: colors.ink, letterSpacing: -0.8 },
    heading: { fontFamily: displayFamily, fontSize: 20, lineHeight: 26, fontWeight: "700" as const, color: colors.ink, letterSpacing: -0.35 },
    body: { fontFamily: bodyFamily, fontSize: 14, lineHeight: 21, color: colors.inkSoft },
    caption: { fontFamily: bodyFamily, fontSize: 12, lineHeight: 17, color: colors.muted },
    label: { fontFamily: bodyFamily, fontSize: 10, lineHeight: 14, fontWeight: "800" as const, color: colors.inkSoft, letterSpacing: 1.05 },
};
export const shadow = Platform.select({ ios: { shadowColor: "#132622", shadowOpacity: 0.08, shadowRadius: 18, shadowOffset: { width: 0, height: 7 } }, android: { elevation: 3 }, web: { boxShadow: "0 10px 28px rgba(22, 37, 34, 0.08)" }, default: {} });
