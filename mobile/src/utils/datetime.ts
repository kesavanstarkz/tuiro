export const DEFAULT_TIMEZONE = "Asia/Kolkata";

export function getSafeTimezone(timezone?: string | null): string {
    if (!timezone) return DEFAULT_TIMEZONE;
    try {
        Intl.DateTimeFormat(undefined, { timeZone: timezone });
        return timezone;
    } catch {
        return DEFAULT_TIMEZONE;
    }
}

/**
 * Returns today's date formatted as YYYY-MM-DD in the organization's timezone.
 */
export function getOrgToday(timezone?: string | null): string {
    const tz = getSafeTimezone(timezone);
    const formatter = new Intl.DateTimeFormat("en-CA", {
        timeZone: tz,
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
    });
    return formatter.format(new Date());
}

/**
 * Returns the day of the week (0 = Monday, ..., 6 = Sunday) in the organization's timezone.
 * Matches ScheduleEntry.day_of_week where 0 is Monday and 6 is Sunday.
 */
export function getOrgDayOfWeek(timezone?: string | null, date: Date = new Date()): number {
    const tz = getSafeTimezone(timezone);
    const formatter = new Intl.DateTimeFormat("en-US", {
        timeZone: tz,
        weekday: "short",
    });
    const weekday = formatter.format(date);
    const map: Record<string, number> = {
        Mon: 0,
        Tue: 1,
        Wed: 2,
        Thu: 3,
        Fri: 4,
        Sat: 5,
        Sun: 6,
    };
    return map[weekday] ?? 0;
}

/**
 * Returns formatted date string in the organization's timezone (e.g., "Monday, Sep 30").
 */
export function formatOrgDate(timezone?: string | null, date: Date | string = new Date()): string {
    const tz = getSafeTimezone(timezone);
    const d = typeof date === "string" ? new Date(date) : date;
    return new Intl.DateTimeFormat(undefined, {
        timeZone: tz,
        weekday: "long",
        month: "short",
        day: "numeric",
    }).format(d);
}

/**
 * Returns HH:MM current time in the organization's timezone.
 */
export function getOrgCurrentTime(timezone?: string | null): string {
    const tz = getSafeTimezone(timezone);
    const formatter = new Intl.DateTimeFormat("en-GB", {
        timeZone: tz,
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
    });
    return formatter.format(new Date());
}
