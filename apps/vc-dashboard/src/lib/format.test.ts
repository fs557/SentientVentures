import { describe, expect, it } from "vitest";
import { displayText, investmentTermsText, moneyText } from "./format";

describe("German number formatting", () => {
  it("normalizes grouped numbers embedded in submitted text", () => {
    expect(displayText("Revenue EUR 1,250,000 and burn EUR 115,000."))
      .toBe("Revenue EUR 1.250.000 and burn EUR 115.000.");
  });

  it("uses dots for monetary thousands and full investment terms", () => {
    expect(moneyText(9_900_000, "EUR")).toContain("9.900.000");
    expect(investmentTermsText({ amount: 100_000, currency: "EUR", equityPercentage: 1 }))
      .toBe("100.000 € for 1%");
  });
});
