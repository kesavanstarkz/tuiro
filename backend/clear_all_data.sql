-- ==============================================================================
-- TUIRO DATABASE CLEANUP SCRIPT (TEMPORARY FOR TESTING)
-- Deletes all records from all application tables while preserving table schemas.
-- Preserves 'alembic_version' so migrations remain valid.
-- Re-seeds the default 'FREE' subscription plan so user registration works immediately.
--
-- Usage:
--   sqlite3 tuiro.db < clear_all_data.sql
--   or from project root:
--   sqlite3 backend/tuiro.db < backend/clear_all_data.sql
-- ==============================================================================

PRAGMA foreign_keys = OFF;

BEGIN TRANSACTION;

-- Academic & Testing Records
DELETE FROM test_marks;
DELETE FROM academic_tests;
DELETE FROM homework;
DELETE FROM assignments;

-- Attendance Records & Sessions
DELETE FROM attendance_records;
DELETE FROM attendance_sessions;
DELETE FROM group_attendance_records;
DELETE FROM group_attendance_sessions;

-- Timetable & Schedules
DELETE FROM schedule_entries;
DELETE FROM group_schedules;

-- Financial Records, Fees & Receipts
DELETE FROM receipts;
DELETE FROM payments;
DELETE FROM fee_payments;
DELETE FROM fees;
DELETE FROM student_fees;

-- Messaging & Notifications
DELETE FROM chat_messages;
DELETE FROM chat_participants;
DELETE FROM chat_threads;
DELETE FROM notifications;
DELETE FROM audit_logs;

-- Class / Group Rosters & Member Links
DELETE FROM class_students;
DELETE FROM class_teachers;
DELETE FROM group_members;
DELETE FROM student_parents;

-- People Entities
DELETE FROM parents;
DELETE FROM students;
DELETE FROM teachers;

-- Classes & Batches
DELETE FROM classes;
DELETE FROM groups;

-- Subscriptions, Sessions & Auth
DELETE FROM subscriptions;
DELETE FROM refresh_sessions;
DELETE FROM organization_members;
DELETE FROM users;
DELETE FROM organizations;

-- Reset Subscription Plans and insert default FREE plan
DELETE FROM subscription_plans;
INSERT INTO subscription_plans (id, name, monthly_price, annual_price, student_limit, teacher_limit, features, is_active)
VALUES ('d28e85107c5c466e86400e375aae18df', 'FREE', 0, 0, 20, NULL, '{}', 1);

COMMIT;

PRAGMA foreign_keys = ON;

-- Reclaim disk space
VACUUM;
