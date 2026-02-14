import type {
  CanonicalCommand,
  NormalizedGatewayPayload,
} from "../integration/nanobot-gateway-bridge";

export interface RouteTarget {
  agentId: "mentor" | "domcobb" | "ana";
  command: "/bmad-rbtv-mentor" | "/bmad-rbtv-domcobb" | "/bmad-rbtv-doc";
  entrypoint: string;
}

export type RouterErrorCode = "UNSUPPORTED_COMMAND";

export interface RouterError {
  code: RouterErrorCode;
  message: string;
  retryable: false;
}

export type RouterResult =
  | {
      ok: true;
      data: {
        sessionKey: string;
        command: CanonicalCommand;
        target: RouteTarget;
      };
      meta: {
        allowedCommands: readonly CanonicalCommand[];
      };
    }
  | {
      ok: false;
      error: RouterError;
      meta: {
        sessionKey: string;
        commandToken: string;
        allowedCommands: readonly CanonicalCommand[];
      };
    };

const ROUTE_TABLE: Record<CanonicalCommand, RouteTarget> = {
  mentor: {
    agentId: "mentor",
    command: "/bmad-rbtv-mentor",
    entrypoint: "_bmad/rbtv/agents/mentor.md",
  },
  domcobb: {
    agentId: "domcobb",
    command: "/bmad-rbtv-domcobb",
    entrypoint: "_bmad/rbtv/agents/domcobb.md",
  },
  doc: {
    agentId: "ana",
    command: "/bmad-rbtv-doc",
    entrypoint: "_bmad/rbtv/agents/ana.md",
  },
};

const ALLOWED_COMMANDS = Object.freeze(
  Object.keys(ROUTE_TABLE) as CanonicalCommand[],
);

export function routeCanonicalCommand(
  payload: Pick<
    NormalizedGatewayPayload,
    "sessionKey" | "commandToken" | "canonicalCommand"
  >,
): RouterResult {
  const { canonicalCommand, commandToken, sessionKey } = payload;

  if (!canonicalCommand) {
    return {
      ok: false,
      error: {
        code: "UNSUPPORTED_COMMAND",
        message: formatUnsupportedCommandMessage(commandToken),
        retryable: false,
      },
      meta: {
        sessionKey,
        commandToken,
        allowedCommands: ALLOWED_COMMANDS,
      },
    };
  }

  return {
    ok: true,
    data: {
      sessionKey,
      command: canonicalCommand,
      target: ROUTE_TABLE[canonicalCommand],
    },
    meta: {
      allowedCommands: ALLOWED_COMMANDS,
    },
  };
}

function formatUnsupportedCommandMessage(commandToken: string): string {
  return `Unsupported command '${commandToken}'. Allowed commands: ${ALLOWED_COMMANDS.join(", ")}.`;
}
