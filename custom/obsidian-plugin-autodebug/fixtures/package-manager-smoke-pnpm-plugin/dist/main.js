class PackageManagerSmokePnpmPlugin extends Plugin {
  async onload() {
    console.log('[package-manager-smoke-pnpm-plugin] loaded');
  }

  onunload() {
    console.log('[package-manager-smoke-pnpm-plugin] unloaded');
  }
}
