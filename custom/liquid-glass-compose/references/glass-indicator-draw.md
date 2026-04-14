# Glass Pill Indicator — drawBehind Implementation

This is the 4-layer glass pill indicator drawn behind the selected tab/chip.
It creates the illusion of a translucent glass capsule highlighting the active item.

## Table of Contents

- [Overview](#overview)
- [Color Definitions](#color-definitions)
- [Complete drawBehind Code (Bottom Navigation Style — CircleShape)](#complete-drawbehind-code-bottom-navigation-style--circleshape)
- [Complete drawBehind Code (Filter Chips Style — RoundedCornerShape)](#complete-drawbehind-code-filter-chips-style--roundedcornershape)
- [Indicator Animation Setup](#indicator-animation-setup)

## Overview

The indicator is drawn using `Modifier.drawBehind { ... }` on a `Box` that is
`matchParentSize()` inside the glass container. It uses 4 overlapping layers:

```
Layer 4 (top):    Horizontal specular highlight stripe
Layer 1:          Vertical gradient fill (top-bright → bottom-dim)
Layer 3:          Bottom inner glow
Layer 2:          Edge highlights (left & right sides)
```

## Color Definitions

These colors are adapted for dark/light themes:

```kotlin
val isDarkTheme = !MaterialTheme.colorScheme.background.luminance().let { it > 0.5f }

// For Bottom Navigation Bar
val glassHighColor = Color.White.copy(alpha = if (isDarkTheme) .12f else .30f)
val glassLowColor = Color.White.copy(alpha = if (isDarkTheme) .04f else .10f)
val specularColor = Color.White.copy(alpha = if (isDarkTheme) .18f else .45f)
val innerGlowColor = Color.White.copy(alpha = if (isDarkTheme) .03f else .08f)
val borderColor = if (isDarkTheme) Color.White.copy(alpha = .08f) else Color.Transparent

// For Top Filter Chips (slightly more transparent)
val glassHighColor = Color.White.copy(alpha = if (isDarkTheme) .14f else .50f)
val glassLowColor = Color.White.copy(alpha = if (isDarkTheme) .05f else .18f)
val specularColor = Color.White.copy(alpha = if (isDarkTheme) .20f else .55f)
val innerGlowColor = Color.White.copy(alpha = if (isDarkTheme) .04f else .10f)
val borderColor = if (isDarkTheme) Color.White.copy(alpha = .10f) else Color.Transparent
```

## Complete drawBehind Code (Bottom Navigation Style — CircleShape)

```kotlin
Box(
    modifier = Modifier
        .matchParentSize()
        .drawBehind {
            if (indicatorWidth.value > 0f) {
                // === Layer: Dark theme border ===
                if (isDarkTheme) {
                    drawRoundRect(
                        color = borderColor,
                        topLeft = Offset(
                            indicatorX.value - .5.dp.toPx(),
                            1.5.dp.toPx(),
                        ),
                        size = Size(
                            indicatorWidth.value + 1.dp.toPx(),
                            size.height - 3.dp.toPx(),
                        ),
                        cornerRadius = CornerRadius(size.height / 2f),
                        style = Stroke(width = 1.dp.toPx()),
                    )
                }

                // === Layer 1: Vertical gradient fill ===
                drawRoundRect(
                    brush = Brush.verticalGradient(
                        colors = listOf(glassHighColor, glassLowColor),
                    ),
                    topLeft = Offset(indicatorX.value, 2.dp.toPx()),
                    size = Size(indicatorWidth.value, size.height - 4.dp.toPx()),
                    cornerRadius = CornerRadius(size.height / 2f),
                )

                // === Layer 2: Horizontal specular highlight ===
                drawRoundRect(
                    brush = Brush.horizontalGradient(
                        colors = listOf(
                            Color.Transparent,
                            specularColor,
                            Color.Transparent,
                        ),
                        startX = indicatorX.value + indicatorWidth.value * .15f,
                        endX = indicatorX.value + indicatorWidth.value * .85f,
                    ),
                    topLeft = Offset(
                        indicatorX.value + indicatorWidth.value * .15f,
                        3.dp.toPx(),
                    ),
                    size = Size(indicatorWidth.value * .7f, 1.5.dp.toPx()),
                    cornerRadius = CornerRadius(1.dp.toPx()),
                )

                // === Layer 3: Bottom inner glow ===
                drawRoundRect(
                    brush = Brush.verticalGradient(
                        colors = listOf(Color.Transparent, innerGlowColor),
                    ),
                    topLeft = Offset(
                        indicatorX.value + 4.dp.toPx(),
                        size.height - 8.dp.toPx(),
                    ),
                    size = Size(indicatorWidth.value - 8.dp.toPx(), 4.dp.toPx()),
                    cornerRadius = CornerRadius(2.dp.toPx()),
                )
            }
        },
)
```

## Complete drawBehind Code (Filter Chips Style — RoundedCornerShape)

The chip variant adds edge highlights and uses different positioning:

```kotlin
Box(
    modifier = Modifier
        .matchParentSize()
        .drawBehind {
            if (indicatorWidth.value > 0f) {
                val pillTop = 5.dp.toPx()
                val pillHeight = size.height - 10.dp.toPx()
                val pillCorner = 14.dp.toPx()
                val pillRadius = CornerRadius(pillCorner)

                // === Layer: Dark theme border ===
                if (isDarkTheme) {
                    drawRoundRect(
                        color = borderColor,
                        topLeft = Offset(
                            indicatorX.value - .5.dp.toPx(),
                            pillTop - .5.dp.toPx(),
                        ),
                        size = Size(
                            indicatorWidth.value + 1.dp.toPx(),
                            pillHeight + 1.dp.toPx(),
                        ),
                        cornerRadius = pillRadius,
                        style = Stroke(width = 1.dp.toPx()),
                    )
                }

                // === Layer 1: Vertical gradient fill ===
                drawRoundRect(
                    brush = Brush.verticalGradient(
                        colors = listOf(glassHighColor, glassLowColor),
                        startY = pillTop,
                        endY = pillTop + pillHeight,
                    ),
                    topLeft = Offset(indicatorX.value, pillTop),
                    size = Size(indicatorWidth.value, pillHeight),
                    cornerRadius = pillRadius,
                )

                // === Layer 2: Horizontal specular highlight ===
                val specLeft = indicatorX.value + indicatorWidth.value * .12f
                val specWidth = indicatorWidth.value * .76f
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

                // === Layer 3: Bottom inner glow ===
                drawRoundRect(
                    brush = Brush.verticalGradient(
                        colors = listOf(Color.Transparent, innerGlowColor),
                        startY = pillTop + pillHeight - 6.dp.toPx(),
                        endY = pillTop + pillHeight,
                    ),
                    topLeft = Offset(
                        indicatorX.value + 6.dp.toPx(),
                        pillTop + pillHeight - 5.dp.toPx(),
                    ),
                    size = Size(indicatorWidth.value - 12.dp.toPx(), 4.dp.toPx()),
                    cornerRadius = CornerRadius(2.dp.toPx()),
                )

                // === Layer 4: Left edge highlight ===
                val edgeAlpha = if (isDarkTheme) .06f else .12f
                drawRoundRect(
                    brush = Brush.horizontalGradient(
                        colors = listOf(
                            Color.White.copy(alpha = edgeAlpha),
                            Color.Transparent,
                        ),
                        startX = indicatorX.value,
                        endX = indicatorX.value + 4.dp.toPx(),
                    ),
                    topLeft = Offset(indicatorX.value, pillTop + 4.dp.toPx()),
                    size = Size(3.dp.toPx(), pillHeight - 8.dp.toPx()),
                    cornerRadius = CornerRadius(1.5.dp.toPx()),
                )

                // === Layer 4: Right edge highlight ===
                drawRoundRect(
                    brush = Brush.horizontalGradient(
                        colors = listOf(
                            Color.Transparent,
                            Color.White.copy(alpha = edgeAlpha),
                        ),
                        startX = indicatorX.value + indicatorWidth.value - 4.dp.toPx(),
                        endX = indicatorX.value + indicatorWidth.value,
                    ),
                    topLeft = Offset(
                        indicatorX.value + indicatorWidth.value - 3.dp.toPx(),
                        pillTop + 4.dp.toPx(),
                    ),
                    size = Size(3.dp.toPx(), pillHeight - 8.dp.toPx()),
                    cornerRadius = CornerRadius(1.5.dp.toPx()),
                )
            }
        },
)
```

## Indicator Animation Setup

The indicator position and width are animated using `Animatable` with spring physics:

```kotlin
val indicatorX = remember { Animatable(0f) }
val indicatorWidth = remember { Animatable(0f) }

// Track each item's position in the Row
val itemPositions = remember { mutableMapOf<Int, Pair<Float, Float>>() }
var selectedItemPos by remember { mutableStateOf<Pair<Float, Float>?>(null) }

// Animate when selection changes
LaunchedEffect(selectedIndex, selectedItemPos) {
    val raw = selectedItemPos ?: itemPositions[selectedIndex] ?: return@LaunchedEffect
    val targetX = raw.first + rowPaddingPx - insetPx
    val targetW = raw.second + insetPx * 2f

    launch {
        indicatorX.animateTo(
            targetValue = targetX,
            animationSpec = spring(
                dampingRatio = Spring.DampingRatioLowBouncy,
                stiffness = Spring.StiffnessLow,
            ),
        )
    }
    launch {
        indicatorWidth.animateTo(
            targetValue = targetW,
            animationSpec = spring(
                dampingRatio = Spring.DampingRatioNoBouncy,
                stiffness = Spring.StiffnessMedium,
            ),
        )
    }
}

// Snap on first composition (no animation for initial state)
// Inside the item's onGloballyPositioned:
if (index == selectedIndex && indicatorWidth.value == 0f) {
    indicatorX.snapTo(x + rowPaddingPx - insetPx)
    indicatorWidth.snapTo(width + insetPx * 2f)
}
```
