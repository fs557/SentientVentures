export const categoryLabel = (category: string) => ({ home: "Home", idea: "Idea", market: "Market", financial: "Financials", management: "Management" }[category] ?? category);
export const scoreText = (score: number | null) => score === null ? "Unavailable" : String(score);
export const dateText = (value: string) => new Intl.DateTimeFormat("de-DE", { dateStyle: "medium" }).format(new Date(value));
export const displayText = (value: string) => value.replace(/\b\d{1,3}(?:,\d{3})+\b/g, (number) => number.replaceAll(",", "."));
export const numberText = (value: number) => new Intl.NumberFormat("de-DE", { maximumFractionDigits: 2 }).format(value);
export const moneyText = (value: number | null, currency: string | null) => {
  if (value === null) return "Not provided";
  if (!currency) return `${new Intl.NumberFormat("de-DE", { maximumFractionDigits: 0 }).format(value)} (currency unavailable)`;
  return new Intl.NumberFormat("de-DE", { style: "currency", currency, maximumFractionDigits: 0 }).format(value);
};
export const investmentTermsText = ({ amount, currency, equityPercentage }: { amount: number | null; currency: string | null; equityPercentage: number | null }) => {
  const amountText = amount === null ? null : currency
    ? `${new Intl.NumberFormat("de-DE", { maximumFractionDigits: 0 }).format(amount)} ${new Intl.NumberFormat("de-DE", { style: "currency", currency, currencyDisplay: "narrowSymbol" }).formatToParts(0).find((part) => part.type === "currency")?.value ?? currency}`
    : `${new Intl.NumberFormat("de-DE", { maximumFractionDigits: 0 }).format(amount)} (currency unavailable)`;
  const equityText = equityPercentage === null ? null : `${numberText(equityPercentage)}%`;

  if (amountText && equityText) return `${amountText} for ${equityText}`;
  if (amountText) return amountText;
  if (equityText) return `${equityText} equity offered`;
  return "Terms unavailable";
};
