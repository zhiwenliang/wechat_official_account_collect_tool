import { describe, expectTypeOf, it } from "vitest";

import "./desktop-contract";
import type { BackendHealth, BackendStatus, DesktopBridge } from "./desktop-contract";

describe("desktop-contract", () => {
  it("BackendHealth matches service health payload", () => {
    expectTypeOf<BackendHealth>().toEqualTypeOf<{ status: "ok"; service: string }>();
  });

  it("BackendStatus is a discriminated union on state", () => {
    expectTypeOf<BackendStatus>().toEqualTypeOf<
      | { state: "starting"; message: string }
      | { state: "ready"; baseUrl: string; health: BackendHealth }
      | { state: "error"; message: string }
    >();
  });

  it("DesktopBridge exposes backend status", () => {
    expectTypeOf<DesktopBridge>().toMatchTypeOf<{
      getBackendStatus: () => Promise<BackendStatus>;
    }>();
  });

  it("augments global Window with optional desktop bridge", () => {
    expectTypeOf<Window["desktop"]>().toEqualTypeOf<DesktopBridge | undefined>();
  });
});
