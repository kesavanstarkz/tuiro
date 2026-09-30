const CURRENCY_LOCALES: Record<string, string> = {
    INR: "en-IN",
    USD: "en-US",
    GBP: "en-GB",
    EUR: "de-DE",
    CAD: "en-CA",
    AUD: "en-AU",
    SGD: "en-SG",
    AED: "en-AE",
};

export function getCurrencyLocale(currency: string = "INR"): string {
    return CURRENCY_LOCALES[currency.toUpperCase()] || "en-US";
}

export function getCurrencySymbol(currency: string = "INR"): string {
    const curr = (currency || "INR").toUpperCase();
    try {
        const formatter = new Intl.NumberFormat(getCurrencyLocale(curr), {
            style: "currency",
            currency: curr,
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        });
        const parts = formatter.formatToParts(0);
        const symbolPart = parts.find((p) => p.type === "currency");
        return symbolPart ? symbolPart.value : curr;
    } catch {
        return curr;
    }
}

/**
 * Formats a monetary amount using the organization currency setting.
 * Defaults to INR if not specified.
 */
export function formatMoney(amount: number | string | null | undefined, currency: string = "INR"): string {
    const numeric = typeof amount === "string" ? parseFloat(amount) : Number(amount);
    const val = isNaN(numeric) ? 0 : numeric;
    const curr = (currency || "INR").toUpperCase();
    try {
        return new Intl.NumberFormat(getCurrencyLocale(curr), {
            style: "currency",
            currency: curr,
            maximumFractionDigits: 0,
        }).format(val);
    } catch {
        return `${curr} ${val.toLocaleString()}`;
    }
}
