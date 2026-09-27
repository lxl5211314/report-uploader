export interface ApiError {
  code: string;
  message: string;
}

export interface DirectoryNode {
  id: number;
  name: string;
  parent_id: number | null;
  children: DirectoryNode[];
  files: FileItem[];
}

export interface FileItem {
  id: number;
  name: string;
  format: 'csv' | 'xlsx';
  size_bytes: number;
  directory_id: number;
  uploaded_at: string | null;
}

export interface DirectoryDto {
  id: number;
  name: string;
  parent_id: number | null;
}

export interface ColumnInfo {
  name: string;
  type: 'string' | 'number' | 'date' | 'boolean';
}

export interface ColumnsPayload {
  columns: ColumnInfo[];
  row_count: number;
}

export interface TemplateItem {
  id: number;
  code: 'overview' | 'group_summary' | 'top_n';
  name: string;
  description: string | null;
  requires_column: 'none' | 'group' | 'top';
  defaults: Record<string, unknown>;
}

export interface ReportSection {
  type: 'table' | 'stats';
  title: string;
  columns?: string[];
  rows?: unknown[][];
  items?: Record<string, unknown>[];
}

export interface ReportContent {
  file: { name: string; generated_at: string };
  dataset: { row_count: number; column_count: number };
  sections: ReportSection[];
}

export interface ReportItem {
  id: number;
  file_id: number;
  template_id: number;
  template: TemplateItem | null;
  status: 'generating' | 'succeeded' | 'failed';
  params: Record<string, unknown>;
  content: ReportContent | null;
  error_message: string | null;
  generated_at: string | null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) {
    let code = 'HTTP_' + res.status;
    let message = `请求失败（${res.status}）`;
    try {
      const body = await res.json();
      if (body && typeof body.code === 'string') code = body.code;
      if (body && typeof body.message === 'string') message = body.message;
    } catch {
      // non-JSON error body keeps defaults
    }
    const error: ApiError = { code, message };
    throw error;
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  listDirectories(): Promise<{ tree: DirectoryNode[] }> {
    return request('/api/v1/directories');
  },

  createDirectory(name: string, parentId: number | null): Promise<DirectoryDto> {
    return request('/api/v1/directories', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, parent_id: parentId }),
    });
  },

  renameDirectory(id: number, name: string): Promise<DirectoryDto> {
    return request(`/api/v1/directories/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    });
  },

  deleteDirectory(id: number): Promise<void> {
    return request(`/api/v1/directories/${id}`, { method: 'DELETE' });
  },

  async uploadFile(file: File, directoryId: number): Promise<FileItem> {
    const form = new FormData();
    form.append('file', file);
    form.append('directory_id', String(directoryId));
    return request('/api/v1/files/upload', { method: 'POST', body: form });
  },

  getColumns(fileId: number): Promise<ColumnsPayload> {
    return request(`/api/v1/files/${fileId}/columns`);
  },

  moveFile(fileId: number, targetDirectoryId: number): Promise<FileItem> {
    return request(`/api/v1/files/${fileId}/move`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target_directory_id: targetDirectoryId }),
    });
  },

  deleteFile(fileId: number): Promise<void> {
    return request(`/api/v1/files/${fileId}`, { method: 'DELETE' });
  },

  listTemplates(): Promise<{ templates: TemplateItem[] }> {
    return request('/api/v1/templates');
  },

  generateReport(
    fileId: number,
    templateId: number,
    params: Record<string, unknown>,
  ): Promise<ReportItem> {
    return request(`/api/v1/files/${fileId}/reports`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ template_id: templateId, params }),
    });
  },

  getReport(reportId: number): Promise<ReportItem> {
    return request(`/api/v1/reports/${reportId}`);
  },

  listFileReports(fileId: number): Promise<{ reports: ReportItem[] }> {
    return request(`/api/v1/files/${fileId}/reports`);
  },

  downloadUrl(reportId: number): string {
    return `/api/v1/reports/${reportId}/download`;
  },
};
