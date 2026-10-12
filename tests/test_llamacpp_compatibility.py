import json

import pytest

from cae.errors import ConfigurationError
from cae.policy import Rule
from cae.providers import HTTPProvider, ProviderConfig
from cae.routing import CapabilityRequest, RoutingError, validated_result

MODEL = r"I:\LocalAI\models\Qwen3-4B-Q4_K_M\Qwen3-4B-Q4_K_M.gguf"


class Transport:
    def __init__(self, content):
        self.content = content

    def send(self, config, method, path, headers, payload):
        assert path == "/v1/chat/completions"
        assert payload["model"] == MODEL
        assert not headers
        return 200, json.dumps({"model": MODEL, "choices": [{
            "message": {"role": "assistant", "content": self.content,
                        "reasoning_content": "PRIVATE_REASONING_CANARY"},
            "finish_reason": "stop" if self.content else "length"}],
            "usage": {"prompt_tokens": 20, "completion_tokens": 116}}).encode()


def test_exact_opaque_windows_model_and_reasoning_exclusion():
    spec = ProviderConfig("llamacpp", "vllm", endpoint="http://127.0.0.1:8080",
                          authenticated=False, routing_models=(MODEL,))
    rule = Rule("local", "test", "llamacpp", "default", frozenset({"chat"}),
                models=frozenset({MODEL}))
    assert rule.matches("test", "llamacpp", "default", "chat", MODEL)
    assert not rule.matches("test", "llamacpp", "default", "chat", MODEL.lower())
    request = CapabilityRequest.parse({"contract_version": 1, "capability": "chat_generation",
        "model": MODEL, "input": "synthetic", "routing_mode": "LOCAL_ONLY"})
    raw = HTTPProvider(spec, Transport("Final answer")).request("chat", "", request.model, "synthetic")
    result, usage = validated_result("chat_generation", raw)
    assert result == {"text": "Final answer"}
    assert usage["input_tokens"] == 20 and usage["output_tokens"] == 116
    assert "reasoning" not in json.dumps(raw)
    assert "PRIVATE_REASONING_CANARY" not in json.dumps(raw)


def test_nonzero_tokens_and_reasoning_do_not_make_empty_content_usable():
    spec = ProviderConfig("llamacpp", "vllm", authenticated=False)
    raw = HTTPProvider(spec, Transport("")).request("chat", "", MODEL, "synthetic", 32)
    with pytest.raises(RoutingError, match="provider_response_invalid"):
        validated_result("chat_generation", raw)


@pytest.mark.parametrize("model", [MODEL + "\n", "\\\\server\\share", "a" * 129, "I:\\bad\x00model"])
def test_model_identifiers_remain_bounded(model):
    with pytest.raises(ConfigurationError):
        ProviderConfig("local", "vllm", authenticated=False, routing_models=(model,))
