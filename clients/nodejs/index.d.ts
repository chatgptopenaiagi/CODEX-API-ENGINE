export type Result = Record<string, unknown>;
export class CAEError extends Error { readonly code: string; }
export class CAEClient {
  constructor(connection?: string, options?: { timeout?: number });
  request(operation: string, args?: Record<string, unknown>): Promise<Result>;
  connect(): Promise<Result>;
  health(provider?: string, profile?: string): Promise<Result>;
  models(provider?: string, profile?: string): Promise<Result>;
  capabilities(profile?: string): Promise<Result>;
  diagnostics(provider?: string, profile?: string): Promise<Result>;
}
