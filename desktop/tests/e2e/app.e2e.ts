import { expect, test } from "@playwright/test";

test("renders the desktop shell", async ({ page }) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: "微信公众号文章采集工具" }),
  ).toBeVisible();
});
