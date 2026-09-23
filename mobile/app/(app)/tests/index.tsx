import { useClasses } from "@/api/hooks";
import { EmptyState, ErrorState, LoadingState, ResourceList, Screen } from "@/components";

export default function TestsScreen() {
    const classes = useClasses();
    if (classes.isLoading) return <Screen><LoadingState /></Screen>;
    if (classes.isError) return <Screen><ErrorState onRetry={() => void classes.refetch()} /></Screen>;
    const classOptions = (classes.data ?? []).map((item) => ({ value: item.id, label: item.name, detail: item.subject }));
    if (!classOptions.length) return <Screen><EmptyState icon="🏫" title="Create a class first" message="Tests need a class roster. Add your first batch before creating a test." /></Screen>;
    return <ResourceList endpoint="/tests" eyebrow="ACADEMICS" title="Tests" icon="📝" emptyTitle="No tests yet" emptyMessage="Create a test to start tracking performance." searchPlaceholder="Search tests" fields={[{ key: "class_id", label: "Class", required: true, options: classOptions }, { key: "name", label: "Test name", required: true }, { key: "subject", label: "Subject" }, { key: "test_date", label: "Test date (YYYY-MM-DD)", required: true }, { key: "maximum_marks", label: "Maximum marks", required: true, keyboardType: "decimal-pad" }]} />;
}
