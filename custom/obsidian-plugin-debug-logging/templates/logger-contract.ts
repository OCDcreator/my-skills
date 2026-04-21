// Template: adapt names, storage keys, indentation, and imports to the target Obsidian plugin.

export type LogLevel = 'always' | 'debug' | 'info' | 'warn' | 'error';
export type DebugModuleKey = string;

export interface LogEntry {
	timestamp: string;
	level: LogLevel;
	scope: string;
	message: string;
}

export interface DebugModuleDefinition {
	key: DebugModuleKey;
	label: string;
	description?: string;
	defaultEnabled?: boolean;
}

export interface Logger {
	always: (...args: unknown[]) => void;
	debug: (...args: unknown[]) => void;
	info: (...args: unknown[]) => void;
	warn: (...args: unknown[]) => void;
	error: (...args: unknown[]) => void;
}

export interface LoggerOptions {
	module?: DebugModuleKey;
}

const DEBUG_STORAGE_KEY = '<plugin-id>:debug';
const INLINE_DEBUG_ARGS_STORAGE_KEY = '<plugin-id>:inline-debug-args';
const DEBUG_MODULES_STORAGE_KEY = '<plugin-id>:debug-modules';
const DEBUG_REFRESH_INTERVAL_MS_STORAGE_KEY = '<plugin-id>:debug-refresh-interval-ms';
const DEBUG_FLAG_KEY = '__<PLUGIN_GLOBAL>_DEBUG__';
const INLINE_DEBUG_ARGS_FLAG_KEY = '__<PLUGIN_GLOBAL>_INLINE_DEBUG_ARGS__';
const DEBUG_MODULES_FLAG_KEY = '__<PLUGIN_GLOBAL>_DEBUG_MODULES__';
const DEBUG_REFRESH_INTERVAL_MS_FLAG_KEY = '__<PLUGIN_GLOBAL>_DEBUG_REFRESH_INTERVAL_MS__';
const MAX_LOG_ENTRIES = 500;
const DEFAULT_DEBUG_REFRESH_INTERVAL_MS = 1000;
const recentLogEntries: LogEntry[] = [];
const lastPayloadByKey = new Map<string, string>();

export const DEBUG_MODULE_REGISTRY: DebugModuleDefinition[] = [
	{ key: 'lifecycle', label: '启动 / 生命周期', defaultEnabled: true },
	{ key: 'sync', label: '同步 / 后台任务', defaultEnabled: true },
	{ key: 'render', label: '渲染 / UI 更新', defaultEnabled: true },
];

const DEFAULT_DEBUG_MODULES = Object.fromEntries(
	DEBUG_MODULE_REGISTRY.map((entry) => [entry.key, entry.defaultEnabled ?? true]),
) as Record<DebugModuleKey, boolean>;

type LoggerGlobalState = {
	[DEBUG_FLAG_KEY]?: boolean;
	[INLINE_DEBUG_ARGS_FLAG_KEY]?: boolean;
	[DEBUG_MODULES_FLAG_KEY]?: Record<DebugModuleKey, boolean>;
	[DEBUG_REFRESH_INTERVAL_MS_FLAG_KEY]?: number;
};

function getLoggerGlobalState(): LoggerGlobalState {
	return globalThis as LoggerGlobalState;
}

function readJsonStorage<T>(storageKey: string, fallback: T): T {
	try {
		const raw = globalThis.localStorage?.getItem(storageKey);
		if (!raw) {
			return fallback;
		}
		return JSON.parse(raw) as T;
	} catch {
		return fallback;
	}
}

function writeStorage(storageKey: string, value: string): void {
	try {
		globalThis.localStorage?.setItem(storageKey, value);
	} catch {
		// Ignore storage failures; in-memory state still applies for this runtime.
	}
}

export function isDebugLoggingEnabled(): boolean {
	const globalValue = getLoggerGlobalState()[DEBUG_FLAG_KEY];
	if (typeof globalValue === 'boolean') {
		return globalValue;
	}

	try {
		return globalThis.localStorage?.getItem(DEBUG_STORAGE_KEY) === 'true';
	} catch {
		return false;
	}
}

export function setDebugLoggingEnabled(enabled: boolean): void {
	getLoggerGlobalState()[DEBUG_FLAG_KEY] = enabled;
	writeStorage(DEBUG_STORAGE_KEY, String(enabled));
}

export function isInlineSerializedDebugLogArgsEnabled(): boolean {
	const globalValue = getLoggerGlobalState()[INLINE_DEBUG_ARGS_FLAG_KEY];
	if (typeof globalValue === 'boolean') {
		return globalValue;
	}

	try {
		return globalThis.localStorage?.getItem(INLINE_DEBUG_ARGS_STORAGE_KEY) === 'true';
	} catch {
		return false;
	}
}

export function setInlineSerializedDebugLogArgsEnabled(enabled: boolean): void {
	getLoggerGlobalState()[INLINE_DEBUG_ARGS_FLAG_KEY] = enabled;
	writeStorage(INLINE_DEBUG_ARGS_STORAGE_KEY, String(enabled));
}

export function getDebugModuleSettings(): Record<DebugModuleKey, boolean> {
	const globalValue = getLoggerGlobalState()[DEBUG_MODULES_FLAG_KEY];
	if (globalValue) {
		return {
			...DEFAULT_DEBUG_MODULES,
			...globalValue,
		};
	}

	return {
		...DEFAULT_DEBUG_MODULES,
		...readJsonStorage<Record<DebugModuleKey, boolean>>(DEBUG_MODULES_STORAGE_KEY, {}),
	};
}

export function isDebugModuleEnabled(moduleKey?: DebugModuleKey): boolean {
	if (!moduleKey) {
		return true;
	}
	return getDebugModuleSettings()[moduleKey] ?? true;
}

export function setDebugModuleEnabled(moduleKey: DebugModuleKey, enabled: boolean): void {
	const nextValue = {
		...getDebugModuleSettings(),
		[moduleKey]: enabled,
	};
	getLoggerGlobalState()[DEBUG_MODULES_FLAG_KEY] = nextValue;
	writeStorage(DEBUG_MODULES_STORAGE_KEY, JSON.stringify(nextValue));
}

export function getDebugRefreshIntervalMs(): number {
	const globalValue = getLoggerGlobalState()[DEBUG_REFRESH_INTERVAL_MS_FLAG_KEY];
	if (typeof globalValue === 'number' && Number.isFinite(globalValue) && globalValue > 0) {
		return globalValue;
	}

	const storedValue = Number(readJsonStorage<number>(DEBUG_REFRESH_INTERVAL_MS_STORAGE_KEY, DEFAULT_DEBUG_REFRESH_INTERVAL_MS));
	return Number.isFinite(storedValue) && storedValue > 0 ? storedValue : DEFAULT_DEBUG_REFRESH_INTERVAL_MS;
}

export function setDebugRefreshIntervalMs(intervalMs: number): void {
	const normalized = Number.isFinite(intervalMs) && intervalMs > 0 ? Math.round(intervalMs) : DEFAULT_DEBUG_REFRESH_INTERVAL_MS;
	getLoggerGlobalState()[DEBUG_REFRESH_INTERVAL_MS_FLAG_KEY] = normalized;
	writeStorage(DEBUG_REFRESH_INTERVAL_MS_STORAGE_KEY, JSON.stringify(normalized));
}

function shouldEmit(level: LogLevel, moduleKey?: DebugModuleKey): boolean {
	if (level === 'always' || level === 'warn' || level === 'error') {
		return true;
	}
	return isDebugLoggingEnabled() && isDebugModuleEnabled(moduleKey);
}

function getShortTimestamp(): string {
	const now = new Date();
	const hours = String(now.getHours()).padStart(2, '0');
	const minutes = String(now.getMinutes()).padStart(2, '0');
	const seconds = String(now.getSeconds()).padStart(2, '0');
	return `${hours}:${minutes}:${seconds}`;
}

function safeStringify(arg: unknown): string {
	if (typeof arg === 'string') {
		return arg;
	}
	if (arg instanceof Error) {
		return arg.stack || arg.message;
	}
	try {
		return JSON.stringify(arg);
	} catch {
		return String(arg);
	}
}

function redactSecrets(message: string): string {
	return message
		.replace(/(api[_-]?key|token|secret|password)(["'\s:=]+)([^"',\s]+)/gi, '$1$2[redacted]')
		.replace(/(bearer\s+)[a-z0-9._~+/=-]+/gi, '$1[redacted]');
}

export function previewText(value: unknown, maxLength = 200): string {
	const text = redactSecrets(safeStringify(value));
	if (text.length <= maxLength) {
		return text;
	}
	return `${text.slice(0, maxLength)}… (${text.length} chars)`;
}

function formatArgs(scope: string, level: LogLevel, args: unknown[], inlineSerialize = false): unknown[] {
	const prefix = `[${getShortTimestamp()}] [${level.toUpperCase()}] [${scope}]`;
	if (inlineSerialize) {
		const message = args.map((arg) => previewText(arg)).filter(Boolean).join(' ');
		return message ? [`${prefix} ${message}`] : [prefix];
	}
	if (typeof args[0] === 'string') {
		return [`${prefix} ${args[0]}`, ...args.slice(1)];
	}
	return [prefix, ...args];
}

function pushRecentLog(level: LogLevel, scope: string, args: unknown[]): void {
	recentLogEntries.push({
		timestamp: new Date().toISOString(),
		level,
		scope,
		message: args.map((arg) => previewText(arg, 500)).filter(Boolean).join(' '),
	});
	if (recentLogEntries.length > MAX_LOG_ENTRIES) {
		recentLogEntries.splice(0, recentLogEntries.length - MAX_LOG_ENTRIES);
	}
}

function emit(level: LogLevel, scope: string, args: unknown[], inlineSerialize = false, moduleKey?: DebugModuleKey): void {
	if (!shouldEmit(level, moduleKey)) {
		return;
	}

	pushRecentLog(level, scope, args);

	const formattedArgs = formatArgs(scope, level, args, inlineSerialize);
	switch (level) {
		case 'error':
			globalThis.console?.error(...formattedArgs);
			break;
		case 'warn':
			globalThis.console?.warn(...formattedArgs);
			break;
		default:
			globalThis.console?.log(...formattedArgs);
			break;
	}
}

export function createLogger(scope: string, options: LoggerOptions = {}): Logger {
	return {
		always: (...args: unknown[]) => emit('always', scope, args, false, options.module),
		info: (...args: unknown[]) => emit('info', scope, args, false, options.module),
		debug: (...args: unknown[]) => emit('debug', scope, args, isInlineSerializedDebugLogArgsEnabled(), options.module),
		warn: (...args: unknown[]) => emit('warn', scope, args, false, options.module),
		error: (...args: unknown[]) => emit('error', scope, args, false, options.module),
	};
}

export function logOnceUntilChanged(logger: Logger, key: string, label: string, payload: unknown): void {
	const serializedPayload = previewText(payload, 1000);
	if (lastPayloadByKey.get(key) === serializedPayload) {
		return;
	}
	lastPayloadByKey.set(key, serializedPayload);
	logger.debug(`${label}:`, payload);
}

export function createThrottledDebugLogger(intervalMs: number | (() => number)): (logger: Logger, message: string, payload?: unknown) => void {
	let lastLoggedAt = 0;
	return (logger, message, payload) => {
		const now = Date.now();
		const resolvedIntervalMs = typeof intervalMs === 'function' ? intervalMs() : intervalMs;
		const nextIntervalMs = Number.isFinite(resolvedIntervalMs) && resolvedIntervalMs > 0
			? resolvedIntervalMs
			: DEFAULT_DEBUG_REFRESH_INTERVAL_MS;
		if (now - lastLoggedAt < nextIntervalMs) {
			return;
		}
		lastLoggedAt = now;
		if (payload === undefined) {
			logger.debug(message);
		} else {
			logger.debug(message, payload);
		}
	};
}

export function clearRecentLogs(): void {
	recentLogEntries.length = 0;
	lastPayloadByKey.clear();
}

export function getRecentLogEntries(): LogEntry[] {
	return [...recentLogEntries];
}

export function getRecentLogText(): string {
	return recentLogEntries
		.map((entry) => `${entry.timestamp} [${entry.level.toUpperCase()}] [${entry.scope}] ${entry.message}`)
		.join('\n');
}
