'use strict';
const { Worker } = require('node:worker_threads');
const path = require('node:path');
const codes = new Set(['access_denied', 'invalid_protocol', 'invalid_configuration',
  'daily_request_limit', 'credential_operation_failed', 'credential_missing',
  'api_request_failed', 'unsupported_operation', 'audit_unavailable', 'broker_unavailable',
  'broker_request_failed']);
class CAEError extends Error {
  constructor(code) { super(codes.has(code) ? code : 'broker_unavailable'); this.code = this.message; }
}
class CAEClient {
  #connection; #timeout; #active = 0;
  constructor(connection = process.env.CAE_CONNECTION_FILE, { timeout = 35000 } = {}) {
    if (typeof connection !== 'string' || !connection || !Number.isInteger(timeout) ||
        timeout < 1 || timeout > 120000) throw new CAEError('invalid_configuration');
    this.#connection = path.resolve(connection);
    this.#timeout = timeout;
  }
  async request(operation, args = {}) {
    if (typeof operation !== 'string' || operation.length > 32 || !args ||
        typeof args !== 'object' || Array.isArray(args)) throw new CAEError('invalid_protocol');
    let input;
    try {
      input = JSON.stringify({ connection: this.#connection, timeout: this.#timeout, operation, args });
      if (Buffer.byteLength(JSON.stringify({v:1, id:'0'.repeat(32), op:operation, args})) > 65536)
        throw new Error();
    } catch { throw new CAEError('invalid_protocol'); }
    if (this.#active >= 8) throw new CAEError('broker_unavailable');
    this.#active++;
    try {
      return await new Promise((resolve, reject) => {
        const worker = new Worker(path.join(__dirname, 'worker.js'), { workerData: input });
        worker.once('message', value => value.ok ? resolve(value.result) : reject(new CAEError(value.code)));
        worker.once('error', () => reject(new CAEError('broker_unavailable')));
        worker.once('exit', code => { if (code !== 0) reject(new CAEError('broker_unavailable')); });
      });
    } finally { this.#active--; }
  }
  connect() { return this.request('status'); }
  health(provider = 'openai', profile = 'default') { return this.request('health', {provider, profile}); }
  models(provider = 'openai', profile = 'default') { return this.request('models', {provider, profile}); }
  capabilities(profile = 'default') { return this.request('providers', {profile}); }
  diagnostics(provider = 'openai', profile = 'default') { return this.request('diagnostics', {provider, profile}); }
}
module.exports = { CAEClient, CAEError };
