import { useMemo, useState } from 'react';
import { ApiError, DirectoryNode, api } from '../services/api';

interface FlatDir {
  id: number;
  label: string;
}

function flatten(nodes: DirectoryNode[], prefix = '', depth = 0): FlatDir[] {
  const out: FlatDir[] = [];
  for (const node of nodes) {
    out.push({ id: node.id, label: `${'　'.repeat(depth)}${node.name}` });
    out.push(...flatten(node.children, prefix, depth + 1));
  }
  return out;
}

interface UploadButtonProps {
  tree: DirectoryNode[];
  onUploaded: () => void;
}

export default function UploadButton({ tree, onUploaded }: UploadButtonProps) {
  const directories = useMemo(() => flatten(tree), [tree]);
  const [directoryId, setDirectoryId] = useState<string>('');
  const [fileName, setFileName] = useState<string>('');
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!file) {
      setError('请先选择要上传的文件（csv 或 xlsx）');
      return;
    }
    if (!directoryId) {
      setError('请选择目标目录');
      return;
    }
    setUploading(true);
    setError(null);
    try {
      await api.uploadFile(file, Number(directoryId));
      setFile(null);
      setFileName('');
      onUploaded();
    } catch (e) {
      const err = e as ApiError;
      setError(err.message || '上传失败，请重试');
    } finally {
      setUploading(false);
    }
  }

  return (
    <form className="upload-form" onSubmit={handleSubmit}>
      <label>
        目标目录
        <select
          value={directoryId}
          onChange={(e) => setDirectoryId(e.target.value)}
          aria-label="目标目录"
        >
          <option value="">请选择目录</option>
          {directories.map((d) => (
            <option key={d.id} value={d.id}>
              {d.label}
            </option>
          ))}
        </select>
      </label>
      <label className="file-picker">
        文件
        <input
          type="file"
          accept=".csv,.xlsx"
          onChange={(e) => {
            const picked = e.target.files?.[0] ?? null;
            setFile(picked);
            setFileName(picked ? picked.name : '');
          }}
          aria-label="选择文件"
        />
      </label>
      <button type="submit" disabled={uploading}>
        {uploading ? '上传中…' : '上传'}
      </button>
      {fileName && <span className="file-picked">{fileName}</span>}
      {error && (
        <div role="alert" className="error-banner">
          {error}
        </div>
      )}
    </form>
  );
}
