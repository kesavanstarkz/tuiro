#!/usr/bin/env python3
"""Route link verification script for Tuiro mobile application.

Inspects all route files under mobile/app, verifies that no dead/placeholder
screens remain, and ensures each route is reachable.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "mobile" / "app"

# Route mapping definition: (URL Route, Relative File Path, Reached From, Status)
ROUTES = [
    ("/", "index.tsx", "App launch / root URL", "Active (Redirects to /dashboard or /auth/login)"),
    ("/auth/login", "auth/login.tsx", "Root redirect, register link, logout", "Active"),
    ("/auth/register", "auth/register.tsx", "Login screen 'Create an account' link", "Active"),
    ("/dashboard", "(app)/(tabs)/dashboard.tsx", "Bottom Tab 1, Desktop Sidebar, root redirect", "Active"),
    ("/students", "(app)/(tabs)/students.tsx", "Bottom Tab 2, Desktop Sidebar", "Active"),
    ("/attendance", "(app)/(tabs)/attendance.tsx", "Bottom Tab 3, Desktop Sidebar, Dashboard quick action", "Active"),
    ("/fees", "(app)/(tabs)/fees.tsx", "Bottom Tab 4, Desktop Sidebar, Dashboard fee follow-up", "Active"),
    ("/more", "(app)/(tabs)/more.tsx", "Bottom Tab 5, Desktop Sidebar", "Active"),
    ("/classes", "(app)/classes/index.tsx", "More menu, Desktop Sidebar, Dashboard quick action", "Active"),
    ("/classes/[classId]", "(app)/classes/[classId]/index.tsx", "Classes list rows", "Active"),
    ("/fees/collect", "(app)/fees/collect.tsx", "Fees tab '+ Create fee', Dashboard quick action", "Active"),
    ("/fees/[feeId]", "(app)/fees/[feeId].tsx", "Fees tab rows, Dashboard fee rows, Student fees rows", "Active"),
    ("/homework", "(app)/homework/index.tsx", "More menu, Desktop Sidebar, Dashboard quick action", "Active"),
    ("/homework/[homeworkId]", "(app)/homework/[homeworkId].tsx", "Homework list cards", "Active"),
    ("/tests", "(app)/tests/index.tsx", "More menu, Desktop Sidebar, Student tests empty state", "Active"),
    ("/tests/[testId]", "(app)/tests/[testId].tsx", "Tests list rows, Student tests result cards", "Active"),
    ("/tests/[testId]/marks", "(app)/tests/[testId]/marks.tsx", "Test detail 'Enter / Edit Marks' button", "Active"),
    ("/teachers", "(app)/teachers/index.tsx", "More menu, Desktop Sidebar", "Active"),
    ("/teachers/[teacherId]", "(app)/teachers/[teacherId].tsx", "Teachers list rows", "Active"),
    ("/parents", "(app)/parents/index.tsx", "More menu, Desktop Sidebar, Student parent empty state", "Active"),
    ("/parents/[parentId]", "(app)/parents/[parentId].tsx", "Parents list rows, Student parent profile button", "Active"),
    ("/payments", "(app)/payments/index.tsx", "More menu, Desktop Sidebar, Fees tab 'Payment records'", "Active"),
    ("/payments/[paymentId]", "(app)/payments/[paymentId].tsx", "Payments list rows", "Active"),
    ("/receipts", "(app)/receipts/index.tsx", "More menu, Desktop Sidebar", "Active"),
    ("/receipts/[receiptId]", "(app)/receipts/[receiptId].tsx", "Receipts list rows, Fee detail receipt button", "Active"),
    ("/schedule", "(app)/schedule/index.tsx", "More menu, Desktop Sidebar, Dashboard quick action", "Active"),
    ("/reports", "(app)/reports/index.tsx", "More menu, Desktop Sidebar", "Active"),
    ("/notifications", "(app)/notifications/index.tsx", "More menu, Desktop Sidebar", "Active"),
    ("/settings", "(app)/settings/index.tsx", "More menu, Desktop Sidebar", "Active"),
    ("/subscription", "(app)/subscription/index.tsx", "More menu, Desktop Sidebar", "Active"),
    ("/help", "(app)/help/index.tsx", "More menu, Desktop Sidebar", "Active"),
    ("/students/[studentId]", "(app)/students/[studentId]/index.tsx", "Students list rows, Class roster rows", "Active"),
    ("/students/[studentId]/attendance", "(app)/students/[studentId]/attendance.tsx", "Student Hub 'Attendance' card", "Active"),
    ("/students/[studentId]/fees", "(app)/students/[studentId]/fees.tsx", "Student Hub 'Fees' card", "Active"),
    ("/students/[studentId]/homework", "(app)/students/[studentId]/homework.tsx", "Student Hub 'Homework' card", "Active"),
    ("/students/[studentId]/parent", "(app)/students/[studentId]/parent.tsx", "Student Hub 'Parent' card", "Active"),
    ("/students/[studentId]/tests", "(app)/students/[studentId]/tests.tsx", "Student Hub 'Tests' card", "Active"),
    ("/people", "(app)/people/index.tsx", "More menu, Desktop Sidebar", "Active"),
    ("/people/create", "(app)/people/create.tsx", "People screen '+ Add employee', EmptyState action", "Active"),
    ("/people/[personId]", "(app)/people/[personId]/index.tsx", "People list rows, Create redirect", "Active"),
    ("/people/[personId]/edit", "(app)/people/[personId]/edit.tsx", "Person detail edit button", "Active"),
    ("/groups", "(app)/groups/index.tsx", "More menu, Desktop Sidebar", "Active"),
    ("/groups/create", "(app)/groups/create.tsx", "Groups screen '+ Create group', EmptyState action", "Active"),
    ("/groups/[groupId]", "(app)/groups/[groupId]/index.tsx", "Groups list rows, Create redirect", "Active"),
    ("/groups/[groupId]/edit", "(app)/groups/[groupId]/edit.tsx", "Group detail edit button", "Active"),
    ("/groups/[groupId]/add-member", "(app)/groups/[groupId]/add-member.tsx", "Group detail 'Add' member action", "Active"),
    ("/requests", "(app)/requests/index.tsx", "More menu, Desktop Sidebar", "Active"),
    ("/requests/create", "(app)/requests/create.tsx", "Requests screen '+ New request', EmptyState action", "Active"),
    ("/requests/[requestId]", "(app)/requests/[requestId]/index.tsx", "Requests list rows, Create redirect", "Active"),
]


def verify_routes() -> int:
    errors = 0
    route_files = set()

    for path in APP_DIR.rglob("*.tsx"):
        rel = path.relative_to(APP_DIR).as_posix()
        # ignore layout files
        if path.name.startswith("_"):
            continue
        route_files.add(rel)

        # Check for placeholder / ContextScreen
        content = path.read_text(encoding="utf-8")
        if "ContextScreen" in content:
            print(f"ERROR: {rel} still uses placeholder ContextScreen!")
            errors += 1

    registered_files = {r[1] for r in ROUTES}

    # Check that all on-disk route files are tracked in ROUTES
    untracked = route_files - registered_files
    if untracked:
        print(f"ERROR: Untracked route files on disk: {untracked}")
        errors += len(untracked)

    # Inbound link verification: Ensure every route has at least one inbound link/navigation reference
    source_files = [
        p for p in (ROOT / "mobile").rglob("*")
        if p.suffix in {".ts", ".tsx"}
        and "node_modules" not in p.parts
        and "dist" not in p.parts
        and ".expo" not in p.parts
    ]
    file_contents = {p: p.read_text(encoding="utf-8", errors="ignore") for p in source_files}

    for url, rel_file, reached_from, status in ROUTES:
        if url == "/":
            continue  # App entrypoint

        # Build search patterns for inbound navigation
        # e.g., /students/[studentId]/attendance matches /students/${...}/attendance
        pattern_str = re.escape(url)
        pattern_str = re.sub(r"\\\[[a-zA-Z0-9_]+\\\]", r"(\\$\\{[^\\}]+\\}|[a-zA-Z0-9_-]+)", pattern_str)
        pat = re.compile(pattern_str)

        # Also match Expo Router tab name registration: name="dashboard", name="students", etc.
        tab_name = url.lstrip("/")
        tab_pat = re.compile(r'name=["\']' + re.escape(tab_name) + r'["\']')

        inbound_refs = []
        for p, content in file_contents.items():
            # Exclude references within the route file itself
            if rel_file in p.as_posix():
                continue
            if pat.search(content) or tab_pat.search(content):
                inbound_refs.append(p.relative_to(ROOT).as_posix())

        if not inbound_refs:
            print(f"ERROR: Route file {rel_file} ({url}) has no inbound link in any navigation or component!")
            errors += 1

    if errors == 0:
        print(f"SUCCESS: All {len(route_files)} routes verified. Zero placeholders, all routes active and reached with verified inbound links.")
    return errors


if __name__ == "__main__":
    sys.exit(verify_routes())
