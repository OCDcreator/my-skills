---
name: design-reference-router
description: Use when the user wants a page or UI to follow a real product or brand style, mentions DESIGN.md, getdesign.md, or awesome-design-md, or asks for a non-generic design that should start from concrete reference sites before implementation.
---

# Design Reference Router

Use this skill to pick strong visual references before implementation. This skill does not build the UI itself. It turns style-seeking requests into a concrete reference set and then hands implementation to `frontend-design`.

## When To Use

Use this skill when the user asks for things like:

- "做成 Vercel / Claude / Stripe / Airbnb 那种风格"
- "参考真实产品官网来设计"
- "不要 AI 味，要像成熟产品页面"
- "use DESIGN.md"
- "use getdesign.md"
- "use awesome-design-md"

Do not use this skill for generic frontend requests that already have a clear visual system.

## Important Boundary

- `external/awesome-design-md/` is a reference source, not a skill source
- The local files under that directory are only brand/slug markers and outbound links
- For deeper style details, fetch `https://getdesign.md/<slug>/design-md` on demand
- After choosing references and summarizing constraints, load `frontend-design` to implement the UI

## Workflow

1. Identify the style goal from the user request
2. Pick 1-3 matching references from `external/awesome-design-md/`
3. If local names are not enough, read `https://getdesign.md/<slug>/design-md`
4. Summarize the references into an actionable design brief
5. Explicitly load `frontend-design` next

Do not skip the reference-selection step when the user asks for a specific brand feel.

## Style Goal Mapping

| Style goal | Recommended references | Why |
|---|---|---|
| Developer platform | `vercel`, `warp`, `cursor`, `opencode.ai` | Monochrome precision, terminal-native feel, tool-centric layouts |
| Dark AI product | `claude`, `voltagent`, `mistral.ai`, `runwayml` | Strong dark surfaces, premium AI-product tone, focused glow accents |
| Luxury minimal marketing | `apple`, `tesla`, `ferrari` | Sparse layouts, image-led rhythm, restrained but high-end surfaces |
| Fintech trust | `stripe`, `wise`, `coinbase`, `revolut` | Strong trust signals, crisp hierarchy, polished product storytelling |
| Friendly SaaS | `airbnb`, `notion`, `intercom`, `zapier` | Softer tone, approachable UI, lighter editorial/product balance |

## Reference Selection Rules

- Prefer 1 primary reference and at most 2 supporting references
- If the user names a brand directly, keep that as the primary reference unless it clearly conflicts with the product type
- If multiple brands fit, explain the difference in one sentence each
- Do not dump a long list of brands without a recommendation

## Reading Local References

Start by checking the local reference index under `external/awesome-design-md/`.

Use the directory names as slugs, for example:

- `external/awesome-design-md/vercel/README.md`
- `external/awesome-design-md/claude/README.md`
- `external/awesome-design-md/stripe/README.md`

The local `README.md` files are only enough to confirm the slug and the target brand.

## Reading Remote Design Detail

When the brand name alone is not enough, fetch the matching design page:

- `https://getdesign.md/vercel/design-md`
- `https://getdesign.md/claude/design-md`
- `https://getdesign.md/stripe/design-md`

Extract only what implementation needs:

- atmosphere and tone
- color direction
- typography character
- spacing density
- component feel
- layout rhythm

If `defuddle` fails on the page, use a normal web reader fallback.

## Output Format

Respond in this order:

1. **Reference choice** — the best 1-3 slugs
2. **Why these references** — one short sentence each
3. **Design brief** — compact implementation constraints
4. **Next step** — explicitly load `frontend-design`

Example:

- Primary reference: `vercel`
- Supporting reference: `stripe`
- Why: `vercel` gives the monochrome infrastructure tone; `stripe` adds clearer product storytelling and trust framing
- Design brief: black-and-white base, sharp geometry, restrained accent color, tight type hierarchy, minimal but premium spacing, high-confidence CTA treatment
- Next action: load `frontend-design` and implement the page using this brief

## Common Mistakes

- Treating `awesome-design-md` as if it contains local skills
- Jumping straight into UI code without choosing a reference
- Picking too many references and averaging them into a bland result
- Using only the brand name without extracting concrete constraints
- Forgetting to hand off to `frontend-design`
