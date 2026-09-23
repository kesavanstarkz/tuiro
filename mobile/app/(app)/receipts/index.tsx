import { ResourceList } from "@/components";
export default function ReceiptsScreen() { return <ResourceList endpoint="/receipts" eyebrow="BUSINESS" title="Receipts" icon="🧾" emptyTitle="No receipts yet" emptyMessage="Receipts will appear after payments are recorded." searchPlaceholder="Search receipts" />; }
