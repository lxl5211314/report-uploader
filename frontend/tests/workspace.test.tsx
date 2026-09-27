import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import WorkspacePage from '../src/pages/WorkspacePage';

type Route = { status?: number; body: unknown };

function stubFetch(routes: Record<string, Route>) {
  const mock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input.toString();
    // longest key first so specific routes win
    const key = Object.keys(routes)
      .sort((a, b) => b.length - a.length)
      .find((k) => url.includes(k));
    if (!key) throw new Error(`unmatched fetch: ${url}`);
    const route = routes[key];
    const status = route.status ?? 200;
    return {
      ok: status >= 200 && status < 300,
      status,
      json: async () => route.body,
    } as Response;
  });
  vi.stubGlobal('fetch', mock);
  return mock;
}

const treeRoute: Route = {
  body: {
    tree: [
      {
        id: 1,
        name: '销售',
        parent_id: null,
        children: [],
        files: [
          {
            id: 10,
            name: 'a.csv',
            format: 'csv',
            size_bytes: 2048,
            directory_id: 1,
            uploaded_at: '2026-01-01T00:00:00',
          },
        ],
      },
    ],
  },
};

const templatesRoute: Route = {
  body: {
    templates: [
      {
        id: 1,
        code: 'overview',
        name: '数据概览',
        description: '行列统计',
        requires_column: 'none',
        defaults: {},
      },
      {
        id: 2,
        code: 'group_summary',
        name: '分组汇总',
        description: '按列聚合',
        requires_column: 'group',
        defaults: { agg: 'sum' },
      },
      {
        id: 3,
        code: 'top_n',
        name: 'TOP N 排行',
        description: '取前 N 行',
        requires_column: 'top',
        defaults: { n: 10 },
      },
    ],
  },
};

afterEach(() => {
  vi.unstubAllGlobals();
});

test('renders directory tree after mocked fetch', async () => {
  stubFetch({
    '/api/v1/templates': templatesRoute,
    '/api/v1/directories': treeRoute,
  });

  render(<WorkspacePage />);

  expect(await screen.findByText('销售')).toBeInTheDocument();
  expect(screen.getByText('a.csv')).toBeInTheDocument();
  expect(screen.getByText('2.0 KB')).toBeInTheDocument();
});

test('upload error message is shown to the user', async () => {
  stubFetch({
    '/api/v1/templates': templatesRoute,
    '/api/v1/directories': treeRoute,
    '/api/v1/files/upload': {
      status: 409,
      body: {
        code: 'FILE_NAME_CONFLICT',
        message: '目标目录中已存在同名文件：a.csv',
      },
    },
  });

  render(<WorkspacePage />);
  await screen.findByText('销售');

  const fileInput = screen.getByLabelText('选择文件');
  const file = new File(['city,amount\nbeijing,1\n'], 'a.csv', {
    type: 'text/csv',
  });
  await userEvent.upload(fileInput, file);

  await userEvent.selectOptions(screen.getByLabelText('目标目录'), '1');
  await userEvent.click(screen.getByRole('button', { name: '上传' }));

  expect(
    await screen.findByText('目标目录中已存在同名文件：a.csv'),
  ).toBeInTheDocument();
});

test('overview report renders a section table end to end', async () => {
  stubFetch({
    '/api/v1/templates': templatesRoute,
    '/api/v1/directories': treeRoute,
    '/api/v1/files/10/columns': {
      body: {
        columns: [
          { name: 'city', type: 'string' },
          { name: 'amount', type: 'number' },
        ],
        row_count: 5,
      },
    },
    '/api/v1/files/10/reports': {
      status: 201,
      body: {
        id: 30,
        file_id: 10,
        template_id: 1,
        template: {
          id: 1,
          code: 'overview',
          name: '数据概览',
          description: '行列统计',
          requires_column: 'none',
          defaults: {},
        },
        status: 'succeeded',
        params: {},
        content: {
          file: { name: 'a.csv', generated_at: '2026-01-01T00:00:00' },
          dataset: { row_count: 5, column_count: 2 },
          sections: [
            {
              type: 'table',
              title: '字段清单',
              columns: ['字段', '类型'],
              rows: [
                ['city', 'string'],
                ['amount', 'number'],
              ],
            },
          ],
        },
        error_message: null,
        generated_at: '2026-01-01T00:00:00',
      },
    },
  });

  render(<WorkspacePage />);
  await screen.findByText('销售');

  await userEvent.click(screen.getByText('a.csv'));
  await screen.findByText(/已选文件/);

  await userEvent.click(screen.getByLabelText(/数据概览/));
  await userEvent.click(screen.getByRole('button', { name: '生成报表' }));

  expect(await screen.findByText('字段清单')).toBeInTheDocument();
  const table = screen.getByRole('table');
  expect(within(table).getByText('字段')).toBeInTheDocument();
  expect(within(table).getByText('city')).toBeInTheDocument();
  expect(within(table).getByText('number')).toBeInTheDocument();
  expect(screen.getByRole('link', { name: '下载 xlsx' })).toHaveAttribute(
    'href',
    '/api/v1/reports/30/download',
  );
});

test('group_summary requires group column and sends params; top_n validates N', async () => {
  const mock = stubFetch({
    '/api/v1/templates': templatesRoute,
    '/api/v1/directories': treeRoute,
    '/api/v1/files/10/columns': {
      body: {
        columns: [
          { name: 'city', type: 'string' },
          { name: 'amount', type: 'number' },
        ],
        row_count: 5,
      },
    },
    '/api/v1/files/10/reports': {
      status: 201,
      body: {
        id: 31,
        file_id: 10,
        template_id: 2,
        template: null,
        status: 'succeeded',
        params: {},
        content: {
          file: { name: 'a.csv', generated_at: '2026-01-01T00:00:00' },
          dataset: { row_count: 5, column_count: 2 },
          sections: [],
        },
        error_message: null,
        generated_at: '2026-01-01T00:00:00',
      },
    },
  });

  render(<WorkspacePage />);
  await screen.findByText('销售');
  await userEvent.click(screen.getByText('a.csv'));
  await screen.findByText(/已选文件/);

  // group_summary: param UI appears, generate blocked until group_by chosen
  await userEvent.click(screen.getByLabelText(/分组汇总/));
  const groupSelect = screen.getByLabelText('分组列');
  expect(groupSelect).toBeInTheDocument();
  expect(
    screen.getByRole('button', { name: '生成报表' }),
  ).toBeDisabled();
  await userEvent.selectOptions(groupSelect, 'city');
  await userEvent.click(screen.getByRole('button', { name: '生成报表' }));

  await waitFor(() => {
    const post = mock.mock.calls.find(
      (c) =>
        String(c[0]).includes('/api/v1/files/10/reports') &&
        (c[1]?.method ?? 'GET') === 'POST',
    );
    expect(post).toBeTruthy();
    const body = JSON.parse(String(post![1]?.body));
    expect(body.template_id).toBe(2);
    expect(body.params).toMatchObject({ group_by: 'city', agg: 'sum' });
  });

  // top_n: invalid N blocks generate and shows inline hint
  await userEvent.click(screen.getByLabelText(/TOP N/));
  const nInput = screen.getByLabelText('N（1-100）');
  await userEvent.clear(nInput);
  await userEvent.type(nInput, '0');
  expect(
    screen.getByRole('button', { name: '生成报表' }),
  ).toBeDisabled();
  expect(screen.getByText('N 必须在 1-100 之间')).toBeInTheDocument();
});
