import { isRecord, type ApiRecord } from './api';

export const display = (value: unknown): string => value === null || value === undefined ? 'Unavailable' : typeof value === 'string' ? value : JSON.stringify(value);
export const reading = (value: unknown): number | null => typeof value === 'number' && Number.isFinite(value) ? value : null;

// History row fields are not specified by the supplied API contract. Plot only
// recognized numeric fields; retain every original row in the history view.
export function series(rows: unknown[], field: string) {
  return rows.flatMap(row => {
    if (!isRecord(row)) return [];
    const source = isRecord(row.esp32) ? row.esp32 : row;
    const value = reading(source[field]);
    return value === null ? [] : [{ value, label: typeof row.timestamp === 'string' ? row.timestamp : '' }];
  }).sort((a, b) => {
    const first = Date.parse(a.label), second = Date.parse(b.label);
    return Number.isFinite(first) && Number.isFinite(second) ? first - second : 0;
  });
}

// Resolve only local OpenAPI references. Never guess hardware device aliases.
export function manualOptions(schema: ApiRecord | null): { devices: string[]; actions: string[] } {
  if (!schema) return { devices: [], actions: [] };
  function resolve(value: unknown, seen = new Set<string>()): ApiRecord {
    if (!isRecord(value)) return {};
    if (typeof value.$ref === 'string') {
      if (!value.$ref.startsWith('#/') || seen.has(value.$ref)) return {};
      const next = new Set(seen).add(value.$ref);
      const target = value.$ref.slice(2).split('/').reduce<unknown>((node, key) => isRecord(node) ? node[key.replaceAll('~1', '/').replaceAll('~0', '~')] : undefined, schema);
      return resolve(target, next);
    }
    if (Array.isArray(value.allOf)) return value.allOf.reduce<ApiRecord>((result, part) => {
      const item = resolve(part, seen);
      return { ...result, ...item, properties: { ...(isRecord(result.properties) ? result.properties : {}), ...(isRecord(item.properties) ? item.properties : {}) } };
    }, value);
    return value;
  }
  function enums(value: unknown): string[] {
    const item = resolve(value);
    if (Array.isArray(item.enum)) return item.enum.filter((v): v is string => typeof v === 'string');
    if (typeof item.const === 'string') return [item.const];
    const variants = item.anyOf ?? item.oneOf;
    return Array.isArray(variants) ? [...new Set(variants.flatMap(enums))] : [];
  }
  const paths = resolve(schema.paths);
  const operation = resolve(resolve(paths['/api/commands/manual']).post);
  const content = resolve(resolve(operation.requestBody).content);
  const body = resolve(resolve(content['application/json']).schema);
  const properties = resolve(body.properties);
  return { devices: enums(properties.device), actions: enums(properties.action) };
}
