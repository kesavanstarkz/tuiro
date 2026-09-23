import { useLocalSearchParams } from "expo-router";
import { ClassHub } from "@/components";
export default function ClassDetailScreen() { const { classId } = useLocalSearchParams<{ classId: string }>(); return <ClassHub classId={classId} />; }
