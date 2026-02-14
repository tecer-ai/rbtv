import type { NormalizedGatewayPayload } from "../integration/nanobot-gateway-bridge";

export type AllowlistErrorCode =
  | "MISSING_IDENTITY"
  | "INVALID_ALLOWLIST_CONFIG"
  | "UNAUTHORIZED";

export interface AllowlistError {
  code: AllowlistErrorCode;
  message: string;
  retryable: boolean;
}

export type AllowlistGateResult =
  | {
      ok: true;
      data: {
        userId: string;
        sessionKey: string;
      };
      meta: {
        mode: "allowlist";
      };
    }
  | {
      ok: false;
      error: AllowlistError;
      meta: {
        userId?: string;
        sessionKey?: string;
        mode: "allowlist";
      };
    };

export interface AllowlistGateInput {
  payload: Pick<NormalizedGatewayPayload, "userId" | "sessionKey">;
  allowlistedUserIds: readonly string[];
}

export function enforceAllowlistGate(input: AllowlistGateInput): AllowlistGateResult {
  const allowlist = normalizeAllowlist(input.allowlistedUserIds);
  if (allowlist.length === 0) {
    return {
      ok: false,
      error: {
        code: "INVALID_ALLOWLIST_CONFIG",
        message: "Allowlist is empty or invalid; deny by default.",
        retryable: false,
      },
      meta: {
        mode: "allowlist",
        sessionKey: input.payload.sessionKey,
      },
    };
  }

  const userId = normalizeIdentity(input.payload.userId);
  if (!userId) {
    return {
      ok: false,
      error: {
        code: "MISSING_IDENTITY",
        message: "Missing or invalid user identity; deny by default.",
        retryable: false,
      },
      meta: {
        mode: "allowlist",
        sessionKey: input.payload.sessionKey,
      },
    };
  }

  if (!allowlist.includes(userId)) {
    return {
      ok: false,
      error: {
        code: "UNAUTHORIZED",
        message: "User is not allowlisted.",
        retryable: false,
      },
      meta: {
        mode: "allowlist",
        userId,
        sessionKey: input.payload.sessionKey,
      },
    };
  }

  return {
    ok: true,
    data: {
      userId,
      sessionKey: input.payload.sessionKey,
    },
    meta: {
      mode: "allowlist",
    },
  };
}

export function parseAllowlist(raw: string): string[] {
  return normalizeAllowlist(raw.split(","));
}

function normalizeAllowlist(userIds: readonly string[]): string[] {
  const unique = new Set<string>();
  for (const value of userIds) {
    const normalized = normalizeIdentity(value);
    if (normalized) {
      unique.add(normalized);
    }
  }
  return Array.from(unique);
}

function normalizeIdentity(identity: string | undefined): string | undefined {
  if (!identity) {
    return undefined;
  }
  const normalized = identity.trim();
  return normalized.length > 0 ? normalized : undefined;
}
