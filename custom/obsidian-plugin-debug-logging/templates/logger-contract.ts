// Template: adapt names, storage keys, indentation, and imports to the target Obsidian plugin.

export type LogLevel = 'always' | 'debug' | 'info' | 'warn' | 'error';

export interface LogEntry {
	timestamp: string;
	level: LogLevel;
	scope: string;
	message: string;
}

export interface Logger {
	always: (...args: unknown[]) => void;
	debug: (...args: unknown[]) => void;
	info: (...args: unknown[]) => void;
	warn: (...args: unknown[]) => void;
	error: (...args: unknown[]) => void;
}

const DEBUG_STORAGE_KEY = '<plugin-id>:debug';
const INLINE_DEBUG_ARGS_STORAGE_KEY = '<plugin-id>:inline-debug-args';
const DEBUG_FLAG_KEY = '__<PLUGIN_GLOBAL>_DEBUG__';
const INLINE_DEBUG_ARGS_FLAG_KEY = '__<PLUGIN_GLOBAL>_INLINE_DEBUG_ARGS__';
const MAX_LOG_ENTRIES = 500;
const recentLogEntries: LogEntry[] = [];
const lastPayloadByKey = new Map<string, string>();

type LoggerGlobalState = {
	[DEBUG_FLAG_KEY]?: boolean;
	[INLINE_DEBUG_ARGS_FLAG_KEY]?: boolean;
};

function getLoggerGlobalState(): LoggerGlobalState {
	return globalThis as LoggerGlobalState;
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
	try {
		globalThis.localStorage?.setItem(DEBUG_STORAGE_KEY, String(enabled));
	} catch {
		// Ignore storage failures; in-memory flag still applies for this runtime.
	}
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
	try {
		globalThis.localStorage?.setItem(INLINE_DEBUG_ARGS_STORAGE_KEY, String(enabled));
	} catch {
		// Ignore storage failures; in-memory flag still applies for this runtime.
	}
}

function shouldPrintToConsole(level: LogLevel): boolean {
	if (level === 'always' || level === 'warn' || level === 'error') {
		return true;
	}
	return isDebugLoggingEnabled();
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

function emit(level: LogLevel, scope: string, args: unknown[], inlineSerialize = false): void {
	pushRecentLog(level, scope, args);
	if (!shouldPrintToConsole(level)) {
		return;
	}

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

export function createLogger(scope: string): Logger {
	return {
		always: (...args: unknown[]) => emit('always', scope, args),
		info: (...args: unknown[]) => emit('info', scope, args),
		debug: (...args: unknown[]) => emit('debug', scope, args, isInlineSerializedDebugLogArgsEnabled()),
		warn: (...args: unknown[]) => emit('warn', scope, args),
		error: (...args: unknown[]) => emit('error', scope, args),
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

export function createThrottledDebugLogger(intervalMs: number): (logger: Logger, message: string, payload?: unknown) => void {
	let lastLoggedAt = 0;
	return (logger, message, payload) => {
		const now = Date.now();
		if (now - lastLoggedAt < intervalMs) {
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
