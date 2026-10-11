// Uses Node-API in Electron's trusted main process; no Node exposure to renderer.
const { app, BrowserWindow } = require('electron');
const fs = require('node:fs');
const path = require('node:path');
const report = process.argv[2];
// Explicit repository-local state for acceptance tests; no global Electron configuration.
if (process.env.CAE_LAB_DATA) {
  for (const name of ['userData', 'sessionData', 'crashDumps', 'logs']) {
    const directory = path.join(process.env.CAE_LAB_DATA, name);
    fs.mkdirSync(directory, {recursive:true});
    app.setPath(name, directory);
  }
}
app.whenReady().then(async () => {
  const { CAEClient } = require(process.env.CAE_CLIENT_PACKAGE || '@cae/client');
  const window = new BrowserWindow({show: !report,
    webPreferences:{nodeIntegration:false, contextIsolation:true, sandbox:true}});
  const client = new CAEClient();
  if (report) {
    while (!fs.existsSync(report + '.stop')) {
      try {
        const status = await client.connect();
        await client.health('lab');
        const models = await client.models('lab'), capabilities = await client.capabilities();
        let denied = false, malformed = false, restricted = false;
        try { await client.request('stop'); } catch (e) { denied = e.code === 'access_denied'; }
        try { await client.request('status', {app:'admin'}); } catch (e) { malformed = e.code === 'invalid_protocol'; }
        try { await client.request('chat', {provider:'lab', model:'lab-model', text:'test'}); }
        catch (e) { restricted = e.code === 'access_denied'; }
      let routing = null;
      if (process.env.CAE_LAB_ROUTING === '1') {
        routing = await client.request('route', {contract_version:1, capability:'chat_generation',
          model:'route-model', input:'synthetic', routing_mode:'LOCAL_ONLY'});
        await client.request('capabilities');
      }
        await window.loadURL('data:text/plain,' + encodeURIComponent(`CAE broker ${status.broker_pid}`));
        fs.writeFileSync(report + '.new', JSON.stringify({status, models, capabilities, routing, denied,
          malformed, restricted, client_pid:process.pid}));
        fs.renameSync(report + '.new', report);
      } catch (error) {
        fs.writeFileSync(report + '.error', error.code === 'broker_unavailable' ? error.code : 'client_failed');
        // Next read reconnects; no generation is replayed.
      }
      await new Promise(resolve => setTimeout(resolve, 500));
    }
    app.quit();
    return;
  }
  try {
    const status = await client.connect();
    const text = `CAE broker ${status.broker_pid}: ${status.broker}`;
    await window.loadURL('data:text/plain;charset=utf-8,' + encodeURIComponent(text));
  } catch { await window.loadURL('data:text/plain,CAE%20broker%20unavailable'); }
}).catch(error => {
  if (report) fs.writeFileSync(report + '.error',
    ['MODULE_NOT_FOUND', 'ERR_DLOPEN_FAILED'].includes(error.code) ? error.code : 'electron_start_failed');
  app.exit(1);
});
app.on('window-all-closed', () => app.quit());
