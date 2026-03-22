import { describe, expect, it } from "vitest";

import { renderBackendCopy } from "./App";

describe("renderBackendCopy", () => {
  it("describes a ready backend", () => {
    expect(
      renderBackendCopy({
        state: "ready",
        health: {
          status: "ok",
          service: "desktop-backend",
        },
      }),
    ).toEqual({
      title: "已连接",
      description: "backend service: desktop-backend",
    });
  });

  it("describes a backend startup failure", () => {
    expect(
      renderBackendCopy({
        state: "error",
        message: "python not found",
      }),
    ).toEqual({
      title: "启动失败",
      description: "python not found",
    });
  });
});
