import type { BackendStatus } from "./task-events";

export interface DesktopBridge {
  getBackendStatus: () => Promise<BackendStatus>;
}

declare global {
  interface Window {
    desktop?: DesktopBridge;
  }
}

export async function getBackendStatus(): Promise<BackendStatus> {
  if (!window.desktop) {
    throw new Error("Desktop bridge unavailable");
  }

  return window.desktop.getBackendStatus();
}

export type StatisticsPayload = {
  total: number;
  pending: number;
  scraped: number;
  failed: number;
  empty_content: number;
  failed_urls: string[];
};

export type RecentArticlePayload = {
  id: number;
  title: string;
  publish_time: string;
  status: string;
  is_empty_content: number;
};

export type ArticlePayload = {
  id: number;
  url: string;
  title: string;
  publish_time: string;
  scraped_at: string;
  file_path: string;
  status: string;
  is_empty_content: number;
};

export type ArticlesPayload = {
  total: number;
  page: number;
  page_size: number;
  items: ArticlePayload[];
};

async function getBaseUrl() {
  const status = await getBackendStatus();
  if (status.state !== "ready") {
    throw new Error(status.message ?? "desktop backend is not ready");
  }

  return status.baseUrl;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const baseUrl = await getBaseUrl();
  const response = await fetch(`${baseUrl}${path}`, init);
  if (!response.ok) {
    throw new Error(`request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export function getStatistics() {
  return requestJson<StatisticsPayload>("/api/statistics");
}

export function getRecentArticles(limit = 5) {
  return requestJson<RecentArticlePayload[]>(`/api/recent-articles?limit=${limit}`);
}

export type ArticlesQuery = {
  status: string;
  search: string;
  page: number;
  pageSize: number;
};

export function getArticles(query: ArticlesQuery) {
  const params = new URLSearchParams({
    status: query.status,
    search: query.search,
    page: String(query.page),
    page_size: String(query.pageSize),
  });
  return requestJson<ArticlesPayload>(`/api/articles?${params.toString()}`);
}
