using Cae;
using System.Text.Json;

try {
    if (args.Length == 1 && args[0] == "--probe") {
        try { await new CaeClient(timeoutMilliseconds: 1000).ConnectAsync(); Console.WriteLine("ok"); }
        catch (CaeException e) { Console.WriteLine(e.Code); }
        return 0;
    }
    var client = new CaeClient();
    if (args.Length == 1 && args[0] == "stop") {
        Console.WriteLine((await client.RequestAsync("stop")).GetRawText());
        return 0;
    }
    var output = args[0];
    while (!File.Exists(output + ".stop")) {
        try {
            var status = await client.ConnectAsync();
            await client.HealthAsync("lab");
            var models = await client.ModelsAsync("lab");
            var capabilities = await client.CapabilitiesAsync();
            var denied = false;
            try { await client.RequestAsync("stop"); }
            catch (CaeException ex) when (ex.Code == "access_denied") { denied = true; }
            var malformed = false;
            try { await client.RequestAsync("status", new { app = "admin" }); }
            catch (CaeException ex) when (ex.Code == "invalid_protocol") { malformed = true; }
            var restricted = false;
            try { await client.RequestAsync("chat", new { provider = "lab", model = "lab-model", text = "test" }); }
            catch (CaeException ex) when (ex.Code == "access_denied") { restricted = true; }
            var result = JsonSerializer.Serialize(new { status, models, capabilities, denied, malformed, restricted,
                client_pid = Environment.ProcessId });
            File.WriteAllText(output + ".new", result);
            File.Move(output + ".new", output, true);
        } catch (CaeException) { /* A later independent read reconnects after broker restart. */ }
        catch (IOException) { /* Report reader may briefly block replacement on Windows. */ }
        await Task.Delay(500);
    }
    return 0;
} catch { Console.Error.WriteLine("lab_client_failed"); return 1; }
