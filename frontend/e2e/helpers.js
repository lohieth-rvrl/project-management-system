import { expect } from "@playwright/test";

export const PASSWORD = "demo12345";

export async function login(page, username, password = PASSWORD) {
  await page.goto("/#/login");
  await page.getByRole("textbox").first().fill(username);
  await page.locator('input[type="password"]').fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("Signed in as")).toBeVisible();
}

export async function logout(page) {
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
}

// The app's labels sit directly before their input/select/textarea
export const field = (scope, text) => scope.locator(`label:text-is("${text}") + *`);
