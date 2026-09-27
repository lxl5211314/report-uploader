import { useState } from 'react';
import { ApiError, DirectoryNode, api } from '../services/api';
import { flattenDirs } from './FileTree';

interface DirectoryActionsProps {
  tree: DirectoryNode[];
  selectedDir: DirectoryNode | null;
  onChanged: () => void;
}

export default function DirectoryActions({
  tree,
  selectedDir,
  onChanged,
}: DirectoryActionsProps) {
  const directories = flattenDirs(tree);
  const [mode, setMode] = useState<'idle' | 'create' | 'rename'>('idle');
  const [parentChoice, setParentChoice] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function startCreate() {
    setMode('create');
    setName('');
    setParentChoice('');
    setError(null);
  }

  function startRename() {
    if (!selectedDir) return;
    setMode('rename');
    setName(selectedDir.name);
    setError(null);
  }

  async function submitCreate() {
    if (!name.trim()) {
      setError('请输入目录名称');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.createDirectory(
        name.trim(),
        parentChoice ? Number(parentChoice) : null,
      );
      setMode('idle');
      onChanged();
    } catch (e) {
      setError((e as ApiError).message || '创建目录失败');
    } finally {
      setBusy(false);
    }
  }

  async function submitRename() {
    if (!selectedDir) return;
    if (!name.trim()) {
      setError('请输入目录名称');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.renameDirectory(selectedDir.id, name.trim());
      setMode('idle');
      onChanged();
    } catch (e) {
      setError((e as ApiError).message || '重命名失败');
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    if (!selectedDir) return;
    setBusy(true);
    setError(null);
    try {
      await api.deleteDirectory(selectedDir.id);
      onChanged();
    } catch (e) {
      setError((e as ApiError).message || '删除目录失败');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="dir-actions">
      <div className="dir-actions-row">
        <button type="button" onClick={startCreate}>
          新建目录
        </button>
        <button type="button" onClick={startRename} disabled={!selectedDir}>
          重命名
        </button>
        <button type="button" onClick={handleDelete} disabled={!selectedDir || busy}>
          删除目录
        </button>
      </div>

      {!selectedDir && mode === 'idle' && (
        <p className="empty-hint">点击左侧目录可重命名或删除</p>
      )}

      {mode === 'create' && (
        <div className="dir-form">
          <label>
            上级目录
            <select
              value={parentChoice}
              onChange={(e) => setParentChoice(e.target.value)}
              aria-label="上级目录"
            >
              <option value="">顶级</option>
              {directories.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            名称
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              aria-label="目录名称"
              placeholder="例如：销售"
            />
          </label>
          <button type="button" onClick={submitCreate} disabled={busy}>
            创建
          </button>
          <button type="button" onClick={() => setMode('idle')} disabled={busy}>
            取消
          </button>
        </div>
      )}

      {mode === 'rename' && selectedDir && (
        <div className="dir-form">
          <label>
            新名称
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              aria-label="目录新名称"
            />
          </label>
          <button type="button" onClick={submitRename} disabled={busy}>
            保存
          </button>
          <button type="button" onClick={() => setMode('idle')} disabled={busy}>
            取消
          </button>
        </div>
      )}

      {error && (
        <div role="alert" className="error-banner">
          {error}
        </div>
      )}
    </div>
  );
}
