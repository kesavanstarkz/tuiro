import { PropsWithChildren, ReactNode } from "react";
import {
    ActivityIndicator,
    Modal,
    Platform,
    Pressable,
    ScrollView,
    StyleSheet,
    Text,
    TextInput,
    TextInputProps,
    useWindowDimensions,
    View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { MaterialCommunityIcons } from "@expo/vector-icons";

import { colors, modalShadow, radius, shadow, spacing, typography } from "@/theme";

export function Screen({ children }: PropsWithChildren) {
    const insets = useSafeAreaInsets();
    const { width } = useWindowDimensions();
    const isDesktop = width >= 768;

    return (
        <View
            style={[
                styles.screen,
                {
                    paddingTop: insets.top + spacing.sm,
                    paddingBottom: isDesktop ? insets.bottom + spacing.xl : insets.bottom + 92,
                },
            ]}
        >
            <View style={[styles.screenContent, isDesktop && styles.screenContentDesktop]}>
                {children}
            </View>
        </View>
    );
}

export function PageHeader({
    eyebrow,
    title,
    subtitle,
    right,
}: {
    eyebrow?: string;
    title: string;
    subtitle?: string;
    right?: ReactNode;
}) {
    return (
        <View style={styles.header}>
            <View style={styles.headerCopy}>
                {eyebrow && <Text style={styles.eyebrow}>{eyebrow}</Text>}
                <Text style={styles.title}>{title}</Text>
                {subtitle && <Text style={styles.subtitle}>{subtitle}</Text>}
            </View>
            {right && <View style={styles.headerRight}>{right}</View>}
        </View>
    );
}

export function Card({ children, style }: PropsWithChildren<{ style?: object }>) {
    return <View style={[styles.card, style]}>{children}</View>;
}

export function SectionHeader({ title, action }: { title: string; action?: ReactNode }) {
    return (
        <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>{title}</Text>
            {action}
        </View>
    );
}

export function StatCard({ label, value, accent = colors.primary }: { label: string; value: string | number; accent?: string }) {
    return (
        <Card style={[styles.statCard, { borderLeftColor: accent, borderLeftWidth: 4 }]}>
            <Text style={styles.statValue}>{value}</Text>
            <Text style={styles.statLabel}>{label}</Text>
        </Card>
    );
}

export function IconButton({
    icon,
    onPress,
    label,
    tone = "light",
}: {
    icon: ReactNode;
    onPress?: () => void;
    label: string;
    tone?: "light" | "primary";
}) {
    return (
        <Pressable
            accessibilityRole="button"
            accessibilityLabel={label}
            onPress={onPress}
            style={({ pressed }) => [
                styles.iconButton,
                tone === "primary" ? styles.iconButtonPrimary : styles.iconButtonLight,
                pressed && styles.pressed,
            ]}
        >
            {icon}
        </Pressable>
    );
}

export function Chip({ children, selected = false, onPress }: PropsWithChildren<{ selected?: boolean; onPress?: () => void }>) {
    return (
        <Pressable onPress={onPress} style={[styles.chip, selected && styles.chipSelected]}>
            <Text style={[styles.chipText, selected && styles.chipTextSelected]}>{children}</Text>
        </Pressable>
    );
}

export function Button({
    children,
    onPress,
    variant = "primary",
    disabled = false,
}: PropsWithChildren<{
    onPress?: () => void;
    variant?: "primary" | "secondary" | "ghost";
    disabled?: boolean;
}>) {
    return (
        <Pressable
            accessibilityRole="button"
            disabled={disabled}
            onPress={onPress}
            style={({ pressed }) => [
                styles.button,
                styles[`button_${variant}`],
                pressed && styles.pressed,
                disabled && styles.disabled,
            ]}
        >
            <Text
                style={[
                    styles.buttonText,
                    variant === "primary"
                        ? styles.buttonTextPrimary
                        : variant === "secondary"
                            ? styles.buttonTextSecondary
                            : styles.buttonTextGhost,
                ]}
            >
                {children}
            </Text>
        </Pressable>
    );
}

export function TuiroInput({ label, error, ...props }: TextInputProps & { label?: string; error?: string }) {
    return (
        <View style={styles.inputGroup}>
            {label && <Text style={styles.inputLabel}>{label}</Text>}
            <TextInput
                {...props}
                accessibilityLabel={props.accessibilityLabel ?? label ?? props.placeholder}
                placeholderTextColor={colors.muted}
                style={[styles.input, error && styles.inputError, props.style]}
            />
            {error && <Text style={styles.fieldError}>{error}</Text>}
        </View>
    );
}

export function Badge({
    children,
    tone = "neutral",
}: PropsWithChildren<{ tone?: "neutral" | "success" | "warning" | "danger" | "active" }>) {
    const effectiveTone = tone === "active" ? "success" : tone;
    return (
        <View style={[styles.badge, styles[`badge_${effectiveTone}`]]}>
            <Text style={[styles.badgeText, styles[`badgeText_${effectiveTone}`]]}>{children}</Text>
        </View>
    );
}

const AVATAR_COLORS = ["#C1622D", "#2F7D52", "#1E2A23", "#A8501F", "#3E4A42", "#286B62"];

export function Avatar({ name, size = 42 }: { name: string; size?: number }) {
    const initials = name
        .trim()
        .split(/\s+/)
        .slice(0, 2)
        .map((part) => part[0])
        .join("")
        .toUpperCase() || "?";

    const charCode = name.charCodeAt(0) || 0;
    const bg = AVATAR_COLORS[charCode % AVATAR_COLORS.length];

    return (
        <View style={[styles.avatar, { width: size, height: size, borderRadius: size / 2, backgroundColor: bg }]}>
            <Text style={[styles.avatarText, { fontSize: size * 0.38 }]}>{initials}</Text>
        </View>
    );
}

export function SearchBar({
    value,
    onChangeText,
    placeholder = "Search",
}: {
    value: string;
    onChangeText: (value: string) => void;
    placeholder?: string;
}) {
    return (
        <View style={styles.search}>
            <MaterialCommunityIcons name="magnify" size={22} color={colors.muted} style={styles.searchIcon} />
            <TextInput
                accessibilityLabel={placeholder}
                value={value}
                onChangeText={onChangeText}
                placeholder={placeholder}
                placeholderTextColor={colors.muted}
                style={styles.searchInput}
                returnKeyType="search"
            />
        </View>
    );
}

export function ListRow({
    leading,
    title,
    subtitle,
    detail,
    trailing,
    statusText,
    statusTone = "neutral",
    onPress,
}: {
    leading?: ReactNode;
    title: string;
    subtitle?: string;
    detail?: string;
    trailing?: ReactNode;
    statusText?: string;
    statusTone?: "neutral" | "success" | "warning" | "danger";
    onPress?: () => void;
}) {
    const sub = subtitle ?? detail;
    return (
        <Pressable onPress={onPress} style={({ pressed }) => [styles.listRow, pressed && styles.rowPressed]}>
            {leading}
            <View style={styles.listCopy}>
                <Text style={styles.listTitle} numberOfLines={1}>
                    {title}
                </Text>
                {sub && (
                    <Text style={styles.listDetail} numberOfLines={2}>
                        {sub}
                    </Text>
                )}
            </View>
            {trailing ? (
                trailing
            ) : (
                <>
                    {statusText && <Badge tone={statusTone}>{statusText}</Badge>}
                    <MaterialCommunityIcons name="chevron-right" size={20} color={colors.muted} style={{ marginLeft: spacing.sm }} />
                </>
            )}
        </Pressable>
    );
}

export function FeatureCard({
    title,
    subtitle,
    icon = "→",
    color,
    onPress,
}: {
    title: string;
    subtitle?: string;
    icon?: string;
    color?: string;
    onPress?: () => void;
}) {
    return (
        <Pressable onPress={onPress} style={({ pressed }) => [styles.featureCard, pressed && styles.rowPressed]}>
            <View style={styles.featureCopy}>
                <Text style={styles.featureTitle}>{title}</Text>
                {subtitle && <Text style={styles.featureSubtitle}>{subtitle}</Text>}
            </View>
            <View style={[styles.featureIconWrap, { backgroundColor: color || colors.coralSoft }]}>
                <Text style={styles.featureIcon}>{icon}</Text>
            </View>
        </Pressable>
    );
}

export function EmptyState({
    icon,
    title,
    message,
    action,
}: {
    icon: string;
    title: string;
    message: string;
    action?: ReactNode;
}) {
    return (
        <View style={styles.empty}>
            <View style={styles.emptyIconWrap}>
                <Text style={styles.emptyIcon}>{icon}</Text>
            </View>
            <Text style={styles.emptyTitle}>{title}</Text>
            <Text style={styles.emptyMessage}>{message}</Text>
            {action && <View style={styles.emptyAction}>{action}</View>}
        </View>
    );
}

export function FormModal({
    visible,
    onClose,
    title,
    children,
    submitLabel = "Save",
    onSubmit,
    isSubmitting = false,
}: PropsWithChildren<{
    visible: boolean;
    onClose: () => void;
    title: string;
    submitLabel?: string;
    onSubmit: () => void;
    isSubmitting?: boolean;
}>) {
    const { width } = useWindowDimensions();
    const isDesktop = width >= 768;

    return (
        <Modal visible={visible} transparent animationType={isDesktop ? "fade" : "slide"} onRequestClose={onClose}>
            <View style={[styles.modalOverlay, isDesktop && styles.modalOverlayDesktop]}>
                <View style={[styles.modalSheet, isDesktop && styles.modalDialogDesktop]}>
                    <View style={styles.modalHeader}>
                        <Text style={styles.modalTitle}>{title}</Text>
                        <Pressable onPress={onClose} hitSlop={12}>
                            <MaterialCommunityIcons name="close" size={24} color={colors.muted} />
                        </Pressable>
                    </View>
                    <ScrollView contentContainerStyle={styles.modalBody} keyboardShouldPersistTaps="handled">
                        {children}
                    </ScrollView>
                    <View style={styles.modalFooter}>
                        <Button variant="secondary" onPress={onClose}>
                            Cancel
                        </Button>
                        <Button disabled={isSubmitting} onPress={onSubmit}>
                            {isSubmitting ? "Saving..." : submitLabel}
                        </Button>
                    </View>
                </View>
            </View>
        </Modal>
    );
}

export function LoadingState() {
    return (
        <View accessibilityLabel="Loading" style={styles.center}>
            <ActivityIndicator color={colors.primary} size="large" />
            <Text style={styles.loadingText}>Loading...</Text>
        </View>
    );
}

export function ErrorState({ onRetry }: { onRetry: () => void }) {
    return (
        <View style={styles.center}>
            <View style={styles.errorIcon}>
                <MaterialCommunityIcons name="alert-circle-outline" size={32} color={colors.danger} />
            </View>
            <Text style={styles.errorTitle}>Something went wrong</Text>
            <Text style={styles.errorMessage}>We couldn’t load this right now. Check your connection and try again.</Text>
            <Button variant="secondary" onPress={onRetry}>
                Try again
            </Button>
        </View>
    );
}

// Backwards compatibility re-exports
export const TuiroListItem = ListRow;

const styles = StyleSheet.create({
    screen: { flex: 1, backgroundColor: colors.paper },
    screenContent: { flex: 1, paddingHorizontal: spacing.xl, width: "100%" },
    screenContentDesktop: { maxWidth: 960, alignSelf: "center", paddingHorizontal: spacing.xxl },

    header: { flexDirection: "row", alignItems: "flex-end", justifyContent: "space-between", paddingTop: spacing.lg, paddingBottom: spacing.lg },
    headerCopy: { flex: 1 },
    eyebrow: { ...typography.label, color: colors.primary, marginBottom: spacing.xs },
    title: typography.display,
    subtitle: { ...typography.body, color: colors.muted, marginTop: spacing.xs },
    headerRight: { marginLeft: spacing.md },

    card: { backgroundColor: colors.white, borderColor: colors.border, borderRadius: radius.lg, borderWidth: 1, padding: spacing.xl, ...shadow },
    statCard: { flex: 1, minWidth: 140 },
    statValue: { ...typography.heading, fontSize: 26, color: colors.ink },
    statLabel: { ...typography.caption, marginTop: spacing.xs },

    sectionHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: spacing.md, marginTop: spacing.md },
    sectionTitle: { ...typography.heading, fontSize: 18 },

    button: { alignItems: "center", justifyContent: "center", minHeight: 48, borderRadius: radius.md, paddingHorizontal: spacing.xl },
    button_primary: { backgroundColor: colors.primary, ...shadow },
    button_secondary: { backgroundColor: "transparent", borderColor: colors.ink, borderWidth: 1.5 },
    button_ghost: { backgroundColor: "transparent" },
    buttonText: { fontFamily: typography.body.fontFamily, fontSize: 15, fontWeight: "600", letterSpacing: 0.1 },
    buttonTextPrimary: { color: colors.white },
    buttonTextSecondary: { color: colors.ink },
    buttonTextGhost: { color: colors.primary },
    pressed: { opacity: 0.8, transform: [{ scale: 0.985 }] },
    disabled: { opacity: 0.5 },

    iconButton: { alignItems: "center", borderRadius: radius.pill, height: 44, justifyContent: "center", width: 44 },
    iconButtonLight: { backgroundColor: colors.white, borderColor: colors.border, borderWidth: 1 },
    iconButtonPrimary: { backgroundColor: colors.primary, ...shadow },

    chip: { backgroundColor: colors.white, borderColor: colors.border, borderRadius: radius.pill, borderWidth: 1, paddingHorizontal: spacing.md, paddingVertical: spacing.sm },
    chipSelected: { backgroundColor: colors.ink, borderColor: colors.ink },
    chipText: { color: colors.inkSoft, fontFamily: typography.body.fontFamily, fontSize: 13, fontWeight: "500" },
    chipTextSelected: { color: colors.white },

    inputGroup: { marginTop: spacing.md },
    inputLabel: { ...typography.caption, color: colors.ink, fontWeight: "600", marginBottom: spacing.xs },
    input: { backgroundColor: colors.white, borderColor: colors.border, borderRadius: radius.md, borderWidth: 1, color: colors.ink, fontFamily: typography.body.fontFamily, fontSize: 15, minHeight: 48, paddingHorizontal: spacing.md },
    inputError: { borderColor: colors.danger },
    fieldError: { color: colors.danger, fontSize: 12, marginTop: spacing.xs },

    badge: { alignSelf: "flex-start", borderRadius: radius.pill, paddingHorizontal: spacing.sm + 2, paddingVertical: 4 },
    badge_neutral: { backgroundColor: colors.border },
    badge_success: { backgroundColor: colors.badgeActiveBg },
    badge_warning: { backgroundColor: colors.amberSoft },
    badge_danger: { backgroundColor: colors.redSoft },
    badgeText: { fontSize: 11, fontWeight: "600" },
    badgeText_neutral: { color: colors.inkSoft },
    badgeText_success: { color: colors.badgeActiveText },
    badgeText_warning: { color: colors.warning },
    badgeText_danger: { color: colors.danger },

    avatar: { alignItems: "center", justifyContent: "center" },
    avatarText: { color: colors.white, fontWeight: "700" },

    search: { alignItems: "center", flexDirection: "row", backgroundColor: colors.white, borderColor: colors.border, borderWidth: 1, borderRadius: radius.md, paddingHorizontal: spacing.md, minHeight: 46, ...shadow },
    searchIcon: { marginRight: spacing.sm },
    searchInput: { flex: 1, color: colors.ink, fontSize: 15, fontFamily: typography.body.fontFamily },

    listRow: { alignItems: "center", backgroundColor: colors.white, borderColor: colors.border, borderWidth: 1, borderRadius: radius.lg, flexDirection: "row", minHeight: 64, padding: spacing.md, marginBottom: spacing.sm, ...shadow },
    rowPressed: { backgroundColor: colors.paper },
    listCopy: { flex: 1, marginHorizontal: spacing.md },
    listTitle: { ...typography.heading, fontSize: 16 },
    listDetail: { ...typography.caption, marginTop: 2 },

    empty: { alignItems: "center", backgroundColor: colors.white, borderColor: colors.border, borderRadius: radius.lg, borderWidth: 1, paddingVertical: spacing.xxxl, paddingHorizontal: spacing.xl, ...shadow, marginVertical: spacing.md },
    emptyIconWrap: { alignItems: "center", backgroundColor: colors.primaryLight, borderRadius: 28, height: 56, justifyContent: "center", marginBottom: spacing.lg, width: 56 },
    emptyIcon: { fontSize: 26 },
    emptyTitle: { ...typography.heading, textAlign: "center" },
    emptyMessage: { ...typography.body, maxWidth: 280, textAlign: "center", marginTop: spacing.xs, marginBottom: spacing.lg },
    emptyAction: { marginTop: spacing.xs },

    center: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.xxl, gap: spacing.md },
    loadingText: { ...typography.body, color: colors.muted },
    errorIcon: { alignItems: "center", backgroundColor: colors.redSoft, borderRadius: 24, height: 48, justifyContent: "center", width: 48 },
    errorTitle: { ...typography.heading, color: colors.danger },
    errorMessage: { ...typography.body, maxWidth: 280, textAlign: "center" },

    modalOverlay: { backgroundColor: "rgba(30, 42, 35, 0.45)", flex: 1, justifyContent: "flex-end" },
    modalOverlayDesktop: { justifyContent: "center", alignItems: "center", padding: spacing.xl },
    modalSheet: { backgroundColor: colors.paper, borderTopLeftRadius: radius.xl, borderTopRightRadius: radius.xl, maxHeight: "90%", width: "100%", ...modalShadow },
    modalDialogDesktop: { borderRadius: radius.xl, maxWidth: 540, maxHeight: "85%" },
    modalHeader: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: spacing.xl, paddingTop: spacing.xl, paddingBottom: spacing.sm },
    modalTitle: { ...typography.heading, fontSize: 20 },
    modalBody: { paddingHorizontal: spacing.xl, paddingBottom: spacing.lg },
    modalFooter: { flexDirection: "row", justifyContent: "flex-end", gap: spacing.md, paddingHorizontal: spacing.xl, paddingVertical: spacing.lg, borderTopColor: colors.border, borderTopWidth: 1 },

    featureCard: {
        alignItems: "center",
        backgroundColor: colors.white,
        borderColor: colors.border,
        borderRadius: radius.md,
        borderWidth: 1,
        flex: 1,
        flexDirection: "row",
        justifyContent: "space-between",
        minWidth: 140,
        padding: spacing.md,
        ...shadow,
    },
    featureCopy: {
        flex: 1,
    },
    featureTitle: {
        ...typography.heading,
        color: colors.ink,
        fontSize: 15,
    },
    featureSubtitle: {
        ...typography.caption,
        marginTop: 2,
    },
    featureIconWrap: {
        alignItems: "center",
        borderRadius: radius.sm,
        height: 32,
        justifyContent: "center",
        width: 32,
    },
    featureIcon: {
        color: colors.primary,
        fontSize: 16,
        fontWeight: "800",
    },
});
