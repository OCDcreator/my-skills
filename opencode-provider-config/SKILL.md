---
name: opencode-provider-config
description: >
  Configure complete model parameters (context window, output tokens, capabilities, cost)
  for custom providers in OpenCode via cc-Switch. Use this skill whenever the user mentions
  configuring a new provider in OpenCode or cc-Switch, when a custom model lacks context
  window information, when the user asks about model limits/pricing/capabilities, or when
  they want to add/update provider models in opencode.json or cc-Switch. Also trigger when
  the user says things like "custom model has no context", "model parameters", "provider config",
  or wants to set up API providers like Zhipu GLM, DeepSeek, Kimi, OpenAI-compatible endpoints,
  or any custom LLM provider for use with OpenCode.
---

# OpenCode Provider Configuration via cc-Switch

A guide for configuring complete model parameters for custom providers in OpenCode,
managed through cc-Switch.

## Architecture Overview

cc-Switch manages OpenCode configuration through an additive model:

```
cc-Switch SQLite DB  -->  sync on switch  -->  opencode.json
(~/.cc-switch/cc-switch.db)                  (~/.config/opencode/opencode.json)
```

- cc-Switch stores provider configs in SQLite, then writes them to opencode.json
- OpenCode reads opencode.json at startup
- Directly editing opencode.json works temporarily, but cc-Switch may overwrite changes
  when the user switches/edits providers
- **The right approach**: modify the data source (cc-Switch DB), then let it sync

## Step 1: Find the Provider in cc-Switch Database

The database is at `~/.cc-switch/cc-switch.db` (SQLite).

```sql
SELECT id, name, app_type FROM providers
WHERE app_type = 'opencode';
```

Find the target provider and read its current `settings_config`:

```sql
SELECT settings_config FROM providers
WHERE id = '<provider-id>' AND app_type = 'opencode';
```

## Step 2: Determine Model Parameters

For each model, you need these parameters. The priority for finding accurate values:

1. **Official docs** (most accurate for pricing and limits)
2. **models.dev data** (good for limits, may have stale pricing)
3. **API response** (call `/v1/models` on the provider endpoint)

### Required Parameters

| Parameter | What it controls | Where to find |
|-----------|-----------------|---------------|
| `limit.context` | Max input tokens (context window) | Official docs, models.dev |
| `limit.output` | Max output tokens per response | Official docs, models.dev |
| `reasoning` | Model supports thinking/reasoning mode | Official docs |
| `attachment` | Model supports image/file input | Official docs |
| `toolcall` | Model supports function/tool calling | Official docs |
| `temperature` | Model supports temperature parameter | Almost always true |

### Optional Parameters

| Parameter | What it controls | When to use |
|-----------|-----------------|-------------|
| `cost.input` | Price per million input tokens (USD) | User wants cost display |
| `cost.output` | Price per million output tokens (USD) | User wants cost display |
| `cost.cache.read` | Price per million cached tokens (USD) | Provider supports prompt caching |
| `cost.cache.write` | Cache storage write price (USD) | Provider supports prompt caching |
| `interleaved` | Thinking content interleaved with response | Model uses `reasoning_content` field |
| `limit.input` | Explicit input limit (overrides context - output) | Rarely needed |
| `options` | Extra AI SDK parameters | Model-specific needs |
| `variants` | Model variants (thinking levels, etc.) | Model supports multiple modes |

**Important about cost**: OpenCode's internal convention is **USD per million tokens**.
If the official pricing is in another currency, convert to USD before writing.

**About `setCacheKey`**: This is an OpenAI-specific option that adds `promptCacheKey`
to API requests. It only works with OpenAI. Do NOT set this for other providers.
Most providers (Zhipu, DeepSeek, etc.) handle caching automatically on the server side.

### Interleaved Reasoning

Some models (like GLM-5, GLM-4.7) output thinking content in a separate field
(`reasoning_content`) interleaved with the main response. For these models:

```json
"interleaved": { "field": "reasoning_content" }
```

Check the model's API documentation or test its response format to determine this.

### Cost Lookup Process

1. Find the official pricing page for the provider
2. Note the unit (usually per million tokens, may be in local currency)
3. Convert to USD if needed
4. Look for tiered pricing (input length ranges, output length ranges)
5. Use the base tier (shortest input range) as the default

For models on subscription plans (like Coding Plans), cost is for reference only.
The user may still want it displayed to see token value.

## Step 3: Write the Updated Config

Build the complete `settings_config` JSON with all parameters, then update the database:

```sql
UPDATE providers
SET settings_config = '<complete-json-config>'
WHERE id = '<provider-id>' AND app_type = 'opencode';
```

### Config Structure

```json
{
  "npm": "@ai-sdk/openai-compatible",
  "options": {
    "baseURL": "https://api.example.com/v1",
    "apiKey": "sk-..."
  },
  "models": {
    "model-id": {
      "name": "Display Name",
      "reasoning": true,
      "temperature": true,
      "toolcall": true,
      "attachment": false,
      "interleaved": { "field": "reasoning_content" },
      "cost": {
        "input": 0.5,
        "output": 1.5,
        "cache": { "read": 0.1, "write": 0 }
      },
      "limit": {
        "context": 128000,
        "output": 65536
      }
    }
  }
}
```

## Step 4: Sync to opencode.json

After updating the database, the user needs to trigger cc-Switch to sync:

1. **Restart cc-Switch** (or the Tauri app)
2. **Or**: toggle the provider (disable then re-enable)
3. **Or**: switch to another provider and back

cc-Switch will read the updated `settings_config` from the database and write it
to `~/.config/opencode/opencode.json`.

## Step 5: Verify

Check that opencode.json has the correct data:

```bash
cat ~/.config/opencode/opencode.json | python3 -m json.tool
```

The target provider's models should now have `limit`, `cost`, and capability fields.

## Common Provider Reference

See `references/providers.md` for pre-collected parameters for common providers
(Zhipu GLM, DeepSeek, Kimi, etc.). This reference is loaded on demand when
configuring these providers.

## Preset Source Code (Advanced)

cc-Switch also has preset configurations in its source code at:
`src/config/opencodeProviderPresets.ts`

Modifying presets affects all new provider instances created from that preset.
This is useful for contributing upstream or for custom cc-Switch builds.
For a single user's provider, modifying the database is simpler and more direct.

The preset file has two relevant structures:
- `opencodeProviderPresets[]` - Provider presets with models, baseURL, templates
- `OPENCODE_PRESET_MODEL_VARIANTS[]` - Per-npm-package model metadata (context/output limits)

Both should be kept in sync when adding new models or providers.
