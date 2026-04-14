# Bottom Navigation Bar — Full Implementation

Complete working code for a glassmorphic bottom navigation bar with animated pill indicator,
based on the GitHub Store implementation.

## Key Design Decisions

- **Shape**: `CircleShape` for the entire bar (floating pill shape)
- **Position**: Bottom center with `navigationBarsPadding() + padding(bottom = 24.dp)`
- **Liquid effect**: Only enabled when `isLiquidGlassEnabled && isLiquidFrostAvailable()`
- **Each tab item** tracks its own position for the animated indicator

## Liquid Glass Parameters (Bottom Nav)

| Parameter | Dark Theme | Light Theme |
|-----------|-----------|-------------|
| Background alpha | 25% | 15% |
| frost | 12dp | 10dp |
| curve | 0.35 | 0.45 |
| refraction | 0.08 | 0.12 |
| dispersion | 0.18 | 0.25 |
| saturation | 0.40 | 0.55 |
| contrast | 1.8 | 1.6 |

## Glass Colors (Bottom Nav)

| Color | Dark Theme | Light Theme |
|-------|-----------|-------------|
| glassHighColor | White @ 12% | White @ 30% |
| glassLowColor | White @ 4% | White @ 10% |
| specularColor | White @ 18% | White @ 45% |
| innerGlowColor | White @ 3% | White @ 8% |
| borderColor | White @ 8% | Transparent |

## Item Animation Specs

| Animation | Type | Damping | Stiffness |
|-----------|------|---------|-----------|
| Press scale | spring | MediumBouncy | Medium |
| Icon scale (selected) | spring | MediumBouncy | Low |
| Icon offsetY | spring | MediumBouncy | Low |
| Label alpha | tween | FastOutSlowIn | 250ms/150ms |
| Label scale | spring | MediumBouncy | Low |
| Horizontal padding | spring | NoBouncy | MediumLow |

## Usage Pattern

```kotlin
// In AppNavigation.kt
val liquidState = rememberLiquidState()

CompositionLocalProvider(
    LocalBottomNavigationLiquid provides liquidState,
) {
    Box(modifier = Modifier.fillMaxSize()) {
        // NavHost content (each screen's content should use liquefiable)

        BottomNavigation(
            currentScreen = currentScreen,
            onNavigate = { navController.navigate(it) { /* ... */ } },
            isUpdateAvailable = appsState.apps.any { it.installedApp.isUpdateAvailable },
            isLiquidGlassEnabled = state.isLiquidGlassEnabled,
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .navigationBarsPadding()
                .padding(bottom = 24.dp),
        )
    }
}
```

## Content Registration

In each screen's scrollable content, register for blur:

```kotlin
// In HomeRoot.kt or any screen with scrollable content
val liquidState = LocalBottomNavigationLiquid.current

LazyVerticalGrid(
    modifier = Modifier
        .fillMaxSize()
        .then(
            if (isLiquidGlassEnabled) {
                Modifier.liquefiable(liquidState)
            } else Modifier
        ),
) {
    items(items) { item ->
        ItemCard(
            modifier = Modifier.then(
                if (isLiquidGlassEnabled) {
                    Modifier.liquefiable(liquidState)
                } else Modifier
            ),
        )
    }
}
```
