import { useMemo, useState } from 'react';
import { ColumnInfo, TemplateItem } from '../services/api';

interface TemplatePickerProps {
  templates: TemplateItem[];
  columns: ColumnInfo[] | null;
  hasFile: boolean;
  busy: boolean;
  onGenerate: (
    template: TemplateItem,
    params: Record<string, unknown>,
  ) => void;
}

export default function TemplatePicker({
  templates,
  columns,
  hasFile,
  busy,
  onGenerate,
}: TemplatePickerProps) {
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [groupBy, setGroupBy] = useState('');
  const [valueBy, setValueBy] = useState('');
  const [agg, setAgg] = useState('sum');
  const [sortBy, setSortBy] = useState('');
  const [n, setN] = useState('10');

  const selected = templates.find((t) => t.id === selectedId) ?? null;
  const stringColumns = useMemo(
    () => (columns ?? []).filter((c) => c.type === 'string'),
    [columns],
  );
  const numericColumns = useMemo(
    () => (columns ?? []).filter((c) => c.type === 'number'),
    [columns],
  );

  const nValue = Number(n);
  const nValid = Number.isInteger(nValue) && nValue >= 1 && nValue <= 100;

  let paramsValid = true;
  if (selected?.requires_column === 'group') {
    paramsValid = groupBy !== '';
  } else if (selected?.requires_column === 'top') {
    paramsValid = sortBy !== '' && nValid;
  }

  function handleGenerate() {
    if (!selected) return;
    const params: Record<string, unknown> = { ...selected.defaults };
    if (selected.requires_column === 'group') {
      params.group_by = groupBy;
      params.agg = agg;
      if (valueBy) params.value_by = valueBy;
    } else if (selected.requires_column === 'top') {
      params.sort_by = sortBy;
      params.n = nValue;
    }
    onGenerate(selected, params);
  }

  if (templates.length === 0) {
    return <p className="empty-hint">暂无可用模板</p>;
  }

  return (
    <div className="template-picker">
      <div className="template-list" role="radiogroup" aria-label="报表模板">
        {templates.map((t) => (
          <label key={t.id} className="template-option">
            <input
              type="radio"
              name="template"
              checked={selectedId === t.id}
              onChange={() => setSelectedId(t.id)}
            />
            <span className="template-name">{t.name}</span>
            {t.description && (
              <span className="template-desc">{t.description}</span>
            )}
          </label>
        ))}
      </div>

      {selected?.requires_column === 'group' && columns && (
        <div className="param-row">
          <label>
            分组列
            <select
              value={groupBy}
              onChange={(e) => setGroupBy(e.target.value)}
              aria-label="分组列"
            >
              <option value="">请选择</option>
              {stringColumns.map((c) => (
                <option key={c.name} value={c.name}>
                  {c.name}
                </option>
              ))}
              {stringColumns.length === 0 &&
                columns.map((c) => (
                  <option key={c.name} value={c.name}>
                    {c.name}
                  </option>
                ))}
            </select>
          </label>
          <label>
            聚合列（可选）
            <select
              value={valueBy}
              onChange={(e) => setValueBy(e.target.value)}
              aria-label="聚合列"
            >
              <option value="">仅统计行数</option>
              {numericColumns.map((c) => (
                <option key={c.name} value={c.name}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            聚合方式
            <select
              value={agg}
              onChange={(e) => setAgg(e.target.value)}
              aria-label="聚合方式"
            >
              <option value="sum">求和</option>
              <option value="mean">平均</option>
            </select>
          </label>
        </div>
      )}

      {selected?.requires_column === 'top' && columns && (
        <div className="param-row">
          <label>
            排序列
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              aria-label="排序列"
            >
              <option value="">请选择数值列</option>
              {numericColumns.map((c) => (
                <option key={c.name} value={c.name}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            N（1-100）
            <input
              type="number"
              min={1}
              max={100}
              value={n}
              onChange={(e) => setN(e.target.value)}
              aria-label="N"
            />
          </label>
          {!nValid && <span className="param-error">N 必须在 1-100 之间</span>}
        </div>
      )}

      <button
        type="button"
        className="generate-btn"
        disabled={!hasFile || !selected || !paramsValid || busy}
        onClick={handleGenerate}
      >
        {busy ? '生成中…' : '生成报表'}
      </button>
      {!hasFile && <p className="empty-hint">请先在左侧选择一个数据文件</p>}
    </div>
  );
}
