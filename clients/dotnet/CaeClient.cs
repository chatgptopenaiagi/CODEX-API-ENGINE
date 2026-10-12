using System.Buffers.Binary;
using System.IO.Pipes;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.Win32.SafeHandles;

namespace Cae;

public sealed class CaeException : Exception
{
    public string Code { get; }
    internal CaeException(string code) : base(code) { Code = code; }
}

/// <summary>One authenticated connection per request; no automatic request replay.</summary>
public sealed class CaeClient
{
    private readonly string pipe, image, sha256;
    private readonly int timeout;
    private static readonly HashSet<string> Codes = new(StringComparer.Ordinal) {
        "access_denied", "invalid_protocol", "invalid_configuration", "daily_request_limit",
        "credential_operation_failed", "credential_missing", "api_request_failed",
        "unsupported_operation", "audit_unavailable", "broker_unavailable"
    };

    public CaeClient(string? connectionFile = null, int timeoutMilliseconds = 35000)
    {
        try {
            if (timeoutMilliseconds is < 1 or > 120000) throw new CaeException("invalid_configuration");
            timeout = timeoutMilliseconds;
            var file = new FileInfo(connectionFile ?? Environment.GetEnvironmentVariable("CAE_CONNECTION_FILE")
                ?? throw new CaeException("invalid_configuration"));
            if (file.Length > 65536 || file.LinkTarget != null) throw new CaeException("invalid_configuration");
            using var config = Parse(File.ReadAllBytes(file.FullName));
            var root = config.RootElement;
            ExactKeys(root, "pipe", "server_image", "server_sha256");
            pipe = root.GetProperty("pipe").GetString()!;
            image = root.GetProperty("server_image").GetString()!;
            sha256 = root.GetProperty("server_sha256").GetString()!;
            if (!Regex.IsMatch(pipe, @"\Acae-[a-z0-9][a-z0-9-]{0,63}\z") ||
                !Path.IsPathFullyQualified(image) || !Regex.IsMatch(sha256, @"\A[a-f0-9]{64}\z"))
                throw new CaeException("invalid_configuration");
            image = Path.GetFullPath(image);
        } catch { throw new CaeException("invalid_configuration"); }
    }

    private static void ExactKeys(JsonElement value, params string[] keys)
    {
        if (value.ValueKind != JsonValueKind.Object ||
            !value.EnumerateObject().Select(x => x.Name).ToHashSet().SetEquals(keys))
            throw new CaeException("invalid_protocol");
    }

    private static JsonDocument Parse(byte[] bytes)
    {
        var doc = JsonDocument.Parse(bytes, new JsonDocumentOptions { MaxDepth = 64 });
        try { Validate(doc.RootElement); return doc; }
        catch { doc.Dispose(); throw; }
    }

    private static void Validate(JsonElement value)
    {
        if (value.ValueKind == JsonValueKind.Object) {
            var names = new HashSet<string>(StringComparer.Ordinal);
            foreach (var property in value.EnumerateObject()) {
                if (!names.Add(property.Name)) throw new CaeException("invalid_protocol");
                Validate(property.Value);
            }
        } else if (value.ValueKind == JsonValueKind.Array) {
            foreach (var item in value.EnumerateArray()) Validate(item);
        }
    }

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool GetNamedPipeServerProcessId(SafePipeHandle pipe, out uint pid);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern SafeProcessHandle OpenProcess(uint access, bool inherit, uint pid);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern bool QueryFullProcessImageName(SafeProcessHandle process, uint flags,
        StringBuilder name, ref uint size);
    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern bool OpenProcessToken(SafeProcessHandle process, uint access,
        out SafeAccessTokenHandle token);

    private uint Authenticate(NamedPipeClientStream stream)
    {
        if (!GetNamedPipeServerProcessId(stream.SafePipeHandle, out var pid))
            throw new CaeException("broker_unavailable");
        using var process = OpenProcess(0x1000, false, pid);
        uint size = 32768;
        var name = new StringBuilder((int)size);
        if (process.IsInvalid || !QueryFullProcessImageName(process, 0, name, ref size) ||
            !OpenProcessToken(process, 8, out var token)) throw new CaeException("broker_unavailable");
        using (token)
        using (var identity = new WindowsIdentity(token.DangerousGetHandle()))
        using (var self = WindowsIdentity.GetCurrent()) {
            if (identity.User != self.User || !String.Equals(Path.GetFullPath(name.ToString()), image,
                    StringComparison.OrdinalIgnoreCase)) throw new CaeException("broker_unavailable");
        }
        using var executable = File.OpenRead(image);
        if (executable.Length > 268435456 ||
            !Convert.ToHexString(SHA256.HashData(executable)).Equals(sha256, StringComparison.OrdinalIgnoreCase))
            throw new CaeException("broker_unavailable");
        return pid;
    }

    private static async Task Send(NamedPipeClientStream stream, byte[] body, CancellationToken token)
    {
        if (body.Length is < 1 or > 65536) throw new CaeException("invalid_protocol");
        var prefix = new byte[4];
        BinaryPrimitives.WriteInt32LittleEndian(prefix, body.Length);
        await stream.WriteAsync(prefix, token).ConfigureAwait(false);
        await stream.WriteAsync(body, token).ConfigureAwait(false);
    }

    public async Task<JsonElement> RequestAsync(string operation, object? arguments = null,
        CancellationToken cancellationToken = default)
    {
        try {
            var id = Guid.NewGuid().ToString("N");
            var body = JsonSerializer.SerializeToUtf8Bytes(new { v = 1, id, op = operation,
                args = arguments ?? new Dictionary<string, object>() });
            if (body.Length > 65536 || operation.Length > 32) throw new CaeException("invalid_protocol");
            using var deadline = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            deadline.CancelAfter(timeout);
            var token = deadline.Token;
            using var stream = new NamedPipeClientStream(".", pipe, PipeDirection.InOut,
                PipeOptions.Asynchronous, TokenImpersonationLevel.Identification);
            await stream.ConnectAsync(Math.Min(timeout, 3000), token).ConfigureAwait(false);
            var pid = Authenticate(stream);
            await Send(stream, body, token).ConfigureAwait(false);
            var prefix = new byte[4];
            await stream.ReadExactlyAsync(prefix, token).ConfigureAwait(false);
            var count = BinaryPrimitives.ReadInt32LittleEndian(prefix);
            if (count is < 1 or > 65536) throw new CaeException("invalid_protocol");
            var bytes = new byte[count];
            await stream.ReadExactlyAsync(bytes, token).ConfigureAwait(false);
            using var doc = Parse(bytes);
            await Send(stream, "OK"u8.ToArray(), token).ConfigureAwait(false);
            var root = doc.RootElement;
            ExactKeys(root, "v", "id", "ok", "result", "error", "broker_pid");
            if (root.GetProperty("v").GetInt32() != 1 || root.GetProperty("id").GetString() != id ||
                root.GetProperty("broker_pid").GetUInt32() != pid ||
                root.GetProperty("result").ValueKind != JsonValueKind.Object)
                throw new CaeException("invalid_protocol");
            if (!root.GetProperty("ok").GetBoolean()) {
                var code = root.GetProperty("error").GetString() ?? "";
                throw new CaeException(Codes.Contains(code) ? code : "broker_request_failed");
            }
            if (root.GetProperty("error").ValueKind != JsonValueKind.Null)
                throw new CaeException("invalid_protocol");
            return root.GetProperty("result").Clone();
        } catch (CaeException) { throw; }
          catch (JsonException) { throw new CaeException("invalid_protocol"); }
          catch (InvalidOperationException) { throw new CaeException("invalid_protocol"); }
          catch { throw new CaeException("broker_unavailable"); }
    }

    public Task<JsonElement> ConnectAsync() => RequestAsync("status");
    public Task<JsonElement> HealthAsync(string provider = "openai", string profile = "default") =>
        RequestAsync("health", new { provider, profile });
    public Task<JsonElement> ModelsAsync(string provider = "openai", string profile = "default") =>
        RequestAsync("models", new { provider, profile });
    public Task<JsonElement> CapabilitiesAsync(string profile = "default") =>
        RequestAsync("providers", new { profile });
    public Task<JsonElement> DiagnosticsAsync(string provider = "openai", string profile = "default") =>
        RequestAsync("diagnostics", new { provider, profile });
}
