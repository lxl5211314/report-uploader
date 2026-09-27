import { ReportItem, api } from '../services/api';

interface ReportViewProps {
  report: ReportItem;
}

export default function ReportView({ report }: ReportViewProps) {
  const content = report.content;
  return (
    <section className="report-view" aria-label="报表预览">
      <header className="report-header">
        <h3>{report.template?.name ?? '报表'}</h3>
        <span className="report-meta">
          源文件：{content?.file.name ?? '—'} · 生成于：
          {report.generated_at ?? '—'}
        </span>
        <a
          className="download-link"
          href={api.downloadUrl(report.id)}
          download
        >
          下载 xlsx
        </a>
      </header>

      {content && (
        <p className="dataset-meta">
          共 {content.dataset.row_count} 行 × {content.dataset.column_count} 列
        </p>
      )}

      {content?.sections.map((section, index) => (
        <div key={index} className="report-section">
          <h4>{section.title}</h4>
          {section.type === 'table' && section.columns && (
            <table>
              <thead>
                <tr>
                  {section.columns.map((c) => (
                    <th key={c}>{c}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(section.rows ?? []).map((row, ri) => (
                  <tr key={ri}>
                    {row.map((cell, ci) => (
                      <td key={ci}>{formatCell(cell)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {section.type === 'stats' && section.items && section.items.length > 0 && (
            <table>
              <thead>
                <tr>
                  {Object.keys(section.items[0]).map((k) => (
                    <th key={k}>{k}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {section.items.map((item, ii) => (
                  <tr key={ii}>
                    {Object.keys(section.items![0]).map((k) => (
                      <td key={k}>{formatCell(item[k])}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {section.type === 'stats' && (!section.items || section.items.length === 0) && (
            <p className="empty-hint">无数值列</p>
          )}
        </div>
      ))}
      {!content && (
        <p className="empty-hint">
          报表状态：{report.status}
          {report.error_message ? `（${report.error_message}）` : ''}
        </p>
      )}
    </section>
  );
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'number') {
    if (Number.isInteger(value)) return String(value);
    return value.toFixed(2);
  }
  if (typeof value === 'boolean') return value ? '是' : '否';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}
