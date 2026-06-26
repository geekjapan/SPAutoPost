import { createHash, randomUUID } from "node:crypto";
import type {
  AdminApiStore,
  AdminCommandType,
  AdminPrincipal,
  AdminRole,
  NewAdminCommand,
} from "./types.js";

export interface ApiResponse {
  readonly status: number;
  readonly body: Record<string, unknown>;
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

export interface RequestContext {
  readonly principal: AdminPrincipal;
  readonly headers: ReadonlyMap<string, string>;
}

const WRITE_ROLES: Record<AdminCommandType, readonly AdminRole[]> = {
  edit: ["reviewer", "admin"],
  approve: ["approver", "admin"],
  reject: ["reviewer", "approver", "admin"],
  request_regeneration: ["reviewer", "approver", "admin"],
  publish_request: ["publisher", "admin"],
};

const READ_ROLES: readonly AdminRole[] = ["viewer", "reviewer", "approver", "publisher", "admin"];

const SECRET_KEY_FRAGMENTS = [
  "api_key",
  "apikey",
  "access_token",
  "refreshtoken",
  "refresh_token",
  "client_secret",
  "private_key",
  "password",
  "cookie",
  "authorization",
] as const;

export async function listDrafts(
  store: AdminApiStore,
  context: RequestContext,
  params: { readonly limit?: number; readonly offset?: number },
): Promise<ApiResponse> {
  requireRole(context.principal, READ_ROLES);
  const limit = normalizePageNumber(params.limit, 100, 1, 200);
  const offset = normalizePageNumber(params.offset, 0, 0, 100_000);
  const drafts = await store.listDrafts({ limit, offset });
  return { status: 200, body: { data: drafts, pagination: { limit, offset } } };
}

export async function getDraft(
  store: AdminApiStore,
  context: RequestContext,
  draftId: string,
): Promise<ApiResponse> {
  requireRole(context.principal, READ_ROLES);
  const draft = await store.getDraft(draftId);
  if (!draft) {
    throw new ApiError(404, "draft_not_found", `DraftPost ${draftId} was not found`);
  }
  const [reviewEvents, auditEvents] = await Promise.all([
    store.listReviewEvents(draftId),
    store.listAuditEvents(draftId),
  ]);
  return { status: 200, body: { data: { draft, reviewEvents, auditEvents } } };
}

export async function listAuditEvents(
  store: AdminApiStore,
  context: RequestContext,
  draftId: string,
): Promise<ApiResponse> {
  requireRole(context.principal, READ_ROLES);
  const auditEvents = await store.listAuditEvents(draftId);
  return { status: 200, body: { data: auditEvents } };
}

export async function getCommandStatus(
  store: AdminApiStore,
  context: RequestContext,
  commandId: string,
): Promise<ApiResponse> {
  requireRole(context.principal, READ_ROLES);
  const command = await store.getCommand(commandId);
  if (!command) {
    throw new ApiError(404, "command_not_found", `AdminCommand ${commandId} was not found`);
  }
  return {
    status: 200,
    body: {
      data: {
        commandId: command.commandId,
        status: command.status,
        errorCode: command.errorCode,
        errorMessage: command.errorMessage,
        processedAt: command.processedAt,
      },
    },
  };
}

export async function enqueueDraftCommand(
  store: AdminApiStore,
  context: RequestContext,
  input: {
    readonly draftId: string;
    readonly commandType: AdminCommandType;
    readonly payload: Record<string, unknown>;
  },
): Promise<ApiResponse> {
  requireRole(context.principal, WRITE_ROLES[input.commandType]);
  rejectSecretPayload(input.payload);
  const clientKey = requireIdempotencyKey(context.headers);
  const correlationId = context.headers.get("x-correlation-id") ?? randomUUID();
  const command: NewAdminCommand = {
    commandId: randomUUID(),
    commandType: input.commandType,
    targetDraftId: input.draftId,
    requestedBy: context.principal.principalId,
    payload: input.payload,
    idempotencyKey: scopedIdempotencyKey(
      context.principal.principalId,
      input.draftId,
      input.commandType,
      clientKey,
    ),
    correlationId,
    createdAt: new Date().toISOString(),
  };
  const result = await store.enqueueCommand(command);
  return {
    status: 202,
    body: {
      data: {
        accepted: true,
        deduplicated: !result.created,
        command: result.command,
        statusUrl: `/api/commands/${result.command.commandId}`,
      },
    },
  };
}

export function parsePrincipal(headers: ReadonlyMap<string, string>): AdminPrincipal {
  const principalId = headers.get("x-spautopost-user")?.trim();
  if (!principalId) {
    throw new ApiError(401, "missing_admin_principal", "Admin principal header is required");
  }
  const roles = parseRoles(headers.get("x-spautopost-roles"));
  if (roles.length === 0) {
    throw new ApiError(403, "missing_admin_role", "At least one admin role is required");
  }
  return {
    principalId,
    displayName: headers.get("x-spautopost-display-name")?.trim() || undefined,
    roles,
  };
}

export function normalizeHeaders(headers: Record<string, string | string[] | undefined>): Map<string, string> {
  const normalized = new Map<string, string>();
  for (const [key, value] of Object.entries(headers)) {
    if (typeof value === "string") {
      normalized.set(key.toLowerCase(), value);
    } else if (Array.isArray(value)) {
      const joined = value.filter((item): item is string => typeof item === "string").join(",");
      normalized.set(key.toLowerCase(), joined);
    }
  }
  return normalized;
}

function normalizePageNumber(
  raw: number | undefined,
  fallback: number,
  min: number,
  max: number,
): number {
  if (raw === undefined) {
    return fallback;
  }
  if (!Number.isInteger(raw) || raw < min || raw > max) {
    throw new ApiError(400, "invalid_pagination", `Pagination value must be ${min}..${max}`);
  }
  return raw;
}

function requireRole(principal: AdminPrincipal, allowed: readonly AdminRole[]): void {
  if (principal.roles.some((role) => allowed.includes(role))) {
    return;
  }
  throw new ApiError(403, "insufficient_role", `Required role: ${allowed.join(" or ")}`);
}

function rejectSecretPayload(payload: Record<string, unknown>): void {
  if (containsSecretKey(payload)) {
    throw new ApiError(
      400,
      "secret_payload_key",
      "AdminCommand payload must not contain secret-looking keys",
    );
  }
}

function containsSecretKey(value: unknown): boolean {
  if (Array.isArray(value)) {
    return value.some(containsSecretKey);
  }
  if (typeof value !== "object" || value === null) {
    return false;
  }
  return Object.entries(value).some(([key, nested]) => {
    const normalized = key.toLowerCase().replaceAll("-", "_");
    return SECRET_KEY_FRAGMENTS.some((fragment) => normalized.includes(fragment))
      || containsSecretKey(nested);
  });
}

function requireIdempotencyKey(headers: ReadonlyMap<string, string>): string {
  const key = headers.get("idempotency-key")?.trim();
  if (!key) {
    throw new ApiError(
      400,
      "missing_idempotency_key",
      "State-changing Admin API requests require an Idempotency-Key header",
    );
  }
  if (key.length > 200) {
    throw new ApiError(400, "invalid_idempotency_key", "Idempotency-Key is too long");
  }
  return key;
}

function scopedIdempotencyKey(
  principalId: string,
  draftId: string,
  commandType: AdminCommandType,
  clientKey: string,
): string {
  const digest = createHash("sha256")
    .update(JSON.stringify([principalId, draftId, commandType, clientKey]))
    .digest("hex");
  return `admin-api:${digest}`;
}

function parseRoles(raw: string | undefined): readonly AdminRole[] {
  if (!raw) {
    return [];
  }
  const roles = new Set<AdminRole>();
  for (const value of raw.split(",")) {
    const role = value.trim();
    if (isAdminRole(role)) {
      roles.add(role);
    }
  }
  return [...roles];
}

export function isAdminRole(value: string): value is AdminRole {
  return ["viewer", "reviewer", "approver", "publisher", "admin"].includes(value);
}
