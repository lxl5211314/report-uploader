import { FileItem } from '../services/api';
import { FlatDir } from './FileTree';

interface MoveMenuProps {
  file: FileItem;
  directories: FlatDir[];
  onMove: (fileId: number, targetDirectoryId: number) => void;
}

export default function MoveMenu({ file, directories, onMove }: MoveMenuProps) {
  return (
    <select
      className="move-menu"
      aria-label={`移动 ${file.name} 到`}
      value=""
      onChange={(e) => {
        if (e.target.value) {
          onMove(file.id, Number(e.target.value));
        }
      }}
    >
      <option value="">移动到…</option>
      {directories
        .filter((d) => d.id !== file.directory_id)
        .map((d) => (
          <option key={d.id} value={d.id}>
            {d.label}
          </option>
        ))}
    </select>
  );
}
