import { DirectoryNode, FileItem } from '../services/api';
import MoveMenu from './MoveMenu';

export interface FlatDir {
  id: number;
  label: string;
}

export function flattenDirs(
  nodes: DirectoryNode[],
  depth = 0,
): FlatDir[] {
  const out: FlatDir[] = [];
  for (const node of nodes) {
    out.push({ id: node.id, label: `${'　'.repeat(depth)}${node.name}` });
    out.push(...flattenDirs(node.children, depth + 1));
  }
  return out;
}

export function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const DRAG_MIME = 'application/x-file-id';

interface FileTreeProps {
  nodes: DirectoryNode[];
  flatDirs: FlatDir[];
  selectedFileId: number | null;
  selectedDirId: number | null;
  onSelectFile: (file: FileItem) => void;
  onSelectDir: (directoryId: number) => void;
  onMoveFile: (fileId: number, targetDirectoryId: number) => void;
}

export default function FileTree({
  nodes,
  flatDirs,
  selectedFileId,
  selectedDirId,
  onSelectFile,
  onSelectDir,
  onMoveFile,
}: FileTreeProps) {
  if (nodes.length === 0) {
    return <p className="empty-hint">暂无目录，请先上传文件</p>;
  }
  return (
    <ul className="tree" role="tree">
      {nodes.map((node) => (
        <li
          key={node.id}
          role="treeitem"
          aria-expanded="true"
          className={
            'tree-dir' + (selectedDirId === node.id ? ' selected-dir' : '')
          }
          onClick={() => onSelectDir(node.id)}
          onDragOver={(e) => {
            if (e.dataTransfer.types.includes(DRAG_MIME)) {
              e.preventDefault();
              e.currentTarget.classList.add('drop-target');
            }
          }}
          onDragLeave={(e) => {
            e.currentTarget.classList.remove('drop-target');
          }}
          onDrop={(e) => {
            e.preventDefault();
            e.currentTarget.classList.remove('drop-target');
            const fileId = e.dataTransfer.getData(DRAG_MIME);
            if (fileId) {
              onMoveFile(Number(fileId), node.id);
            }
          }}
        >
          <span className="dir-name">📁 {node.name}</span>
          {node.files.length > 0 && (
            <ul className="tree-files" role="group">
              {node.files.map((file) => (
                <li key={file.id} role="treeitem">
                  <div className="file-row">
                    <button
                      type="button"
                      className={
                        'file-item' +
                        (selectedFileId === file.id ? ' selected' : '')
                      }
                      draggable
                      onDragStart={(e) => {
                        e.dataTransfer.setData(DRAG_MIME, String(file.id));
                        e.dataTransfer.effectAllowed = 'move';
                      }}
                      onClick={() => onSelectFile(file)}
                    >
                      <span className="file-name">{file.name}</span>
                      <span className="file-size">
                        {formatSize(file.size_bytes)}
                      </span>
                    </button>
                    <MoveMenu
                      file={file}
                      directories={flatDirs}
                      onMove={onMoveFile}
                    />
                  </div>
                </li>
              ))}
            </ul>
          )}
          {node.children.length > 0 && (
            <FileTree
              nodes={node.children}
              flatDirs={flatDirs}
              selectedFileId={selectedFileId}
              selectedDirId={selectedDirId}
              onSelectFile={onSelectFile}
              onSelectDir={onSelectDir}
              onMoveFile={onMoveFile}
            />
          )}
        </li>
      ))}
    </ul>
  );
}
