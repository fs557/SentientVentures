export const categoryLabel = (category: string) => ({ home: "Home", idea: "Idea", market: "Market", financial: "Financials", management: "Management" }[category] ?? category);
export const scoreText = (score: number | null) => score === null ? "Unavailable" : String(score);
export const dateText = (value: string) => new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(value));
export const moneyText = (value: number | null, currency: string | null) => value === null ? "Not provided" : new Intl.NumberFormat(undefined, { style: "currency", currency: currency ?? "USD", maximumFractionDigits: 0 }).format(value);
