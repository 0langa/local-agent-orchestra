# Live AI Testing Matrix

Use this after configuring providers through `agentheim provider ...`. Do not rely on AI provider `.env` values; runtime provider config must come from provider profiles and vault/keychain secrets.

## Provider Profile Setup

- [ ] `agentheim provider templates` lists all supported templates.
- [ ] `agentheim provider add openai --template openai_v1 --model <model> --role planner` stores secret securely.
- [ ] `agentheim provider add ollama --template ollama --model <model> --role executor` works with `auth=none`.
- [ ] `agentheim provider assign verifier --provider <provider> --model <model>` changes role binding.
- [ ] `agentheim provider list` shows provider/profile state without raw secrets.
- [ ] `agentheim provider use <profile>` switches default profile.
- [ ] `agentheim provider use <profile> --project` writes `.ai-team/provider-profile.json`.
- [ ] `agentheim provider rotate-secret <provider>` replaces a vault/keychain secret.
- [ ] `agentheim provider import-env` migrates old env setup once, then runtime ignores old provider env vars.
- [ ] `agentheim config-dump --redacted` never prints raw key material.
- [ ] `agentheim doctor --skip-connectivity` reports provider profile status.
- [ ] `agentheim ping-models` pings every configured role.

## Provider Text Smoke

- [ ] `openai_v1`
- [ ] `openai_compatible`
- [ ] `azure_foundry`
- [ ] `aws_bedrock` with `aws_chain`
- [ ] `aws_bedrock` with `bedrock_api_key`
- [ ] `oci_genai`
- [ ] `xai_grok`
- [ ] `gemini`
- [ ] `vertex_ai`
- [ ] `anthropic`
- [ ] `kimi_moonshot`
- [ ] `mistral`
- [ ] `groq`
- [ ] `deepseek`
- [ ] `openrouter`
- [ ] `together`
- [ ] `cohere`
- [ ] `perplexity`
- [ ] `ollama`
- [ ] `ollama_cloud`
- [ ] `lm_studio`

## Role Routing

- [ ] `planner` bound to provider A works.
- [ ] `executor` bound to provider B works.
- [ ] `verifier` bound to provider C works.
- [ ] `context` binding exists and AICtx live mode uses it when configured.
- [ ] Mixed-provider profile runs one workflow end to end.

## Vision Smoke

Use only models declared with `vision` capability.

- [ ] Azure vision deployment.
- [ ] Bedrock vision model.
- [ ] Gemini vision model.
- [ ] Anthropic vision model.
- [ ] Kimi/Moonshot vision-capable model.
- [ ] Ollama/LM Studio local vision model if installed.

## API / Web

- [ ] `GET /api/providers`
- [ ] `GET /api/providers/templates`
- [ ] `POST /api/providers`
- [ ] `POST /api/providers/assign`
- [ ] Web UI Provider Center lists configured profiles/providers.
- [ ] API/Web responses never expose raw secrets.
