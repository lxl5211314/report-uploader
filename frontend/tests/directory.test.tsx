import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import WorkspacePage from '../src/pages/WorkspacePage';

type Route = { status?: number; body?: unknown };

function stubFetch(routes: Record<string, Route>) {
  const mock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input.toString();
    const method = (init?.method ?? 'GET').toUpperCase();
    const key = Object.keys(routes)
      .sort((a, b) => b.length - a.length)
      .find((k) => {
        const parts = k.split(' ');
        if (parts.length === 2) {
          return parts[0] === method && url.includes(parts[1]);
        }
        return url.includes(k);
      });
    if (!key) throw new Error(`unmatched fetch: ${method} ${url}`);
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
      {
        id: 2,
        name: '归档',
        parent_id: null,
        children: [],
        files: [],
      },
    ],
  },
};

const baseRoutes: Record<string, Route> = {
  'GET /api/v1/templates': { body: { templates: [] } },
  'GET /api/v1/directories': treeRoute,
};

afterEach(() => {
  vi.unstubAllGlobals();
});

test('create directory form renders and submits', async () => {
  const mock = stubFetch({
    ...baseRoutes,
    'POST /api/v1/directories': {
      status: 201,
      body: { id: 9, name: '新目录', parent_id: null },
    },
  });

  render(<WorkspacePage />);
  await screen.findByText('销售');

  await userEvent.click(screen.getByRole('button', { name: '新建目录' }));
  expect(screen.getByLabelText('目录名称')).toBeInTheDocument();
  expect(screen.getByLabelText('上级目录')).toBeInTheDocument();

  await userEvent.type(screen.getByLabelText('目录名称'), '新目录');
  await userEvent.click(screen.getByRole('button', { name: '创建' }));

  await waitFor(() => {
    const postCall = mock.mock.calls.find(
      (c) => (c[1]?.method ?? 'GET') === 'POST',
    );
    expect(postCall).toBeTruthy();
    expect(String(postCall![0])).toContain('/api/v1/directories');
  });
  expect(screen.queryByLabelText('目录名称')).not.toBeInTheDocument();
});

test('create conflict error is surfaced to the user', async () => {
  stubFetch({
    ...baseRoutes,
    'POST /api/v1/directories': {
      status: 409,
      body: {
        code: 'DIRECTORY_NAME_CONFLICT',
        message: '同级已存在同名目录：销售',
      },
    },
  });

  render(<WorkspacePage />);
  await screen.findByText('销售');

  await userEvent.click(screen.getByRole('button', { name: '新建目录' }));
  await userEvent.type(screen.getByLabelText('目录名称'), '销售');
  await userEvent.click(screen.getByRole('button', { name: '创建' }));

  expect(await screen.findByRole('alert')).toHaveTextContent(
    '同级已存在同名目录：销售',
  );
});

test('dragging a file onto a directory calls the move API', async () => {
  const mock = stubFetch({
    ...baseRoutes,
    'POST /api/v1/files/10/move': {
      body: {
        id: 10,
        name: 'a.csv',
        format: 'csv',
        size_bytes: 2048,
        directory_id: 2,
        uploaded_at: '2026-01-01T00:00:00',
      },
    },
  });

  render(<WorkspacePage />);
  await screen.findByText('a.csv');

  const fileButton = screen.getByText('a.csv').closest('button')!;
  const archiveDir = Array.from(document.querySelectorAll('.dir-name'))
    .find((el) => el.textContent === '📁 归档')!
    .closest('[role="treeitem"]')!;

  const dt = {
    data: {} as Record<string, string>,
    setData(key: string, value: string) {
      this.data[key] = value;
    },
    getData(key: string) {
      return this.data[key] ?? '';
    },
    types: [] as string[],
    effectAllowed: 'move',
    dropEffect: 'none',
  };

  fireEvent.dragStart(fileButton, { dataTransfer: dt });
  fireEvent.drop(archiveDir, { dataTransfer: dt });

  await waitFor(() => {
    const moveCall = mock.mock.calls.find(
      (c) => String(c[0]).includes('/api/v1/files/10/move'),
    );
    expect(moveCall).toBeTruthy();
    expect(moveCall![1]?.method).toBe('POST');
  });
});

test('move-menu fallback is present and triggers move', async () => {
  const mock = stubFetch({
    ...baseRoutes,
    'POST /api/v1/files/10/move': {
      body: {
        id: 10,
        name: 'a.csv',
        format: 'csv',
        size_bytes: 2048,
        directory_id: 2,
        uploaded_at: '2026-01-01T00:00:00',
      },
    },
  });

  render(<WorkspacePage />);
  await screen.findByText('a.csv');

  const menu = screen.getByLabelText('移动 a.csv 到');
  await userEvent.selectOptions(menu, '2');

  await waitFor(() => {
    const moveCall = mock.mock.calls.find(
      (c) => String(c[0]).includes('/api/v1/files/10/move'),
    );
    expect(moveCall).toBeTruthy();
  });
});

test('move conflict error surfaces in global banner', async () => {
  stubFetch({
    ...baseRoutes,
    'POST /api/v1/files/10/move': {
      status: 409,
      body: {
        code: 'FILE_NAME_CONFLICT',
        message: '目标目录中已存在同名文件：a.csv',
      },
    },
  });

  render(<WorkspacePage />);
  await screen.findByText('a.csv');

  const menu = screen.getByLabelText('移动 a.csv 到');
  await userEvent.selectOptions(menu, '2');

  expect(await screen.findByRole('alert')).toHaveTextContent(
    '目标目录中已存在同名文件：a.csv',
  );
});
