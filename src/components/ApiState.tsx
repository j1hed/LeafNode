import type { Resource } from '../app/DashboardContext';
import { display } from '../services/data';

export function ResourceState({ resource, empty, message = 'No data available yet.' }: { resource: Resource<unknown>; empty?: boolean; message?: string }) {
  if (resource.loading) return <p className="api-state" role="status">Loading…</p>;
  if (resource.error) return <p className="api-state api-error" role="alert">{resource.error}</p>;
  if (empty) return <p className="api-state" role="status">{message}</p>;
  return null;
}
export function JsonData({ value }: { value: unknown }) {
  return <pre className="api-json">{typeof value === 'object' && value !== null ? JSON.stringify(value, null, 2) : display(value)}</pre>;
}
