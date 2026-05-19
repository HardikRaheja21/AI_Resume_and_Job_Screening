const path = require("path");
const { test, expect } = require("@playwright/test");

function uniqueEmail(prefix = "e2e") {
  return `${prefix}_${Date.now()}_${Math.floor(Math.random() * 100000)}@example.com`;
}

test.describe("Swagger UI + API flows", () => {
  test.beforeEach(async ({ page, baseURL }) => {
    await page.goto(`${baseURL}/docs`);
    await expect(page.locator(".swagger-ui")).toBeVisible();
  });

  test("signs up a user from /auth/signup", async ({ request, baseURL }) => {
    const email = uniqueEmail("signup");
    const response = await request.post(`${baseURL}/auth/signup`, {
      data: {
        email,
        password: "Secret123",
        full_name: "Swagger Signup User",
      },
    });

    expect(response.ok()).toBeTruthy();
    const payload = await response.json();
    expect(payload.email).toBe(email);
  });

  test("logs in a user from /auth/login and returns bearer token", async ({ request, baseURL }) => {
    const email = uniqueEmail("login");
    await request.post(`${baseURL}/auth/signup`, {
      data: {
        email,
        password: "Secret123",
        full_name: "Swagger Login User",
      },
    });

    const response = await request.post(`${baseURL}/auth/login`, {
      data: {
        email,
        password: "Secret123",
      },
    });
    expect(response.ok()).toBeTruthy();
    const payload = await response.json();
    expect(payload.access_token).toBeTruthy();
    expect(payload.token_type).toBe("bearer");
  });

  test("uploads JD + resumes via /resumes/upload", async ({ request, baseURL }) => {
    const email = uniqueEmail("upload");
    await request.post(`${baseURL}/auth/signup`, {
      data: { email, password: "Secret123", full_name: "Swagger Upload User" },
    });
    const loginResponse = await request.post(`${baseURL}/auth/login`, {
      data: { email, password: "Secret123" },
    });
    const loginPayload = await loginResponse.json();
    const token = loginPayload.access_token;

    const resumeA = path.resolve(__dirname, "fixtures", "resume_a.txt");
    const uploadResponse = await request.post(`${baseURL}/resumes/upload`, {
      headers: { Authorization: `Bearer ${token}` },
      multipart: {
        jd_text: "Looking for Python FastAPI SQL backend engineer",
        file: {
          name: "resume_a.txt",
          mimeType: "text/plain",
          buffer: require("fs").readFileSync(resumeA),
        },
      },
    });

    expect(uploadResponse.ok()).toBeTruthy();
    const payload = await uploadResponse.json();
    expect(payload.total_resumes).toBeGreaterThan(0);
    expect(Array.isArray(payload.results)).toBeTruthy();
  });
});
