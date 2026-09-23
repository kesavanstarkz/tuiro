import { useLocalSearchParams } from "expo-router";
import { StudentHub } from "@/components";
export default function StudentDetailScreen() { const { studentId } = useLocalSearchParams<{ studentId: string }>(); return <StudentHub studentId={studentId} />; }
