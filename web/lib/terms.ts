export type Term = { singular: string; plural: string };
export type Terms = Record<string, Term>;
export const fallbackTerms: Terms = {
  person: { singular: "Person", plural: "People" }, group: { singular: "Group", plural: "Groups" },
  work_item: { singular: "Task", plural: "Tasks" }, attendance: { singular: "Attendance", plural: "Attendance" },
  leave_request: { singular: "Request", plural: "Requests" }, org_admin: { singular: "Administrator", plural: "Administrators" },
};

export function label(terms: Terms, key: string, plural = true) { return terms[key]?.[plural ? "plural" : "singular"] ?? fallbackTerms[key]?.[plural ? "plural" : "singular"] ?? key; }
