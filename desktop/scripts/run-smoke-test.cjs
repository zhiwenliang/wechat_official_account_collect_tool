const path = require("node:path");
const process = require("node:process");

require("ts-node/register/transpile-only");

const [, , testFile = "App.test.tsx"] = process.argv;

const resolvedTestFile = path.isAbsolute(testFile)
  ? testFile
  : path.resolve(process.cwd(), "src", "renderer", testFile);

require(resolvedTestFile);
