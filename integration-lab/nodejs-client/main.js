'use strict';
const { CAEClient, CAEError } = require('@cae/client');
const fs = require('node:fs');
const client = new CAEClient(undefined, {timeout: process.argv[2] === '--probe' ? 1000 : 35000});
const output = process.argv[2];
async function run() {
  if (output === '--probe') {
    try { await client.connect(); console.log('ok'); } catch (e) { console.log(e.code); }
    return;
  }
  while (!fs.existsSync(output + '.stop')) {
    try {
      const status = await client.connect();
      await client.health('lab');
      const models = await client.models('lab'), capabilities = await client.capabilities();
      let denied = false, malformed = false, restricted = false;
      try { await client.request('stop'); } catch (e) { denied = e.code === 'access_denied'; }
      try { await client.request('status', {app:'admin'}); } catch (e) { malformed = e.code === 'invalid_protocol'; }
      try { await client.request('chat', {provider:'lab', model:'lab-model', text:'test'}); }
      catch (e) { restricted = e.code === 'access_denied'; }
      fs.writeFileSync(output + '.new', JSON.stringify({status, models, capabilities, denied, malformed, restricted,
        client_pid: process.pid}));
      fs.renameSync(output + '.new', output);
    } catch (e) { if (!(e instanceof CAEError)) throw e; }
    await new Promise(resolve => setTimeout(resolve, 500));
  }
}
run().catch(() => { console.error('lab_client_failed'); process.exitCode = 1; });
