import { expect, test } from "@playwright/test";

test("renders the desktop shell", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByText("微信文章采集")).toBeVisible();
  await expect(page.getByRole("heading", { name: "启动失败" })).toBeVisible();
  await expect(page.getByRole("main").getByText("Desktop bridge unavailable")).toBeVisible();
});
