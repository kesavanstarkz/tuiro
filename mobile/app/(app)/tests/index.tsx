import { router } from "expo-router";
import { useGroups } from "@/api/hooks";
import { Button, EmptyState, ErrorState, LoadingState, ResourceList, Screen } from "@/components";

export default function TestsScreen() {
    const groups = useGroups();

    if (groups.isLoading) return <Screen><LoadingState /></Screen>;
    if (groups.isError) return <Screen><ErrorState onRetry={() => void groups.refetch()} /></Screen>;

    const classList = groups.data ?? [];
    const classOptions = classList.map((item) => ({
        value: item.id,
        label: item.name,
        detail: `${item.student_count} student${item.student_count === 1 ? "" : "s"}`,
    }));

    if (!classOptions.length) {
        return (
            <Screen>
                <EmptyState
                    icon="🏫"
                    title="Create a class first"
                    message="Tests need a class roster. Add your first batch before creating a test."
                    action={<Button onPress={() => router.push("/(app)/classes")}>Create a class</Button>}
                />
            </Screen>
        );
    }

    return (
        <ResourceList
            endpoint="/tests"
            eyebrow="ACADEMICS"
            title="Tests"
            icon="📝"
            emptyTitle="No tests yet"
            emptyMessage="Create a test to start tracking performance."
            searchPlaceholder="Search tests"
            fields={[
                { key: "class_id", label: "Class / Batch", required: true, options: classOptions },
                { key: "name", label: "Test name", required: true },
                { key: "subject", label: "Subject" },
                { key: "test_date", label: "Test date (YYYY-MM-DD)", required: true },
                { key: "maximum_marks", label: "Maximum marks", required: true, keyboardType: "decimal-pad" },
            ]}
        />
    );
}
