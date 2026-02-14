import { promises as fs } from "node:fs";
import * as path from "node:path";

export type MemoErrorCode =
  | "MEMO_NOT_FOUND"
  | "MEMO_IO_ERROR"
  | "MISSING_FRONTMATTER"
  | "MISSING_REQUIRED_FIELD"
  | "INVALID_FIELD_TYPE";

export interface MemoError {
  code: MemoErrorCode;
  message: string;
  retryable: boolean;
  details?: Record<string, unknown>;
}

export interface ProjectMemoState {
  projectName: string;
  currentMilestone: string;
  currentFramework: string;
  stepsCompleted: string[];
  lastUpdated?: string;
  extraFrontmatter: Record<string, MemoFrontmatterValue>;
}

export type MemoFrontmatterValue = string | string[];

export type MemoAdapterResult<T> =
  | {
      ok: true;
      data: T;
      meta: { updatedAt: string };
    }
  | {
      ok: false;
      error: MemoError;
      meta: { updatedAt: string };
    };

export type ProjectMemoPatch = Partial<
  Pick<
    ProjectMemoState,
    "projectName" | "currentMilestone" | "currentFramework" | "stepsCompleted" | "lastUpdated"
  >
>;

const REQUIRED_KEYS = [
  "projectName",
  "currentMilestone",
  "currentFramework",
  "stepsCompleted",
] as const;

const CANONICAL_KEY_ORDER = [
  "projectName",
  "currentMilestone",
  "currentFramework",
  "stepsCompleted",
  "lastUpdated",
] as const;

export async function readProjectMemo(
  memoPath: string,
): Promise<MemoAdapterResult<ProjectMemoState>> {
  const now = new Date().toISOString();
  const readResult = await readMemoFile(memoPath);
  if (!readResult.ok) {
    return { ...readResult, meta: { updatedAt: now } };
  }

  const parsed = parseMemoContent(readResult.data);
  if (!parsed.ok) {
    return { ...parsed, meta: { updatedAt: now } };
  }

  return {
    ok: true,
    data: parsed.data.memoState,
    meta: { updatedAt: now },
  };
}

export async function updateProjectMemo(
  memoPath: string,
  patch: ProjectMemoPatch,
): Promise<MemoAdapterResult<ProjectMemoState>> {
  const now = new Date().toISOString();
  const readResult = await readMemoFile(memoPath);
  if (!readResult.ok) {
    return { ...readResult, meta: { updatedAt: now } };
  }

  const parsed = parseMemoContent(readResult.data);
  if (!parsed.ok) {
    return { ...parsed, meta: { updatedAt: now } };
  }

  const mergedFrontmatter: Record<string, MemoFrontmatterValue> = {
    ...parsed.data.frontmatterMap,
    ...normalizePatch(patch),
  };

  if (!Object.prototype.hasOwnProperty.call(mergedFrontmatter, "lastUpdated")) {
    mergedFrontmatter.lastUpdated = now.slice(0, 10);
  }

  const stateResult = toMemoState(mergedFrontmatter);
  if (!stateResult.ok) {
    return { ...stateResult, meta: { updatedAt: now } };
  }

  const updatedContent = buildMemoContent({
    frontmatterMap: mergedFrontmatter,
    body: parsed.data.body,
  });

  const writeResult = await writeFileAtomic(memoPath, updatedContent);
  if (!writeResult.ok) {
    return { ...writeResult, meta: { updatedAt: now } };
  }

  return {
    ok: true,
    data: stateResult.data,
    meta: { updatedAt: now },
  };
}

function normalizePatch(patch: ProjectMemoPatch): Record<string, MemoFrontmatterValue> {
  const normalized: Record<string, MemoFrontmatterValue> = {};

  if (patch.projectName !== undefined) {
    normalized.projectName = patch.projectName;
  }
  if (patch.currentMilestone !== undefined) {
    normalized.currentMilestone = patch.currentMilestone;
  }
  if (patch.currentFramework !== undefined) {
    normalized.currentFramework = patch.currentFramework;
  }
  if (patch.stepsCompleted !== undefined) {
    normalized.stepsCompleted = patch.stepsCompleted;
  }
  if (patch.lastUpdated !== undefined) {
    normalized.lastUpdated = patch.lastUpdated;
  }

  return normalized;
}

async function readMemoFile(memoPath: string): Promise<MemoAdapterResult<string>> {
  const now = new Date().toISOString();

  try {
    const content = await fs.readFile(memoPath, "utf8");
    return { ok: true, data: content, meta: { updatedAt: now } };
  } catch (error) {
    const isNotFound = isNodeError(error) && error.code === "ENOENT";
    return {
      ok: false,
      error: {
        code: isNotFound ? "MEMO_NOT_FOUND" : "MEMO_IO_ERROR",
        message: isNotFound
          ? `project-memo file not found at '${memoPath}'.`
          : `Unable to read project-memo file at '${memoPath}'.`,
        retryable: !isNotFound,
        details: isNodeError(error) ? { cause: error.message } : undefined,
      },
      meta: { updatedAt: now },
    };
  }
}

function parseMemoContent(
  content: string,
): MemoAdapterResult<{
  frontmatterMap: Record<string, MemoFrontmatterValue>;
  memoState: ProjectMemoState;
  body: string;
}> {
  const now = new Date().toISOString();
  const match = content.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$/);

  if (!match) {
    return {
      ok: false,
      error: {
        code: "MISSING_FRONTMATTER",
        message: "project-memo is missing YAML frontmatter delimiters.",
        retryable: false,
      },
      meta: { updatedAt: now },
    };
  }

  const [, rawFrontmatter, body] = match;
  const frontmatterMap = parseFrontmatterMap(rawFrontmatter);
  const stateResult = toMemoState(frontmatterMap);

  if (!stateResult.ok) {
    return { ...stateResult, meta: { updatedAt: now } };
  }

  return {
    ok: true,
    data: {
      frontmatterMap,
      memoState: stateResult.data,
      body,
    },
    meta: { updatedAt: now },
  };
}

function toMemoState(
  frontmatterMap: Record<string, MemoFrontmatterValue>,
): MemoAdapterResult<ProjectMemoState> {
  const now = new Date().toISOString();

  for (const key of REQUIRED_KEYS) {
    if (!Object.prototype.hasOwnProperty.call(frontmatterMap, key)) {
      return {
        ok: false,
        error: {
          code: "MISSING_REQUIRED_FIELD",
          message: `project-memo frontmatter is missing required field '${key}'.`,
          retryable: false,
        },
        meta: { updatedAt: now },
      };
    }
  }

  const projectName = readRequiredString(frontmatterMap.projectName, "projectName");
  if (!projectName.ok) {
    return { ...projectName, meta: { updatedAt: now } };
  }

  const currentMilestone = readRequiredString(
    frontmatterMap.currentMilestone,
    "currentMilestone",
  );
  if (!currentMilestone.ok) {
    return { ...currentMilestone, meta: { updatedAt: now } };
  }

  const currentFramework = readRequiredString(
    frontmatterMap.currentFramework,
    "currentFramework",
  );
  if (!currentFramework.ok) {
    return { ...currentFramework, meta: { updatedAt: now } };
  }

  const stepsCompleted = readRequiredStringArray(
    frontmatterMap.stepsCompleted,
    "stepsCompleted",
  );
  if (!stepsCompleted.ok) {
    return { ...stepsCompleted, meta: { updatedAt: now } };
  }

  let lastUpdated: string | undefined;
  if (frontmatterMap.lastUpdated !== undefined) {
    const readLastUpdated = readRequiredString(frontmatterMap.lastUpdated, "lastUpdated");
    if (!readLastUpdated.ok) {
      return { ...readLastUpdated, meta: { updatedAt: now } };
    }
    lastUpdated = readLastUpdated.data;
  }

  const extraFrontmatter: Record<string, MemoFrontmatterValue> = {};
  for (const [key, value] of Object.entries(frontmatterMap)) {
    if (!CANONICAL_KEY_ORDER.includes(key as (typeof CANONICAL_KEY_ORDER)[number])) {
      extraFrontmatter[key] = value;
    }
  }

  return {
    ok: true,
    data: {
      projectName: projectName.data,
      currentMilestone: currentMilestone.data,
      currentFramework: currentFramework.data,
      stepsCompleted: stepsCompleted.data,
      lastUpdated,
      extraFrontmatter,
    },
    meta: { updatedAt: now },
  };
}

function readRequiredString(
  value: MemoFrontmatterValue | undefined,
  fieldName: string,
): MemoAdapterResult<string> {
  const now = new Date().toISOString();

  if (typeof value !== "string" || value.trim().length === 0) {
    return {
      ok: false,
      error: {
        code: "INVALID_FIELD_TYPE",
        message: `project-memo field '${fieldName}' must be a non-empty string.`,
        retryable: false,
      },
      meta: { updatedAt: now },
    };
  }

  return {
    ok: true,
    data: value.trim(),
    meta: { updatedAt: now },
  };
}

function readRequiredStringArray(
  value: MemoFrontmatterValue | undefined,
  fieldName: string,
): MemoAdapterResult<string[]> {
  const now = new Date().toISOString();

  if (!Array.isArray(value)) {
    return {
      ok: false,
      error: {
        code: "INVALID_FIELD_TYPE",
        message: `project-memo field '${fieldName}' must be a string array.`,
        retryable: false,
      },
      meta: { updatedAt: now },
    };
  }

  const cleaned = value.map((entry) => entry.trim()).filter((entry) => entry.length > 0);
  if (cleaned.length !== value.length) {
    return {
      ok: false,
      error: {
        code: "INVALID_FIELD_TYPE",
        message: `project-memo field '${fieldName}' must not contain empty items.`,
        retryable: false,
      },
      meta: { updatedAt: now },
    };
  }

  return {
    ok: true,
    data: cleaned,
    meta: { updatedAt: now },
  };
}

function parseFrontmatterMap(rawFrontmatter: string): Record<string, MemoFrontmatterValue> {
  const map: Record<string, MemoFrontmatterValue> = {};

  for (const rawLine of rawFrontmatter.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (line.length === 0 || line.startsWith("#")) {
      continue;
    }

    const match = line.match(/^([A-Za-z][\w-]*):\s*(.*)$/);
    if (!match) {
      continue;
    }

    const [, key, value] = match;
    map[key] = parseFrontmatterValue(value);
  }

  return map;
}

function parseFrontmatterValue(rawValue: string): MemoFrontmatterValue {
  const value = rawValue.trim();

  if (value.startsWith("[") && value.endsWith("]")) {
    const content = value.slice(1, -1).trim();
    if (content.length === 0) {
      return [];
    }
    return content
      .split(",")
      .map((entry) => unquote(entry.trim()))
      .filter((entry) => entry.length > 0);
  }

  return unquote(value);
}

function buildMemoContent(input: {
  frontmatterMap: Record<string, MemoFrontmatterValue>;
  body: string;
}): string {
  const keys = Object.keys(input.frontmatterMap);
  const canonicalKeys = CANONICAL_KEY_ORDER.filter((key) => keys.includes(key));
  const extraKeys = keys
    .filter((key) => !CANONICAL_KEY_ORDER.includes(key as (typeof CANONICAL_KEY_ORDER)[number]))
    .sort();
  const orderedKeys = [...canonicalKeys, ...extraKeys];

  const frontmatterLines = orderedKeys.map((key) => {
    const value = input.frontmatterMap[key];
    return `${key}: ${serializeFrontmatterValue(value)}`;
  });

  return `---\n${frontmatterLines.join("\n")}\n---\n${input.body}`;
}

function serializeFrontmatterValue(value: MemoFrontmatterValue): string {
  if (Array.isArray(value)) {
    const serializedItems = value.map((item) => `'${escapeSingleQuotes(item)}'`).join(", ");
    return `[${serializedItems}]`;
  }
  return `'${escapeSingleQuotes(value)}'`;
}

async function writeFileAtomic(
  targetPath: string,
  content: string,
): Promise<MemoAdapterResult<true>> {
  const now = new Date().toISOString();
  const tempPath = path.join(
    path.dirname(targetPath),
    `${path.basename(targetPath)}.tmp-${Date.now()}`,
  );

  try {
    await fs.writeFile(tempPath, content, "utf8");
    await fs.rename(tempPath, targetPath);
    return { ok: true, data: true, meta: { updatedAt: now } };
  } catch (error) {
    try {
      await fs.unlink(tempPath);
    } catch {
      // Best effort cleanup only.
    }
    return {
      ok: false,
      error: {
        code: "MEMO_IO_ERROR",
        message: `Failed to atomically write project-memo at '${targetPath}'.`,
        retryable: true,
        details: isNodeError(error) ? { cause: error.message } : undefined,
      },
      meta: { updatedAt: now },
    };
  }
}

function unquote(value: string): string {
  const trimmed = value.trim();
  if (
    (trimmed.startsWith("'") && trimmed.endsWith("'")) ||
    (trimmed.startsWith('"') && trimmed.endsWith('"'))
  ) {
    return trimmed.slice(1, -1);
  }
  return trimmed;
}

function escapeSingleQuotes(value: string): string {
  return value.replace(/'/g, "''");
}

function isNodeError(error: unknown): error is NodeJS.ErrnoException {
  return typeof error === "object" && error !== null && "message" in error;
}
