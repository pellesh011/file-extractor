import type {
  StartDownloadRequest,
  StartDownloadResponse,
  TaskStatusResponse,
  FilesResponse,
} from './types';

const API_BASE = '/api';

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

export const api = {
  startDownload: (body: StartDownloadRequest) =>
    request<StartDownloadResponse>('/download/start', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  getTaskStatus: (taskId: string) =>
    request<TaskStatusResponse>(`/download/${taskId}`),

  getFiles: (params: { page?: number; per_page?: number; status?: string } = {}) => {
    const searchParams = new URLSearchParams();
    if (params.page) searchParams.set('page', String(params.page));
    if (params.per_page) searchParams.set('per_page', String(params.per_page));
    if (params.status) searchParams.set('status', params.status);
    const query = searchParams.toString();
    return request<FilesResponse>(`/files${query ? `?${query}` : ''}`);
  },

  calculateStats: (fileIds: string[]) =>
    request<{ overall: Record<string, number>; per_file: Record<string, Record<string, number>> }>(
      '/files/calculate',
      {
        method: 'POST',
        body: JSON.stringify({ file_ids: fileIds }),
      }
    ),
};
