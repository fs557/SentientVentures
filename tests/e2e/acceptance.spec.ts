import { expect, test } from "@playwright/test";

test("api health, founder portal, and dashboard navigation", async ({ page, request }) => {
  await expect.poll(async () => {
    const health = await request.get("http://localhost:8000/health");
    if (!health.ok()) {
      return null;
    }
    return health.json();
  }, { timeout: 30000 }).toMatchObject({
    status: "ok",
    version: "v1",
    workerAvailable: false,
  });

  await page.goto("http://localhost:8080/");
  await expect(page.getByRole("heading", { name: "Put your company in focus." })).toBeVisible();
  await expect(page.getByLabel("Company name")).toBeVisible();
  await expect(page.getByRole("button", { name: "Submit for evaluation" })).toBeVisible();

  await page.goto("http://localhost:8081/companies/aether-robotics/home");
  await expect(page.getByRole("heading", { name: "Aether Robotics" })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Evaluation categories" })).toBeVisible();
  await expect(page.getByLabel("Company under review")).toHaveValue("aether-robotics");

  await page.getByLabel("Company under review").selectOption("harborloop");
  await expect(page.getByRole("heading", { name: "HarborLoop" })).toBeVisible();

  await page.getByRole("link", { name: /^Market/ }).click();
  await expect(page.getByRole("heading", { name: "Market evaluation" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "What problems exist in the target market?" })).toBeVisible();
});
