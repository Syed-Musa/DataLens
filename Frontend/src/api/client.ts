const BASE = import.meta.env.VITE_API_URL || '/api';

async function request<T>(
  path: string,
  init?: RequestInit & { json?: unknown }
): Promise<T> {
  const { json, ...opts } = init ?? {};
  const headers: Record<string, string> = {
    ...(opts.headers as Record<string, string>),
  };
  if (json !== undefined) {
    headers['Content-Type'] = 'application/json';
  }
  const res = await fetch(`${BASE}${path}`, {
    ...opts,
    headers,
    body: json !== undefined ? JSON.stringify(json) : opts.body,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = err.detail ?? err.message;
    const message = Array.isArray(detail)
      ? detail.map((d: { msg?: string }) => d.msg ?? JSON.stringify(d)).join('; ')
      : typeof detail === 'string'
        ? detail
        : String(res.status);
    throw new Error(message || res.statusText);
  }
  return res.json();
}

export const api = {
  connectionStatus: () =>
    request<{ connected: boolean }>('/connection-status'),

  connectDb: (connectionString: string) =>
    request<{ success: boolean; message: string; tables_count?: number }>(
      '/connect-db',
      { method: 'POST', json: { connection_string: connectionString } }
    ),

  getTables: () =>
    request<Array<{ schema: string; name: string; full_name: string }>>('/tables'),

  getTable: (name: string) =>
    request<{
      table: string;
      schema: string;
      full_name: string;
      columns: Array<{ name: string; type: string; nullable: boolean; default?: string }>;
      primary_keys: string[];
      foreign_keys: Array<{
        columns: string[];
        referred_table: string;
        referred_schema: string;
        referred_columns: string[];
      }>;
      constraints: Array<{ type: string; name?: string; columns?: string[]; sqltext?: string }>;
      ai_description?: string;
    }>(`/tables/${encodeURIComponent(name)}`),

  getTableRelationships: (name: string) =>
    request<{
      table: string;
      outgoing_relationships: Array<{
        type: string;
        related_table: string;
        column_mapping: Record<string, string>;
        description: string;
      }>;
      incoming_relationships: Array<{
        type: string;
        related_table: string;
        column_mapping: Record<string, string>;
        description: string;
      }>;
    }>(`/inspector/${encodeURIComponent(name)}/relationships`),

  getTableDq: (name: string, refresh?: boolean) =>
    request<{
      table: string;
      schema: string;
      row_count: number;
      pk_duplicate_pct?: number;
      columns: Array<{
        column: string;
        row_count: number;
        null_count: number;
        null_pct: number;
        distinct_count: number;
        distinct_pct: number;
        min?: unknown;
        max?: unknown;
        mean?: number;
        median?: number;
        freshness?: string;
        duplicate_pct?: number | null;
      }>;
    }>(`/tables/${encodeURIComponent(name)}/dq${refresh ? '?refresh=true' : ''}`),

  chat: (message: string, history: Array<{ role: string; content: string }> = []) =>
    request<{ response: string; sql_suggestion?: string; relevant_tables?: string[] }>(
      '/chat',
      { method: 'POST', json: { message, history } }
    ),

  generateDocs: (tableNames?: string[]) =>
    request<{ success: boolean; message: string; tables_processed: number; artifacts?: string[] }>(
      '/generate-docs',
      { method: 'POST', json: { table_names: tableNames ?? null } }
    ),

  listArtifacts: () => request<{ artifacts: string[] }>('/artifacts'),
  
  getArtifactUrl: (filename: string) => `${BASE}/artifacts/${filename}`,

  generateSql: (prompt: string) =>
    request<{ sql?: string; explanation?: string }>('/generate-sql', {
      method: 'POST',
      json: { prompt },
    }),

  lineage: () =>
    request<{ nodes: Array<{ id: string; label: string; type: string; columns: string[]; primary_keys: string[] }>; edges: Array<{ source: string; target: string; type: string; columns: string[]; referred_columns: string[] }> }>(
      '/lineage'
    ),
};
