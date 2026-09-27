import { useCallback, useEffect, useMemo, useState } from 'react';
import DirectoryActions from '../components/DirectoryActions';
import FileTree, { flattenDirs } from '../components/FileTree';
import ReportView from '../components/ReportView';
import TemplatePicker from '../components/TemplatePicker';
import UploadButton from '../components/UploadButton';
import {
  ApiError,
  ColumnInfo,
  DirectoryNode,
  FileItem,
  ReportItem,
  TemplateItem,
  api,
} from '../services/api';

export default function WorkspacePage() {
  const [tree, setTree] = useState<DirectoryNode[]>([]);
  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [columns, setColumns] = useState<ColumnInfo[] | null>(null);
  const [selectedFile, setSelectedFile] = useState<FileItem | null>(null);
  const [selectedDirId, setSelectedDirId] = useState<number | null>(null);
  const [report, setReport] = useState<ReportItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [slowHint, setSlowHint] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const payload = await api.listDirectories();
      setTree(payload.tree);
      setError(null);
    } catch (e) {
      setError((e as ApiError).message || '加载目录失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    api
      .listTemplates()
      .then((p) => setTemplates(p.templates))
      .catch((e: ApiError) => setError(e.message || '加载模板失败'));
  }, [refresh]);

  async function handleSelectFile(file: FileItem) {
    setSelectedFile(file);
    setReport(null);
    setError(null);
    try {
      const payload = await api.getColumns(file.id);
      setColumns(payload.columns);
    } catch (e) {
      setColumns(null);
      setError((e as ApiError).message || '解析文件失败');
    }
  }

  async function handleMoveFile(fileId: number, targetDirectoryId: number) {
    try {
      await api.moveFile(fileId, targetDirectoryId);
      await refresh();
    } catch (e) {
      setError((e as ApiError).message || '移动文件失败');
    }
  }

  const flatDirs = useMemo(() => flattenDirs(tree), [tree]);
  const selectedDir = useMemo(() => {
    if (selectedDirId === null) return null;
    const stack = [...tree];
    while (stack.length > 0) {
      const node = stack.pop()!;
      if (node.id === selectedDirId) return node;
      stack.push(...node.children);
    }
    return null;
  }, [tree, selectedDirId]);

  async function handleGenerate(
    template: TemplateItem,
    params: Record<string, unknown>,
  ) {
    if (!selectedFile) return;
    setGenerating(true);
    setError(null);
    setSlowHint(false);
    // FR-013: 超过 10 秒给出“仍在处理”反馈，不得无响应
    const slowTimer = window.setTimeout(() => setSlowHint(true), 10_000);
    try {
      const created = await api.generateReport(selectedFile.id, template.id, params);
      setReport(created);
    } catch (e) {
      setError((e as ApiError).message || '报表生成失败');
    } finally {
      window.clearTimeout(slowTimer);
      setSlowHint(false);
      setGenerating(false);
    }
  }

  return (
    <div className="workspace">
      <header className="app-header">
        <h1>上传报表工具</h1>
        <p className="subtitle">上传 Excel/CSV → 选择模板 → 生成并下载报表</p>
      </header>

      {error && (
        <div role="alert" className="error-banner global">
          {error}
        </div>
      )}

      <div className="workspace-body">
        <aside className="panel tree-panel">
          <h2>目录</h2>
          <UploadButton tree={tree} onUploaded={refresh} />
          <DirectoryActions
            tree={tree}
            selectedDir={selectedDir}
            onChanged={refresh}
          />
          {loading ? (
            <p className="empty-hint">加载中…</p>
          ) : (
            <FileTree
              nodes={tree}
              flatDirs={flatDirs}
              selectedFileId={selectedFile?.id ?? null}
              selectedDirId={selectedDirId}
              onSelectFile={handleSelectFile}
              onSelectDir={setSelectedDirId}
              onMoveFile={handleMoveFile}
            />
          )}
        </aside>

        <main className="panel main-panel">
          <h2>生成报表</h2>
          {selectedFile && (
            <p className="selected-file">
              已选文件：<strong>{selectedFile.name}</strong>
              {columns && `（${columns.length} 列）`}
            </p>
          )}
          <TemplatePicker
            templates={templates}
            columns={columns}
            hasFile={selectedFile !== null}
            busy={generating}
            onGenerate={handleGenerate}
          />
          {slowHint && (
            <p role="status" className="slow-hint">
              已超过 10 秒，报表仍在处理中，请稍候…（大文件可能更慢）
            </p>
          )}
          {report && <ReportView report={report} />}
        </main>
      </div>
    </div>
  );
}
