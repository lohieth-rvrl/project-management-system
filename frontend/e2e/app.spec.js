import { expect, test } from "@playwright/test";
import { field, login, logout } from "./helpers.js";

test.describe("sign in and dashboard", () => {
  test("wrong password is rejected, right one reaches the dashboard", async ({ page }) => {
    await page.goto("/#/login");
    await page.getByRole("textbox").first().fill("meera");
    await page.locator('input[type="password"]').fill("wrong-password");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByText("Invalid username or password")).toBeVisible();

    await page.locator('input[type="password"]').fill("demo12345");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
    await expect(page.getByText("Total tasks")).toBeVisible();
    await expect(page.getByText("Overdue tasks").first()).toBeVisible();
    await expect(page.locator("canvas").first()).toBeVisible(); // ECharts rendered
  });

  test("protected pages redirect to the login screen", async ({ page }) => {
    await page.goto("/#/projects");
    await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
  });
});

test.describe("projects, sprints, milestones, team", () => {
  test("manager creates a project then edits it, adds a sprint and a milestone", async ({ page }) => {
    await login(page, "meera");
    await page.getByRole("link", { name: "Projects" }).click();
    await page.getByRole("button", { name: "New project" }).click();
    const form = page.locator("form.form");
    await field(form, "Code").fill("E2E");
    await field(form, "Name").fill("End to end project");
    await field(form, "Budget").fill("5000");
    await field(form, "Cost per hour").fill("40");
    await form.getByRole("button", { name: "Create" }).click();

    await page.getByRole("link", { name: "E2E" }).click();
    await expect(page.getByRole("heading", { name: "E2E: End to end project" })).toBeVisible();

    const main = page.locator("form.form").first();
    await field(main, "Name").fill("Renamed by e2e");
    await main.getByRole("button", { name: "Save changes" }).click();
    await expect(page.getByRole("heading", { name: "E2E: Renamed by e2e" })).toBeVisible();

    const sprint = page.locator("form.form", { hasText: "Add sprint" });
    await field(sprint, "Name").fill("Sprint A");
    await field(sprint, "Start").fill("2026-10-05");
    await field(sprint, "End").fill("2026-10-19");
    await sprint.getByRole("button", { name: "Add sprint" }).click();
    await expect(page.getByRole("cell", { name: "Sprint A" })).toBeVisible();

    const ms = page.locator("form.form", { hasText: "Add milestone" });
    await field(ms, "Name").fill("Go live");
    await field(ms, "Due").fill("2026-11-01");
    await ms.getByRole("button", { name: "Add milestone" }).click();
    await expect(page.getByRole("cell", { name: "Go live" })).toBeVisible();

    const team = page.locator("form.form", { hasText: "Add to team" });
    await field(team, "Person").selectOption({ label: "Priya" });
    await team.getByRole("button", { name: "Add to team" }).click();
    await expect(page.getByRole("cell", { name: "priya" })).toBeVisible();
  });

  test("a sprint with end before start is rejected with a message", async ({ page }) => {
    await login(page, "meera");
    await page.goto("/#/projects");
    await page.getByRole("link", { name: "ERP" }).click();
    const sprint = page.locator("form.form", { hasText: "Add sprint" });
    await field(sprint, "Name").fill("Backwards");
    await field(sprint, "Start").fill("2026-10-20");
    await field(sprint, "End").fill("2026-10-01");
    await sprint.getByRole("button", { name: "Add sprint" }).click();
    await expect(page.locator(".error")).toContainText("end_date");
  });

  test("manager can delete a project, member cannot see the delete button", async ({ page }) => {
    await login(page, "priya");
    await page.goto("/#/projects");
    await page.getByRole("link", { name: "E2E" }).click();
    // wait for the page to be fully loaded first, otherwise "no delete button" proves nothing
    await expect(page.getByRole("button", { name: "Save changes" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Delete project" })).toHaveCount(0);
    await logout(page);

    await login(page, "meera");
    await expect(page.getByText("Role: manager")).toBeVisible(); // not the previous user's cached role
    await page.goto("/#/projects");
    await page.getByRole("link", { name: "E2E" }).click();
    page.once("dialog", (d) => d.accept());
    await page.getByRole("button", { name: "Delete project" }).click();
    await expect(page.getByRole("heading", { name: "Projects" })).toBeVisible();
    await expect(page.getByRole("link", { name: "E2E" })).toHaveCount(0);
  });
});

test.describe("task board and task details", () => {
  test("add a task, open it, add subtask and comment, move it to Done", async ({ page }) => {
    await login(page, "priya");
    await page.getByRole("link", { name: "Task Board" }).click();
    await page.getByPlaceholder("Add a task and press Enter").fill("E2E board task");
    await page.getByRole("button", { name: "Add", exact: true }).click();
    const card = page.locator(".tcard", { hasText: "E2E board task" });
    await expect(card).toBeVisible();

    await card.click();
    const drawer = page.getByRole("dialog", { name: "Task details" });
    await expect(drawer).toBeVisible();
    await drawer.getByPlaceholder("Add a subtask").fill("Sub one");
    await drawer.getByRole("button", { name: "Add", exact: true }).first().click();
    await expect(drawer.getByText("Sub one")).toBeVisible();
    await drawer.getByPlaceholder("Write a comment").fill("Looks good");
    await drawer.getByRole("button", { name: "Post" }).click();
    await expect(drawer.getByText("Looks good")).toBeVisible();

    await field(drawer, "Status").selectOption("done");
    await field(drawer, "Estimate (hours)").fill("3");
    await drawer.getByRole("button", { name: "Save changes" }).click();
    await expect(drawer).toHaveCount(0);
    const doneColumn = page.locator(".col", { hasText: "Done" });
    await expect(doneColumn.locator(".tcard", { hasText: "E2E board task" })).toBeVisible();
  });

  test("drag a card to another column", async ({ page }) => {
    await login(page, "priya");
    await page.goto("/#/board");
    await page.getByPlaceholder("Add a task and press Enter").fill("Drag me");
    await page.getByRole("button", { name: "Add", exact: true }).click();
    const card = page.locator(".tcard", { hasText: "Drag me" });
    await expect(card).toBeVisible();
    // Drop on the column header: it is already on screen, so Playwright does not scroll the
    // page mid-drag (a scroll puts a different card under the pointer and drags that one).
    await card.dragTo(page.locator(".col", { hasText: "In Progress" }).locator("h3"));
    await expect(page.locator(".col", { hasText: "In Progress" }).locator(".tcard", { hasText: "Drag me" })).toBeVisible();
  });

  test("board filters narrow the cards", async ({ page }) => {
    await login(page, "meera");
    await page.goto("/#/board");
    await page.getByPlaceholder("Add a task and press Enter").fill("Unique-needle-task");
    await page.getByRole("button", { name: "Add", exact: true }).click();
    await expect(page.locator(".tcard", { hasText: "Unique-needle-task" })).toBeVisible();
    await page.getByPlaceholder("Filter by title").fill("needle");
    await expect(page.locator(".tcard")).toHaveCount(1);
    await expect(page.getByText(/1 of \d+ tasks/)).toBeVisible();
  });

  test("viewer sees the board read-only", async ({ page }) => {
    await login(page, "divya");
    await page.goto("/#/board");
    await expect(page.getByPlaceholder("Add a task and press Enter")).toHaveCount(0);
    await page.locator(".tcard").first().click();
    const drawer = page.getByRole("dialog", { name: "Task details" });
    await expect(field(drawer, "Title")).toBeDisabled();
    await expect(drawer.getByRole("button", { name: "Save changes" })).toHaveCount(0);
  });
});

test.describe("task list, search and pagination", () => {
  test("all-tasks page filters and pages", async ({ page }) => {
    await login(page, "meera");
    await page.getByRole("link", { name: "All Tasks" }).click();
    await expect(page.locator("tbody tr").first()).toBeVisible();
    await expect(page.getByText(/1-25 of \d+/)).toBeVisible();
    await page.getByRole("button", { name: "Next" }).click();
    await expect(page.getByText(/Page 2 of/)).toBeVisible();

    await field(page, "Status").selectOption("blocked");
    await expect(page.getByText(/Page 1 of/)).toBeVisible(); // filter reset the page
    // The table keeps the old rows on screen until the filtered page arrives, so wait for it
    const statuses = page.locator("tbody tr td:nth-child(3)");
    await expect.poll(async () => {
      const all = await statuses.allTextContents();
      return all.length > 0 && all.every((s) => s === "Blocked");
    }).toBe(true);

    await page.getByLabel("Overdue").check();
    await page.getByLabel("Overdue").uncheck();
    await field(page, "Search").fill("zzz-no-such-task");
    await expect(page.getByText("No tasks match these filters.")).toBeVisible();
  });

  test("global search finds a task and opens it", async ({ page }) => {
    await login(page, "meera");
    await page.getByLabel("Search", { exact: true }).fill("Unique-needle");
    const hit = page.locator(".search-item", { hasText: "Unique-needle-task" });
    await expect(hit).toBeVisible();
    await hit.dispatchEvent("mousedown");
    await expect(page.getByRole("dialog", { name: "Task details" })).toBeVisible();
    await expect(field(page.getByRole("dialog"), "Title")).toHaveValue("Unique-needle-task");
  });
});

test.describe("people and account", () => {
  test("manager adds a person who signs in and changes their password", async ({ page }) => {
    await login(page, "meera");
    await page.getByRole("link", { name: "People" }).click();
    await page.getByRole("button", { name: "Add person" }).click();
    const form = page.locator("form.form");
    await field(form, "Username").fill("newhire");
    await field(form, "First name").fill("Nina");
    await field(form, "Password").fill("Start-pass-1234");
    await form.getByRole("button", { name: "Save" }).click();
    await expect(page.getByRole("cell", { name: "newhire" })).toBeVisible();
    // a manager must not be offered the admin role
    await page.getByRole("button", { name: "Add person" }).click();
    await expect(field(page.locator("form.form"), "Role").locator('option[value="admin"]')).toHaveCount(0);
    await logout(page);

    await login(page, "newhire", "Start-pass-1234");
    await page.getByRole("link", { name: "My Account" }).click();
    await field(page, "Current password").fill("Start-pass-1234");
    await field(page, "New password").fill("Second-pass-5678");
    await field(page, "Confirm new password").fill("Second-pass-5678");
    await page.getByRole("button", { name: "Change password" }).click();
    await expect(page.getByText("Password changed.")).toBeVisible();
    await logout(page);

    await login(page, "newhire", "Second-pass-5678");
  });

  test("mismatched confirmation is caught before sending", async ({ page }) => {
    await login(page, "priya");
    await page.goto("/#/account");
    await field(page, "Current password").fill("demo12345");
    await field(page, "New password").fill("Another-pass-1");
    await field(page, "Confirm new password").fill("Different-pass-2");
    await page.getByRole("button", { name: "Change password" }).click();
    await expect(page.getByText("New passwords do not match")).toBeVisible();
  });
});
