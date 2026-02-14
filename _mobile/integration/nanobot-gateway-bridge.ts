import { routeCanonicalCommand } from "../routing/command-router";
import { enforceAllowlistGate, parseAllowlist } from "../security/allowlist-gate";
import { readProjectMemo, type ProjectMemoState } from "../state/project-memo-adapter";

export type CanonicalCommand = "mentor" | "domcobb" | "doc";

export type BridgeErrorCode =
  | "MALFORMED_PAYLOAD"
  | "MISSING_TEXT"
  | "MISSING_USER_ID"
  | "MISSING_CHANNEL_ID";

export interface BridgeError {
  code: BridgeErrorCode;
  message: string;
  retryable: boolean;
}

export type BridgeResult =
  | {
      ok: true;
      data: NormalizedGatewayPayload;
      meta: {
        receivedAt: string;
      };
    }
  | {
      ok: false;
      error: BridgeError;
      meta: {
        receivedAt: string;
      };
    };

export interface NormalizedGatewayPayload {
  sessionKey: string;
  userId: string;
  channelId: string;
  chatId: string;
  text: string;
  commandToken: string;
  canonicalCommand?: CanonicalCommand;
  rawPayload: unknown;
}

interface RawGatewayPayload {
  text?: unknown;
  user?: unknown;
  userId?: unknown;
  channel?: unknown;
  channelId?: unknown;
  chatId?: unknown;
}

const SUPPORTED_COMMANDS: readonly CanonicalCommand[] = [
  "mentor",
  "domcobb",
  "doc",
];

type GatewayBootstrapStage = "bridge" | "allowlist" | "router" | "state";

export interface GatewayHarnessConfig {
  memoPath: string;
  allowlistedUserIds?: readonly string[] | string;
}

export type GatewayBootstrapResult =
  | {
      ok: true;
      data: {
        payload: NormalizedGatewayPayload;
        route: {
          command: CanonicalCommand;
          target: {
            agentId: "mentor" | "domcobb" | "ana";
            command: "/bmad-rbtv-mentor" | "/bmad-rbtv-domcobb" | "/bmad-rbtv-doc";
            entrypoint: string;
          };
        };
        memoState: ProjectMemoState;
      };
      meta: {
        receivedAt: string;
        stage: GatewayBootstrapStage;
      };
    }
  | {
      ok: false;
      error: {
        code:
          | BridgeErrorCode
          | "MISSING_IDENTITY"
          | "INVALID_ALLOWLIST_CONFIG"
          | "UNAUTHORIZED"
          | "UNSUPPORTED_COMMAND"
          | "MEMO_NOT_FOUND"
          | "MEMO_IO_ERROR"
          | "MISSING_FRONTMATTER"
          | "MISSING_REQUIRED_FIELD"
          | "INVALID_FIELD_TYPE";
        message: string;
        retryable: boolean;
      };
      meta: {
        receivedAt: string;
        stage: GatewayBootstrapStage;
        sessionKey?: string;
      };
    };

export async function bootstrapGatewayHarness(
  payload: unknown,
  config: GatewayHarnessConfig,
): Promise<GatewayBootstrapResult> {
  const bridgeResult = normalizeNanobotGatewayPayload(payload);
  if (!bridgeResult.ok) {
    return {
      ok: false,
      error: bridgeResult.error,
      meta: {
        receivedAt: bridgeResult.meta.receivedAt,
        stage: "bridge",
      },
    };
  }

  const normalizedPayload = bridgeResult.data;
  const gateResult = enforceAllowlistGate({
    payload: {
      userId: normalizedPayload.userId,
      sessionKey: normalizedPayload.sessionKey,
    },
    allowlistedUserIds: toAllowlistArray(config.allowlistedUserIds),
  });
  if (!gateResult.ok) {
    return {
      ok: false,
      error: gateResult.error,
      meta: {
        receivedAt: bridgeResult.meta.receivedAt,
        stage: "allowlist",
        sessionKey: normalizedPayload.sessionKey,
      },
    };
  }

  const routeResult = routeCanonicalCommand({
    sessionKey: normalizedPayload.sessionKey,
    commandToken: normalizedPayload.commandToken,
    canonicalCommand: normalizedPayload.canonicalCommand,
  });
  if (!routeResult.ok) {
    return {
      ok: false,
      error: routeResult.error,
      meta: {
        receivedAt: bridgeResult.meta.receivedAt,
        stage: "router",
        sessionKey: normalizedPayload.sessionKey,
      },
    };
  }

  // Read canonical workflow state before downstream execution.
  const memoResult = await readProjectMemo(config.memoPath);
  if (!memoResult.ok) {
    return {
      ok: false,
      error: memoResult.error,
      meta: {
        receivedAt: bridgeResult.meta.receivedAt,
        stage: "state",
        sessionKey: normalizedPayload.sessionKey,
      },
    };
  }

  return {
    ok: true,
    data: {
      payload: normalizedPayload,
      route: {
        command: routeResult.data.command,
        target: routeResult.data.target,
      },
      memoState: memoResult.data,
    },
    meta: {
      receivedAt: bridgeResult.meta.receivedAt,
      stage: "state",
    },
  };
}

export function normalizeNanobotGatewayPayload(payload: unknown): BridgeResult {
  const receivedAt = new Date().toISOString();

  if (!isRecord(payload)) {
    return {
      ok: false,
      error: {
        code: "MALFORMED_PAYLOAD",
        message: "Inbound payload must be an object.",
        retryable: false,
      },
      meta: { receivedAt },
    };
  }

  const raw = payload as RawGatewayPayload;
  const userId = readString(raw.userId) ?? readString(raw.user);
  const channelId = readString(raw.channelId) ?? readString(raw.channel);
  const chatId = readString(raw.chatId) ?? channelId;
  const text = normalizeWhitespace(readString(raw.text));

  if (!userId) {
    return {
      ok: false,
      error: {
        code: "MISSING_USER_ID",
        message: "Inbound payload is missing user identity.",
        retryable: false,
      },
      meta: { receivedAt },
    };
  }

  if (!channelId) {
    return {
      ok: false,
      error: {
        code: "MISSING_CHANNEL_ID",
        message: "Inbound payload is missing channel identity.",
        retryable: false,
      },
      meta: { receivedAt },
    };
  }

  if (!text) {
    return {
      ok: false,
      error: {
        code: "MISSING_TEXT",
        message: "Inbound payload is missing command text.",
        retryable: false,
      },
      meta: { receivedAt },
    };
  }

  const commandToken = extractCommandToken(text);
  const canonicalCommand = toCanonicalCommand(commandToken);

  return {
    ok: true,
    data: {
      sessionKey: toSessionKey(channelId, chatId),
      userId,
      channelId,
      chatId,
      text,
      commandToken,
      canonicalCommand,
      rawPayload: payload,
    },
    meta: { receivedAt },
  };
}

export function toSessionKey(channelId: string, chatId: string): string {
  return `${channelId}:${chatId}`;
}

function extractCommandToken(text: string): string {
  const firstToken = text.trim().split(/\s+/, 1)[0] ?? "";
  return stripCommandPrefix(firstToken).toLowerCase();
}

function stripCommandPrefix(token: string): string {
  if (token.startsWith("/")) {
    return token.slice(1);
  }
  return token;
}

function toCanonicalCommand(commandToken: string): CanonicalCommand | undefined {
  if (SUPPORTED_COMMANDS.includes(commandToken as CanonicalCommand)) {
    return commandToken as CanonicalCommand;
  }
  return undefined;
}

function normalizeWhitespace(value: string | undefined): string | undefined {
  if (!value) {
    return undefined;
  }
  const normalized = value.trim().replace(/\s+/g, " ");
  return normalized.length > 0 ? normalized : undefined;
}

function readString(value: unknown): string | undefined {
  if (typeof value !== "string") {
    return undefined;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : undefined;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function toAllowlistArray(rawAllowlist: readonly string[] | string | undefined): string[] {
  if (!rawAllowlist) {
    return [];
  }
  if (typeof rawAllowlist === "string") {
    return parseAllowlist(rawAllowlist);
  }
  return rawAllowlist.map((value) => value.trim()).filter((value) => value.length > 0);
}
