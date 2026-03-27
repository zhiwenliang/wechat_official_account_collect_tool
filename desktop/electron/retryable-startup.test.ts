import { describe, expect, it, vi } from "vitest";

import { RetryableStartup } from "./retryable-startup";

describe("RetryableStartup", () => {
  it("reuses the same in-flight startup promise", async () => {
    let resolveBootstrap: (() => void) | undefined;
    const bootstrap = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          resolveBootstrap = resolve;
        }),
    );
    const startup = new RetryableStartup();

    const firstRun = startup.run(bootstrap);
    const secondRun = startup.run(bootstrap);

    expect(firstRun).toBe(secondRun);
    expect(bootstrap).toHaveBeenCalledTimes(1);

    resolveBootstrap?.();
    await firstRun;
  });

  it("allows retry after a failed startup", async () => {
    const bootstrap = vi
      .fn<() => Promise<void>>()
      .mockRejectedValueOnce(new Error("boom"))
      .mockResolvedValueOnce(undefined);
    const startup = new RetryableStartup();

    await expect(startup.run(bootstrap)).rejects.toThrow("boom");
    await expect(startup.run(bootstrap)).resolves.toBeUndefined();

    expect(bootstrap).toHaveBeenCalledTimes(2);
  });
});
