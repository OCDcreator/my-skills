# Glass Item Animations — Full Reference

Complete animation specs for glass-style tab/chip items, including press, selection,
label, and indicator animations.

## Animation Specs Table

| Animation | Type | Damping | Stiffness | Duration | Notes |
|-----------|------|---------|-----------|----------|-------|
| Press scale | spring | MediumBouncy | Medium | — | Scale down to 85–90% |
| Icon scale (selected) | spring | MediumBouncy | Low | — | Scale up to 115% |
| Icon offsetY (selected) | spring | MediumBouncy | Low | — | Slight upward shift |
| Label alpha (show/hide) | tween | FastOutSlowInEasing | — | 250ms / 150ms | Fade in/out |
| Label scale (selected) | spring | MediumBouncy | Low | — | Grow slightly |
| Horizontal padding | spring | NoBouncy | MediumLow | — | Expand when selected |

## Press Animation

```kotlin
// Scale down to 85-90% when pressed
val pressScale by animateFloatAsState(
    targetValue = if (isPressed) 0.85f else 1f,
    animationSpec = spring(
        dampingRatio = Spring.DampingRatioMediumBouncy,
        stiffness = Spring.StiffnessMedium,
    ),
)

// Apply to the whole item
Modifier.graphicsLayer {
    scaleX = pressScale
    scaleY = pressScale
}
```

## Selection Animation

```kotlin
// Icon scales up when selected
val iconScale by animateFloatAsState(
    targetValue = if (isSelected) 1.15f else 1f,
    animationSpec = spring(
        dampingRatio = Spring.DampingRatioMediumBouncy,
        stiffness = Spring.StiffnessLow,
    ),
)
```

## Label Crossfade (Filter Chips)

Use two overlapping `Text` composables with different font weights, crossfading
between them based on selection state:

```kotlin
val selectedAlpha by animateFloatAsState(
    targetValue = if (isSelected) 1f else 0f,
    animationSpec = tween(200),
)

val textColor by animateColorAsState(
    targetValue = if (isSelected) {
        MaterialTheme.colorScheme.onSurface
    } else {
        MaterialTheme.colorScheme.onSurface.copy(alpha = .65f)
    },
    animationSpec = tween(250),
)

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
```

## Indicator Position Animation

The glass pill indicator smoothly animates between items using spring physics.
Two `Animatable` values track horizontal position and width independently:

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

### Position Tracking

Each item reports its position via `onGloballyPositioned`:

```kotlin
.onGloballyPositioned { coordinates ->
    val x = coordinates.positionInParent().x
    val width = coordinates.size.width.toFloat()
    scope.launch { onPositioned(x, width) }
}
```

### Initial Snap (No Animation)

On first composition, snap the indicator to the selected item without animation:

```kotlin
// Inside onGloballyPositioned callback:
if (index == selectedIndex && indicatorWidth.value == 0f) {
    indicatorX.snapTo(x + rowPaddingPx - insetPx)
    indicatorWidth.snapTo(width + insetPx * 2f)
}
```
