const { defineConfig } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "./tests/e2e",
  testMatch: /.*\.e2e\.ts/,
  use: {
    baseURL: "http://127.0.0.1:4173",
  },
  webServer: {
    cwd: __dirname,
    command: "npm run serve:e2e",
    url: "http://127.0.0.1:4173",
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
});
