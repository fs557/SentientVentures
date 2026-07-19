export const categoryLabel = (category: string) => ({ home: "Home", idea: "Idea", market: "Market", financial: "Financials", management: "Management" }[category] ?? category);
export const scoreText = (score: number | null) => score === null ? "Unavailable" : String(score);
export const dateText = (value: string) => new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(value));
export const moneyText = (value: number | null, currency: string | null) => {
  if (value === null) return "Not provided";
  if (!currency) return `${new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(value)} (currency unavailable)`;
  return new Intl.NumberFormat(undefined, { style: "currency", currency, maximumFractionDigits: 0 }).format(value);
};
export const investmentTermsText = ({ amount, currency, equityPercentage }: { amount: number | null; currency: string | null; equityPercentage: number | null }) => {
  const compactNumber = (value: number) => new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 }).format(value).replace(/K$/, "k");
  const amountText = amount === null ? null : currency
    ? `${new Intl.NumberFormat("en", { style: "currency", currency, currencyDisplay: "narrowSymbol" }).formatToParts(0).find((part) => part.type === "currency")?.value ?? currency}${compactNumber(amount)}`
    : `${compactNumber(amount)} (currency unavailable)`;
  const equityText = equityPercentage === null ? null : `${equityPercentage}%`;

  if (amountText && equityText) return `${amountText} for ${equityText}`;
  if (amountText) return amountText;
  if (equityText) return `${equityText} equity offered`;
  return "Terms unavailable";
};
