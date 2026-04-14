# Filter Chips / Top Tab Bar — Full Implementation

Complete working code for a glassmorphic top filter chips bar with animated pill indicator,
based on the GitHub Store `LiquidGlassCategoryChips` implementation.

## Key Design Decisions

- **Shape**: `RoundedCornerShape(20.dp)` for the container (rounded rectangle pill)
- **Layout**: Full-width horizontal Row with `weight(1f)` items
- **Liquid effect**: Only enabled when `isLiquidGlassEnabled && isLiquidFrostAvailable()`
- **Each chip item** tracks its position for the animated indicator
- **Background color differs**: Dark uses `surfaceContainerHighest`, Light uses `primaryContainer`

## Liquid Glass Parameters (Filter Chips)

| Parameter | Dark Theme | Light Theme |
|-----------|-----------|-------------|
| Background alpha | 30% (surfaceContainerHighest) | 45% (primaryContainer) |
| frost | 14dp | 12dp |
| curve | 0.30 | 0.40 |
| refraction | 0.06 | 0.10 |
| dispersion | 0.15 | 0.22 |
| saturation | 0.35 | 0.50 |
| contrast | 1.7 | 1.5 |

## Glass Colors (Filter Chips)

| Color | Dark Theme | Light Theme |
|-------|-----------|-------------|
| glassHighColor | White @ 14% | White @ 50% |
| glassLowColor | White @ 5% | White @ 18% |
| specularColor | White @ 20% | White @ 55% |
| innerGlowColor | White @ 4% | White @ 10% |
| borderColor | White @ 10% | Transparent |
| edgeAlpha | 6% | 12% |

## Extra Layers (vs Bottom Nav)

The filter chips add two additional layers that the bottom nav doesn't have:

### Left Edge Highlight
```kotlin
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
```

### Right Edge Highlight
```kotlin
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
```

## Chip Item Animation

```kotlin
@Composable
private fun LiquidGlassCategoryChip(
    category: Category,
    isSelected: Boolean,
    onSelect: () -> Unit,
    modifier: Modifier = Modifier,
    onPositioned: suspend (x: Float, width: Float) -> Unit,
) {
    // Press: scale down to 90%
    val pressScale by animateFloatAsState(
        targetValue = if (isPressed) 0.90f else 1f,
        animationSpec = spring(
            dampingRatio = Spring.DampingRatioMediumBouncy,
            stiffness = Spring.StiffnessMedium,
        ),
    )

    // Crossfade between normal/bold text
    val selectedAlpha by animateFloatAsState(
        targetValue = if (isSelected) 1f else 0f,
        animationSpec = tween(200),
    )

    // Text color animation
    val textColor by animateColorAsState(
        targetValue = if (isSelected) {
            MaterialTheme.colorScheme.onSurface
        } else {
            MaterialTheme.colorScheme.onSurface.copy(alpha = .65f)
        },
        animationSpec = tween(250),
    )

    Box(
        modifier = modifier
            .clip(CircleShape)
            .clickable(interactionSource = interactionSource, indication = null) { onSelect() }
            .onGloballyPositioned { coordinates ->
                val x = coordinates.positionInParent().x
                val width = coordinates.size.width.toFloat()
                scope.launch { onPositioned(x, width) }
            }
            .graphicsLayer { scaleX = pressScale; scaleY = pressScale }
            .padding(vertical = 8.dp),
        contentAlignment = Alignment.Center,
    ) {
        // Two overlapping texts for crossfade between font weights
        Box(contentAlignment = Alignment.Center) {
            Text(
                text = category.displayText(),
                style = MaterialTheme.typography.labelLarge.copy(
                    fontWeight = FontWeight.Medium,
                ),
                color = textColor,
                modifier = Modifier.graphicsLayer { alpha = 1f - selectedAlpha },
            )
            Text(
                text = category.displayText(),
                style = MaterialTheme.typography.labelLarge.copy(
                    fontWeight = FontWeight.Bold,
                ),
                color = textColor,
                modifier = Modifier.graphicsLayer { alpha = selectedAlpha },
            )
        }
    }
}
```

## Usage Pattern

```kotlin
// In your screen composable
val topBarLiquidState = rememberLiquidState()

CompositionLocalProvider(
    LocalTopBarLiquid provides topBarLiquidState,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .then(
                if (isLiquidGlassEnabled) {
                    Modifier.liquefiable(topBarLiquidState)
                } else Modifier
            ),
    ) {
        LiquidGlassCategoryChips(
            categories = categories,
            selectedCategory = selectedCategory,
            onCategorySelected = { /* ... */ },
            isLiquidGlassEnabled = isLiquidGlassEnabled,
        )

        // Scrollable content below
    }
}
```
