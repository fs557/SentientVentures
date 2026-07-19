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

  // Test WalletProFun database integration and founder details
  await page.goto("http://localhost:8081/companies/walletprofun/home");
  await expect(page.getByRole("heading", { name: "WalletProFun" })).toBeVisible();
  
  await page.getByRole("link", { name: /^Management/ }).click();
  await expect(page.getByRole("heading", { name: "Management evaluation" })).toBeVisible();
  
  // Verify database integration card
  const dbCardTitle = page.getByRole("heading", { name: "Which projects have they done?" });
  await expect(dbCardTitle).toBeVisible();
  
  // Verify matching founders from DB are listed
  const founderDbSection = page.locator(".founder-db-profile");
  await expect(founderDbSection.getByText("Akshat Tandon")).toBeVisible();
  await expect(founderDbSection.getByText("Technical University of Munich")).toBeVisible();
  await expect(founderDbSection.getByText("OpportunityMap")).toBeVisible();
  
  await expect(founderDbSection.getByText("Binhui Shao")).toBeVisible();
  await expect(founderDbSection.getByText("Cambridge university")).toBeVisible();
  await expect(founderDbSection.getByText("OmniSkill Pathways: From Invisible Skills to Resilient Livelihoods")).toBeVisible();

  // Test the Founder Network Graph tab
  await page.getByRole("button", { name: "Founder Network Graph" }).click();
  await expect(page.getByRole("heading", { name: "Founder Connection Network" })).toBeVisible();
  
  // Verify the SVG canvas and legend
  await expect(page.locator("svg")).toBeVisible();
  await expect(page.getByText("Founder", { exact: true })).toBeVisible();
  await expect(page.getByText("University", { exact: true })).toBeVisible();
  await expect(page.getByText("Project", { exact: true })).toBeVisible();
  await expect(page.getByText("Hackathon", { exact: true })).toBeVisible();
});

