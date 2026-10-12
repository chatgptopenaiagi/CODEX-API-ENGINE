'use strict';
const { parentPort, workerData } = require('node:worker_threads');
try {
  const native = require('./cae_native.node');
  parentPort.postMessage({ok: true, result: JSON.parse(native.request(workerData))});
} catch (error) {
  parentPort.postMessage({ok: false, code: error.message});
}
