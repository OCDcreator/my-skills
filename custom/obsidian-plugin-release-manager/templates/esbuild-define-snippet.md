# esbuild `define` Injection Snippet

在 `esbuild.config.mjs` 中可直接复用下面的模式：

```js
import esbuild from 'esbuild';
import fs from 'fs';

const packageJson = JSON.parse(
  fs.readFileSync(new URL('./package.json', import.meta.url), 'utf-8')
);

const appVersion = packageJson.version;
const releaseCodename = packageJson.releaseCodename ?? 'Reed';
const buildId = `${appVersion}+${new Date().toISOString()}`;

const context = await esbuild.context({
  define: {
    __APP_VERSION__: JSON.stringify(appVersion),
    __BUILD_ID__: JSON.stringify(buildId),
    __RELEASE_CODENAME__: JSON.stringify(releaseCodename),
  },
  // ...
});
```

## Notes

- `releaseCodename` 来自 `package.json`
- `manifest.json` 不参与展示层拼装
- `BUILD_ID` 应在构建时生成，而不是运行时生成
