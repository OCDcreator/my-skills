---
name: liquid-glass-compose
description: >
  Implement Apple-style Liquid Glass / glassmorphism UI effects in Kotlin Compose Multiplatform
  projects using the `io.github.fletchmckee.liquid:liquid` library. Use this skill whenever the user
  asks to create frosted glass, glassmorphism, liquid glass, blur glass, translucent navigation bars,
  glass-style tabs/chips, or any frosted/blurry overlay UI in Jetpack Compose or Compose Multiplatform.
  Also trigger when the user mentions "glass effect", "glass style", "frosted glass", "毛玻璃", "玻璃效果",
  "liquid glass", "blur background", "translucent bar", "glass navigation", "glassmorphism" in the
  context of Android/Kotlin/Compose development — even if they don't mention the library by name.
  This skill also covers glass-style dialogs, bottom sheets, sidebars, floating action buttons,
  cards with blur, translucent panels, frosted overlays, and any UI component that should show
  blurred content behind it. Use it for all Compose glassmorphism regardless of component type —
  navigation bars, tab bars, and filter chips are the primary examples, but the same liquid library
  patterns apply to any translucent overlay surface.
---

# Liquid Glass Effect for Compose Multiplatform

This skill teaches you how to implement a production-quality glassmorphism ("Liquid Glass") UI effect
in Kotlin Compose Multiplatform, based on the patterns used in the GitHub Store app (65K+ users).

The effect uses the `liquid` library (`io.github.fletchmckee.liquid:liquid`) which provides
GPU-accelerated RuntimeShader-based blur, refraction, and chromatic dispersion. The result is a
real-time frosted glass look that works on Android API 33+ and JVM/Desktop platforms.

---

## 1. Add the Dependency

In your `gradle/libs.versions.toml`:

```toml
[versions]
liquid = "1.1.1"

[libraries]
liquid = { module = "io.github.fletchmckee.liquid:liquid", version.ref = "liquid" }
```

Then add to the relevant module's `build.gradle.kts`:

```kotlin
commonMain.dependencies {
    implementation(libs.liquid)
}
```

The library is on Maven Central — ensure `mavenCentral()` is in your repository block.

**Library links:**
- GitHub: https://github.com/FletchMcKee/liquid
- API docs: https://fletchmckee.github.io/liquid/api/
- Getting started: https://fletchmckee.github.io/liquid/getting_started/

---

## 2. The Core Pattern (3 Parts)

The liquid glass effect is a two-layer system: content behind the glass gets sampled and blurred,
then the glass panel renders the blurred version with optical effects on top.

### Part A: Create & Distribute LiquidState

Create the state at the top of your composable tree and pass it down via `CompositionLocal`:

```kotlin
// locals/LocalBottomBarLiquid.kt
package yourapp.ui.locals

import androidx.compose.runtime.compositionLocalOf
import io.github.fletchmckee.liquid.LiquidState

val LocalBottomBarLiquid = compositionLocalOf<LiquidState> {
    error("LiquidState not provided")
}
```

```kotlin
// In your top-level composable (e.g. AppNavigation)
val liquidState = rememberLiquidState()

CompositionLocalProvider(
    LocalBottomBarLiquid provides liquidState,
) {
    // Your app content
}
```

**Why separate LiquidState instances?** Each glass panel (bottom bar, top bar, sidebar) needs its
own `LiquidState` because each panel blurs a different region of the screen. Content that should
appear blurred through a specific panel must be registered to that panel's state via `liquefiable`.

### Part B: Mark Background Content as "Liquefiable"

Content that should be visible (blurred) through the glass must be marked with `Modifier.liquefiable()`:

```kotlin
Column(
    modifier = Modifier
        .fillMaxSize()
        .liquefiable(bottomBarLiquidState)  // Visible through bottom bar glass
        .liquefiable(topBarLiquidState),    // Visible through top bar glass
) {
    // Your scrollable content, cards, images, etc.
}
```

Each card/item in a list should also be marked so they blur correctly as they scroll behind the glass:

```kotlin
items.forEach { item ->
    ContentCard(
        modifier = Modifier
            .liquefiable(bottomBarLiquidState)
            .liquefiable(topBarLiquidState),
    )
}
```

### Part C: Apply the Glass Effect on the Panel

The glass container uses `Modifier.liquid()` to create the frosted effect:

```kotlin
Box(
    modifier = Modifier
        .clip(CircleShape)                              // or RoundedCornerShape(20.dp)
        .background(
            backgroundColor.copy(alpha = backgroundAlpha) // Semi-transparent fill
        )
        .liquid(liquidState) {
            // Optical parameters — see parameter tables below
            frost = 12.dp
            curve = 0.35f
            refraction = 0.08f
            dispersion = 0.18f
            saturation = 0.40f
            contrast = 1.8f
        }
) {
    // Glass panel content (icons, labels, etc.)
}
```

---

## 3. Parameter Reference Tables

These are the battle-tested values from a production app with 65K+ users, tuned for both dark and light themes.

### Bottom Navigation Bar (Pill/Capsule Shape)

| Parameter       | Dark Theme              | Light Theme             | Notes                        |
|-----------------|-------------------------|-------------------------|------------------------------|
| Background      | `surfaceContainerHighest @ 0.25` | `surfaceContainerHighest @ 0.15` | Semi-transparent surface |
| `frost`         | `12.dp`                 | `10.dp`                 | Blur radius                  |
| `curve`         | `0.35f`                 | `0.45f`                 | Lens curvature effect        |
| `refraction`    | `0.08f`                 | `0.12f`                 | Light bending                |
| `dispersion`    | `0.18f`                 | `0.25f`                 | Chromatic aberration         |
| `saturation`    | `0.40f`                 | `0.55f`                 | Color vividness boost        |
| `contrast`      | `1.8f`                  | `1.6f`                  | Tonal contrast               |
| `shape`         | `CircleShape`           | `CircleShape`           | Capsule shape                |

### Top Filter Chips / Tab Bar (Rounded Rectangle)

| Parameter       | Dark Theme              | Light Theme             | Notes                        |
|-----------------|-------------------------|-------------------------|------------------------------|
| Background      | `surfaceContainerHighest @ 0.30` | `primaryContainer @ 0.45` | Different color for emphasis |
| `frost`         | `14.dp`                 | `12.dp`                 | Slightly more blur than nav  |
| `curve`         | `0.30f`                 | `0.40f`                 |                              |
| `refraction`    | `0.06f`                 | `0.10f`                 |                              |
| `dispersion`    | `0.15f`                 | `0.22f`                 |                              |
| `saturation`    | `0.35f`                 | `0.50f`                 |                              |
| `contrast`      | `1.7f`                  | `1.5f`                  |                              |
| `shape`         | `RoundedCornerShape(20.dp)` | `RoundedCornerShape(20.dp)` |  |

### Theme Detection

```kotlin
val isDarkTheme = !MaterialTheme.colorScheme.background.luminance().let { it > 0.5f }
```

---

## 4. Hand-Drawn Glass Indicator (Selected Item Highlight)

The selected tab/chip gets a multi-layered glass pill indicator drawn with `drawBehind`. This creates
a realistic glass refraction look with 4 distinct layers.

### Glass Color Definitions

```kotlin
// ── Dark theme / Light theme values ──
val glassHighColor  = Color.White.copy(alpha = if (isDarkTheme) .12f else .30f)  // Top of gradient
val glassLowColor   = Color.White.copy(alpha = if (isDarkTheme) .04f else .10f)  // Bottom of gradient
val specularColor   = Color.White.copy(alpha = if (isDarkTheme) .18f else .45f)  // Mirror highlight
val innerGlowColor  = Color.White.copy(alpha = if (isDarkTheme) .03f else .08f)  // Bottom glow
val borderColor     = if (isDarkTheme) Color.White.copy(alpha = .08f) else Color.Transparent
```

### The 4-Layer Drawing (inside `drawBehind`)

Read the full reference implementation at `references/glass-indicator-draw.md` for the complete
`drawBehind` block. The 4 layers in painting order:

**Layer 1 — Border outline (dark mode only):**
A 1dp stroked round rect that gives the pill a subtle edge in dark themes.

**Layer 2 — Vertical gradient fill:**
```kotlin
drawRoundRect(
    brush = Brush.verticalGradient(
        colors = listOf(glassHighColor, glassLowColor)
    ),
    topLeft = Offset(indicatorX, pillTop),
    size = Size(indicatorWidth, pillHeight),
    cornerRadius = CornerRadius(pillCorner),
)
```

**Layer 3 — Horizontal specular highlight (top shine line):**
```kotlin
drawRoundRect(
    brush = Brush.horizontalGradient(
        colors = listOf(
            Color.Transparent,
            specularColor,
            specularColor.copy(alpha = specularColor.alpha * .6f),
            Color.Transparent,
        ),
        startX = specLeft,
        endX = specLeft + specWidth,
    ),
    topLeft = Offset(specLeft, pillTop + 1.dp.toPx()),
    size = Size(specWidth, 1.5.dp.toPx()),
    cornerRadius = CornerRadius(1.dp.toPx()),
)
```
This is only 1.5dp tall and spans ~70% of the indicator width, creating a thin bright reflection line.

**Layer 4 — Bottom inner glow:**
```kotlin
drawRoundRect(
    brush = Brush.verticalGradient(
        colors = listOf(Color.Transparent, innerGlowColor)
    ),
    topLeft = Offset(indicatorX + 6.dp.toPx(), pillTop + pillHeight - 5.dp.toPx()),
    size = Size(indicatorWidth - 12.dp.toPx(), 4.dp.toPx()),
    cornerRadius = CornerRadius(2.dp.toPx()),
)
```

**Optional Layer 5 — Left/right edge highlights** (used in filter chips):
```kotlin
val edgeAlpha = if (isDarkTheme) .06f else .12f
// Left edge
drawRoundRect(
    brush = Brush.horizontalGradient(
        colors = listOf(Color.White.copy(alpha = edgeAlpha), Color.Transparent)
    ),
    // ... left edge coordinates
)
// Right edge
drawRoundRect(
    brush = Brush.horizontalGradient(
        colors = listOf(Color.Transparent, Color.White.copy(alpha = edgeAlpha))
    ),
    // ... right edge coordinates
)
```

### Animated Indicator Position

The indicator smoothly animates between items using spring physics:

```kotlin
val indicatorX = remember { Animatable(0f) }
val indicatorWidth = remember { Animatable(0f) }

LaunchedEffect(selectedIndex, selectedItemPos) {
    val raw = selectedItemPos ?: itemPositions[selectedIndex] ?: return@LaunchedEffect
    val targetX = raw.first + rowPaddingPx - insetPx
    val targetW = raw.second + insetPx * 2f

    launch {
        indicatorX.animateTo(
            targetValue = targetX,
            animationSpec = spring(
                dampingRatio = Spring.DampingRatioLowBouncy,   // Slight overshoot
                stiffness = Spring.StiffnessLow,
            ),
        )
    }
    launch {
        indicatorWidth.animateTo(
            targetValue = targetW,
            animationSpec = spring(
                dampingRatio = Spring.DampingRatioNoBouncy,   // No overshoot on width
                stiffness = Spring.StiffnessMedium,
            ),
        )
    }
}
```

Item positions are tracked via `onGloballyPositioned`:

```kotlin
.onGloballyPositioned { coordinates ->
    val x = coordinates.positionInParent().x
    val width = coordinates.size.width.toFloat()
    scope.launch { onPositioned(x, width) }
}
```

---

## 5. Platform Compatibility (expect/actual)

The liquid library requires GPU shader support. On Android this means API 33+. Define a compatibility
check so you can fall back gracefully:

```kotlin
// commonMain: isLiquidFrostAvailable.kt
expect fun isLiquidFrostAvailable(): Boolean

// androidMain: isLiquidFrostAvailable.android.kt
actual fun isLiquidFrostAvailable(): Boolean =
    Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU

// jvmMain: isLiquidFrostAvailable.jvm.kt
actual fun isLiquidFrostAvailable(): Boolean = true  // Desktop always supports it
```

### Fallback When Glass Is Not Available

```kotlin
val useLiquid = isLiquidGlassEnabled && isLiquidFrostAvailable()

Box(
    modifier = Modifier
        .clip(shape)
        .then(
            if (useLiquid) {
                Modifier
                    .background(backgroundColor.copy(alpha = 0.25f))
                    .liquid(liquidState) { /* glass params */ }
            } else {
                Modifier
                    .background(MaterialTheme.colorScheme.surfaceContainer)
                    .border(1.dp, MaterialTheme.colorScheme.outlineVariant, shape)
            }
        )
)
```

---

## 6. Glass Item Animations

Each tab/chip item has press, selection, and label crossfade animations driven by spring physics.

**Key patterns:**

- **Press**: Scale down to 85–90% via `spring(DampingRatioMediumBouncy, StiffnessMedium)`
- **Selection**: Icon scales up to 115% via `spring(DampingRatioMediumBouncy, StiffnessLow)`
- **Label crossfade**: Two overlapping `Text` composables with different `FontWeight`, alpha crossfaded via `tween(200)`
- **Indicator position**: `Animatable` with `spring(DampingRatioLowBouncy, StiffnessLow)` for slight overshoot

Read the full animation reference at `references/item-animations.md` for complete specs, code, and position tracking setup.

---

## 7. Complete Implementation Checklist

When implementing this style, follow these steps in order:

1. **Add dependency** — `io.github.fletchmckee.liquid:liquid:1.1.1` via version catalog
2. **Create CompositionLocal** — One per glass panel (`LocalBottomBarLiquid`, `LocalTopBarLiquid`)
3. **Create LiquidState** — `rememberLiquidState()` at the top of your navigation/screen composable
4. **Provide via CompositionLocalProvider** — Distribute state to children
5. **Add platform check** — `expect/actual fun isLiquidFrostAvailable()` with Android API 33+ gate
6. **Mark background content** — Add `.liquefiable(state)` to scrollable content and list items
7. **Apply glass to panel** — `.liquid(state) { frost, curve, refraction, ... }` with theme-aware params
8. **Add semi-transparent background** — `.background(color.copy(alpha = 0.15-0.30))`
9. **Draw glass indicator** — `drawBehind` with 4 layers (gradient, specular, glow, border)
10. **Add spring animations** — Indicator position, press scale, selection scale
11. **Implement fallback** — Opaque background + border when glass is not available

---

## 8. File Reference

For complete working code examples, read the reference files in this skill:

- **`references/glass-indicator-draw.md`** — Full `drawBehind` implementation for the glass pill indicator
- **`references/bottom-nav-full.md`** — Complete bottom navigation bar composable (450 lines)
- **`references/filter-chips-full.md`** — Complete filter chips composable with glass effect (390 lines)
- **`references/item-animations.md`** — Complete animation specs and code for glass item press, selection, label crossfade, and indicator position tracking
