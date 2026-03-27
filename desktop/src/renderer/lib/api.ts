import type { BackendStatus } from "../../shared/desktop-contract";
import type { TaskSnapshotPayload } from "./task-events";

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

export type CalibrationStatusPayload = Record<string, boolean>;

export type ArticleDetailPayload = {
  id: number;
  url: string;
  title: string;
  publish_time: string;
  scraped_at: string;
  file_path: string;
  status: string;
  is_empty_content: number;
  content_markdown: string;
};

export function getCalibrationStatus() {
  return requestJson<CalibrationStatusPayload>("/api/calibration/status");
}

export function getArticleDetail(id: number) {
  return requestJson<ArticleDetailPayload>(`/api/article-detail?id=${id}`);
}

export async function imageProxyUrl(src: string): Promise<string> {
  const baseUrl = await getBaseUrl();
  return `${baseUrl}/api/image-proxy?url=${encodeURIComponent(src)}`;
}

export type TaskStartPayload = {
  task_id: string;
};

export type TaskStopPayload = {
  task_id: string;
  stopping: boolean;
};

export type TaskSnapshotResponse = TaskSnapshotPayload;
export type CalibrationAction =
  | "article_click_area"
  | "scroll_amount"
  | "visible_articles"
  | "more_button"
  | "copy_link_menu"
  | "tab_management"
  | "test";

export type CalibrationTaskResponsePayload = {
  task_id: string;
  accepted: boolean;
};

export function startCollectionTask() {
  return requestJson<TaskStartPayload>("/tasks/collection", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: "{}",
  });
}

export function startScrapeTask() {
  return requestJson<TaskStartPayload>("/tasks/scrape", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: "{}",
  });
}

export function startCalibrationTask(action: CalibrationAction) {
  return requestJson<TaskStartPayload>("/tasks/calibration", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ action }),
  });
}

export function stopTask(taskId: string) {
  return requestJson<TaskStopPayload>(`/tasks/${taskId}/stop`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: "{}",
  });
}

export function getTaskSnapshot(taskId: string) {
  return requestJson<TaskSnapshotResponse>(`/tasks/${taskId}`);
}

export function respondToCalibrationTask(
  taskId: string,
  payload:
    | { response: "record" }
    | { response: "continue"; value?: number }
    | { response: "confirm"; accepted: boolean },
) {
  return requestJson<CalibrationTaskResponsePayload>(`/tasks/${taskId}/respond`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}
