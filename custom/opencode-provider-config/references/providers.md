# Common Provider Model Parameters

Pre-collected model parameters for popular providers. Values sourced from official docs and models.dev.
Cost is in **USD per million tokens** (converted from local currency where applicable).

## Table of Contents

- [Zhipu GLM](#zhipu-glm)
- [DeepSeek](#deepseek)
- [Kimi / Moonshot](#kimi--moonshot)
- [StepFun](#stepfun)
- [MiniMax](#minimax)
- [OpenAI](#openai)
- [Anthropic (Claude)](#anthropic-claude)
- [Google (Gemini)](#google-gemini)

---

## Zhipu GLM

**API Docs**: https://docs.bigmodel.cn
**Pricing**: https://bigmodel.cn/pricing
**Currency**: CNY, converted at ~7.2 RMB/USD

### Standard API (`https://open.bigmodel.cn/api/paas/v4`)

| Model | Context | Output | Reasoning | Attachment | Interleaved | input $/M | output $/M | cache_read $/M |
|-------|---------|--------|-----------|------------|-------------|-----------|------------|----------------|
| GLM-5.1 | 204,800 | 131,072 | true | false | - | 0.83 | 3.33 | 0.18 |
| GLM-5-Turbo | 200,000 | 128,000 | true | false | `{field: "reasoning_content"}` | 0.69 | 3.06 | 0.17 |
| GLM-5 | 202,752 | 131,072 | true | false | `{field: "reasoning_content"}` | 0.56 | 2.50 | 0.14 |
| GLM-4.7 | 202,752 | 131,072 | true | false | `{field: "reasoning_content"}` | 0.28 | 1.11 | 0.06 |
| GLM-4.6V | 128,000 | 128,000 | false | true | - | 0.14 | 0.42 | 0.03 |
| GLM-4.6 | 202,752 | 131,072 | true | false | - | 0.28 | 1.11 | 0.06 |
| GLM-4.5 | 128,000 | 98,304 | true | false | - | 0.21 | 1.39 | 0.04 |
| GLM-4.5-Air | 128,000 | 98,304 | true | false | - | 0.11 | 0.28 | 0.02 |
| GLM-4.7-Flash | 200,000 | 131,072 | true | false | - | 0 | 0 | 0 |

### Coding Plan API (`https://open.bigmodel.cn/api/coding/paas/v4`)

Same models and parameters as standard API. Subscription-based, cost is for reference only.

### English API (`https://api.z.ai/v1`)

Same models. Pricing in USD natively (check https://z.ai for current rates).

---

## DeepSeek

**API Docs**: https://platform.deepseek.com
**Pricing**: https://platform.deepseek.com/pricing

| Model | Context | Output | Reasoning | Attachment | input $/M | output $/M | cache_read $/M |
|-------|---------|--------|-----------|------------|-----------|------------|----------------|
| DeepSeek V3.2 | 163,840 | 65,536 | true | false | 0.27 | 1.10 | 0.07 |
| DeepSeek R1 | 131,072 | 131,072 | true | false | 0.55 | 2.19 | 0.14 |

---

## Kimi / Moonshot

**API Docs**: https://platform.moonshot.cn
**Pricing**: https://platform.moonshot.cn/pricing

| Model | Context | Output | Reasoning | Attachment | input $/M | output $/M |
|-------|---------|--------|-----------|------------|-----------|------------|
| Kimi K2.5 | 262,144 | 262,144 | true | true (image, video) | varies | varies |

Note: Kimi K2.5 supports image and video input. Check current pricing as it changes frequently.

### Kimi For Coding API (`https://api.kimi.com/coding/v1`)

Uses Anthropic-compatible format (`@ai-sdk/anthropic`). Same model capabilities.

---

## StepFun

**API Docs**: https://platform.stepfun.ai
**Pricing**: https://platform.stepfun.ai/pricing

| Model | Context | Output | Reasoning | Attachment | input $/M | output $/M |
|-------|---------|--------|-----------|------------|-----------|------------|
| Step 3.5 Flash | 262,144 | 262,144 | true | false | varies | varies |

---

## MiniMax

**API Docs**: https://platform.minimaxi.com
**Pricing**: https://platform.minimaxi.com/pricing

| Model | Context | Output | Reasoning | Attachment | input $/M | output $/M |
|-------|---------|--------|-----------|------------|-----------|------------|
| MiniMax M2.7 | 204,800 | 131,072 | true | false | varies | varies |

---

## OpenAI

**API Docs**: https://platform.openai.com
**npm**: `@ai-sdk/openai` (Responses API) or `@ai-sdk/openai-compatible`

| Model | Context | Output | Reasoning | Attachment | input $/M | output $/M | cache_read $/M |
|-------|---------|--------|-----------|------------|-----------|------------|----------------|
| GPT-5.4 | 400,000 | 128,000 | true | true | varies | varies | varies |
| GPT-5.3 Codex | varies | varies | true | false | varies | varies | varies |

---

## Anthropic (Claude)

**npm**: `@ai-sdk/anthropic`

| Model | Context | Output | Reasoning | Attachment | input $/M | output $/M | cache_read $/M |
|-------|---------|--------|-----------|------------|-----------|------------|----------------|
| Claude Opus 4.6 | 1,000,000 | 128,000 | true | true | 15.00 | 75.00 | 1.50 |
| Claude Sonnet 4.6 | 1,000,000 | 64,000 | true | true | 3.00 | 15.00 | 0.30 |
| Claude Haiku 4.5 | 200,000 | 64,000 | true | true | 0.80 | 4.00 | 0.08 |

---

## Google (Gemini)

**npm**: `@ai-sdk/google`

| Model | Context | Output | Reasoning | Attachment | input $/M | output $/M |
|-------|---------|--------|-----------|------------|-----------|------------|
| Gemini 2.5 Flash Lite | 1,048,576 | 65,536 | true | true | varies | varies |
| Gemini 3 Flash Preview | 1,048,576 | 65,536 | true | true | varies | varies |
| Gemini 3 Pro Preview | 1,048,576 | 65,536 | true | true | varies | varies |

Gemini supports thinking levels via `thinkingConfig`.

---

## How to Add a New Provider

When adding a provider not listed here:

1. **Find the official API docs and pricing page**
2. **Check models.dev** - search for the model ID in the opencode fixtures:
   `packages/opencode/test/tool/fixtures/models-api.json`
3. **Test the API** - call `GET {baseURL}/v1/models` to see what the provider returns
4. **Convert pricing to USD** if listed in local currency
5. **Add to this reference file** so future configurations are faster
