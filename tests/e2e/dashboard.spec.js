const path = require("path");
const { test, expect } = require("@playwright/test");

function uniqueEmail(prefix = "ui") {
  return `${prefix}_${Date.now()}_${Math.floor(Math.random() * 100000)}@example.com`;
}

test.describe("Frontend dashboard flow", () => {
  test("signup, login, upload, history/filter, view/edit/delete", async ({ page, baseURL }) => {
    const email = uniqueEmail("dashboard");
    const password = "Secret123";

    await page.goto(`${baseURL}/frontend/login.html`);
    await page.fill("#signup-email", email);
    await page.fill("#signup-password", password);
    await page.click("#btn-signup");
    await expect(page.locator("#signup-msg")).toContainText("Signup successful");

    await page.fill("#login-email", email);
    await page.fill("#login-password", password);
    await page.click("#btn-login");
    await expect(page.locator("#login-msg")).toContainText("Login successful");
    await expect(page.locator("#auth-token")).not.toHaveValue("");

    await page.goto(`${baseURL}/frontend/dashboard.html`);
    const skipOnboarding = page.locator("#btn-skip-onboarding");
    if (await skipOnboarding.count()) {
      await skipOnboarding.click().catch(() => {});
    }
    await page.fill("#job-description", "Looking for Python FastAPI SQL backend engineer");

    const resumeA = path.resolve(__dirname, "fixtures", "resume_a.txt");
    const resumeB = path.resolve(__dirname, "fixtures", "resume_b.txt");
    await page.setInputFiles("#resumes", [resumeA, resumeB]);
    await page.click("#btn-parse");
    await expect(page.locator("#parse-msg")).toContainText("Success");
    await expect(page.locator("#results-container .leader-row")).toHaveCount(2);

    await page.click("#btn-load-history");
    await expect(page.locator("#parse-msg")).toContainText("Loaded");
    await expect(page.locator("#stats-summary")).toContainText("History stats");

    await page.fill("#filter-email", "john.doe@example.com");
    await page.click("#btn-apply-filters");
    await expect(page.locator("#results-container .leader-row")).toHaveCount(1);

    await page.click("#results-container .btn-view");
    await expect(page.locator("#resume-modal")).not.toHaveClass(/hidden/);
    await page.click("#btn-close-modal");
    await expect(page.locator("#resume-modal")).toHaveClass(/hidden/);

    const promptResponses = ["Updated Name", "Backend Engineer", "0.91"];
    page.on("dialog", async (dialog) => {
      if (dialog.type() === "prompt") {
        await dialog.accept(promptResponses.shift() || "");
        return;
      }
      await dialog.accept();
    });
    await page.click("#results-container .btn-edit");
    await expect(page.locator("#parse-msg")).toContainText("updated");

    await page.click("#results-container .btn-delete");
    await expect(page.locator("#parse-msg")).toContainText("deleted");
  });
});
