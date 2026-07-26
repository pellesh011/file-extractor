export interface StartDownloadRequest {
  candidate_id?: string | null;
}

export interface StartDownloadResponse {
  task_id: string;
}

export interface TaskStatusResponse {
  task_id: string;
  status: string;
  received_files: number;
  processed_files: number;
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
  blocked_until: string | null;
  block_reason: string | null;
}

export interface FileItem {
  id: string;
  filename: string;
  size: number;
  status: string;
  hash: string | null;
  created_at: string;
  uploaded_at: string | null;
}

export interface FilesResponse {
  items: FileItem[];
  total: number;
  page: number;
  per_page: number;
}

export interface StatisticsResponse {
  total_files: number;
  total_size: number;
  uploaded_files: number;
  failed_files: number;
  average_file_size: number;
}
