import React from "react";
import { act } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createRoot } from "react-dom/client";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import { ArticlesPage } from "./ArticlesPage";
import { useArticlesViewStore } from "../../state/app-store";

function createJsonResponse(payload: unknown) {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
    },
  });
}

async function renderArticlesPage() {
  const container = document.createElement("div");
  document.body.append(container);

  const client = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  const root = createRoot(container);

  await act(async () => {
    root.render(
      <QueryClientProvider client={client}>
        <ArticlesPage />
      </QueryClientProvider>,
    );
    await Promise.resolve();
  });

  return { container, root, client };
}

beforeAll(() => {
  (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
});

afterAll(() => {
  delete (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT;
});

afterEach(async () => {
  document.body.innerHTML = "";
  delete (window as typeof window & { desktop?: unknown }).desktop;
  await act(async () => {
    useArticlesViewStore.setState({
      status: "all",
      draftSearch: "",
      search: "",
      page: 1,
      pageSize: 20,
    });
  });
  vi.restoreAllMocks();
});

describe("ArticlesPage", () => {
  it("requests article data with the current search and filter controls", async () => {
    Object.defineProperty(window, "desktop", {
      configurable: true,
      value: {
        getBackendStatus: vi.fn().mockResolvedValue({
          state: "ready",
          baseUrl: "http://desktop-backend",
          health: {
            status: "ok",
            service: "desktop-backend",
          },
        }),
      },
    });

    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      const isSecondPage = url.includes("page=2");
      return Promise.resolve(
        createJsonResponse({
          total: 45,
          page: isSecondPage ? 2 : 1,
          page_size: 20,
          items: [
            {
              id: 9,
              url: isSecondPage ? "https://example.com/delta" : "https://example.com/gamma",
              title: isSecondPage ? "Delta" : "Gamma",
              publish_time: "2024-01-03 08:00:00",
              scraped_at: "",
              file_path: "",
              status: "scraped",
              is_empty_content: 0,
            },
          ],
        }),
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    const { container, root, client } = await renderArticlesPage();

    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    const searchInput = container.querySelector<HTMLInputElement>('input[name="article-search"]');
    const statusSelect = container.querySelector<HTMLSelectElement>('select[name="article-status"]');
    const searchButton = container.querySelector<HTMLButtonElement>('button[name="article-search-submit"]');
    const nextPageButton = () =>
      container.querySelector<HTMLButtonElement>('button[name="article-page-next"]');

    expect(searchInput).not.toBeNull();
    expect(statusSelect).not.toBeNull();
    expect(searchButton).not.toBeNull();

    if (!searchInput || !statusSelect || !searchButton) {
      throw new Error("expected search controls");
    }

    await act(async () => {
      statusSelect.value = "scraped";
      statusSelect.dispatchEvent(new Event("change", { bubbles: true }));
      useArticlesViewStore.getState().submitSearch("Gamma");
      await Promise.resolve();
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    const lastUrl = String(fetchMock.mock.calls[fetchMock.mock.calls.length - 1][0]);
    expect(lastUrl).toContain("/api/articles?");
    expect(lastUrl).toContain("status=scraped");
    expect(lastUrl).toContain("search=Gamma");
    expect(lastUrl).toContain("page=1");
    expect(lastUrl).toContain("page_size=20");

    // Wait for react-query to settle after the refetch
    await act(async () => {
      await Promise.resolve();
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    await act(async () => {
      const button = nextPageButton();
      if (!button) {
        throw new Error("expected next page button");
      }

      button.click();
      await Promise.resolve();
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    const pagedUrl = String(fetchMock.mock.calls[fetchMock.mock.calls.length - 1][0]);
    expect(pagedUrl).toContain("page=2");

    await act(async () => {
      root.unmount();
      client.clear();
    });
  });

  it("surfaces article query failures instead of showing an empty list", async () => {
    Object.defineProperty(window, "desktop", {
      configurable: true,
      value: {
        getBackendStatus: vi.fn().mockResolvedValue({
          state: "ready",
          baseUrl: "http://desktop-backend",
          health: {
            status: "ok",
            service: "desktop-backend",
          },
        }),
      },
    });

    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("request failed"))));

    const { container, root, client } = await renderArticlesPage();

    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    expect(container.textContent).toContain("文章列表加载失败");
    expect(container.textContent).toContain("request failed");

    await act(async () => {
      root.unmount();
      client.clear();
    });
  });
});
