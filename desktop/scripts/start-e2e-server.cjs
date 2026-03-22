const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");

const PROJECT_DIR = path.resolve(__dirname, "..");
const DIST_DIR = path.resolve(PROJECT_DIR, "dist");
const HOST = "127.0.0.1";
const PORT = 4173;

function contentType(filePath) {
  switch (path.extname(filePath)) {
    case ".html":
      return "text/html; charset=utf-8";
    case ".js":
      return "text/javascript; charset=utf-8";
    case ".css":
      return "text/css; charset=utf-8";
    case ".json":
      return "application/json; charset=utf-8";
    case ".svg":
      return "image/svg+xml";
    case ".png":
      return "image/png";
    case ".ico":
      return "image/x-icon";
    default:
      return "application/octet-stream";
  }
}

function serveFile(res, filePath) {
  const body = fs.readFileSync(filePath);
  res.writeHead(200, {
    "Content-Type": contentType(filePath),
    "Content-Length": body.length,
  });
  res.end(body);
}

function main() {
  if (!fs.existsSync(DIST_DIR)) {
    throw new Error("dist directory not found; run npm run build first");
  }

  const server = http.createServer((req, res) => {
    const urlPath = new URL(req.url ?? "/", `http://${HOST}:${PORT}`).pathname;
    const relativePath = urlPath === "/" ? "index.html" : urlPath.slice(1);
    const filePath = path.resolve(DIST_DIR, relativePath);

    if (filePath.startsWith(DIST_DIR) && fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
      serveFile(res, filePath);
      return;
    }

    serveFile(res, path.resolve(DIST_DIR, "index.html"));
  });

  server.listen(PORT, HOST, () => {
    console.log(`Serving ${DIST_DIR} at http://${HOST}:${PORT}`);
  });

  const close = () => {
    server.close(() => process.exit(0));
  };

  process.on("SIGINT", close);
  process.on("SIGTERM", close);
}

try {
  main();
} catch (error) {
  console.error(error);
  process.exit(1);
}
