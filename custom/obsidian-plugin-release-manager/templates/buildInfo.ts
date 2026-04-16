declare const __APP_VERSION__: string;
declare const __BUILD_ID__: string;
declare const __RELEASE_CODENAME__: string;

export const APP_VERSION = __APP_VERSION__;
export const BUILD_ID = __BUILD_ID__;
export const RELEASE_CODENAME = __RELEASE_CODENAME__;
export const DISPLAY_VERSION = `${RELEASE_CODENAME} v${APP_VERSION}`;
