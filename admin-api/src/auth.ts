import { ApiError, isAdminRole, parsePrincipal } from "./service.js";
import type { AdminPrincipal, AdminRole } from "./types.js";

export type Authenticator = (headers: ReadonlyMap<string, string>) => AdminPrincipal;

export type AuthMode = "easyauth" | "dev";

const EASYAUTH_PRINCIPAL_HEADER = "x-ms-client-principal";
const EASYAUTH_ID_HEADER = "x-ms-client-principal-id";
const OID_CLAIM_TYPES = [
  "http://schemas.microsoft.com/identity/claims/objectidentifier",
  "oid",
] as const;
const DISPLAY_NAME_CLAIM_TYPE = "name";
const DEFAULT_ROLE_CLAIM_TYPE = "roles";

interface EasyAuthClaim {
  readonly typ: string;
  readonly val: string;
}

interface EasyAuthPrincipal {
  readonly roleClaimType: string;
  readonly claims: readonly EasyAuthClaim[];
}

/**
 * Trusts the principal injected by Azure Container Apps Authentication (EasyAuth).
 * The platform performs the Entra ID OIDC flow; this only parses the asserted
 * principal. Never validates tokens or holds secrets (Option A).
 */
export function easyAuthAuthenticator(headers: ReadonlyMap<string, string>): AdminPrincipal {
  const principal = decodeEasyAuthPrincipal(headers.get(EASYAUTH_PRINCIPAL_HEADER));
  const claims = principal?.claims ?? [];

  const principalId =
    firstClaimValue(claims, OID_CLAIM_TYPES) ?? headers.get(EASYAUTH_ID_HEADER)?.trim();
  if (!principalId) {
    throw new ApiError(
      401,
      "missing_admin_principal",
      "Entra ID authenticated principal is required",
    );
  }

  const roleClaimType = principal?.roleClaimType ?? DEFAULT_ROLE_CLAIM_TYPE;
  const roles = toAdminRoles(
    claims.filter((claim) => claim.typ === roleClaimType).map((claim) => claim.val),
  );
  if (roles.length === 0) {
    throw new ApiError(403, "missing_admin_role", "At least one mapped admin role is required");
  }

  const displayName = firstClaimValue(claims, [DISPLAY_NAME_CLAIM_TYPE]);
  return {
    principalId,
    displayName: displayName || undefined,
    roles,
  };
}

/** Dev-only principal injection via explicit headers. Never enabled by default. */
export const devHeaderAuthenticator: Authenticator = parsePrincipal;

/**
 * Resolves the active authenticator. Default (unset) is the production-safe
 * EasyAuth path; the dev header bypass must be opted into explicitly and fails
 * closed when NODE_ENV=production so it can never run in production.
 */
export function resolveAuthenticator(env: Record<string, string | undefined> = process.env): Authenticator {
  const mode = env.ADMIN_AUTH_MODE?.trim() || "easyauth";
  if (mode === "easyauth") {
    return easyAuthAuthenticator;
  }
  if (mode === "dev") {
    if ((env.NODE_ENV ?? "").trim() === "production") {
      throw new Error(
        "ADMIN_AUTH_MODE=dev must not be used with NODE_ENV=production (dev auth bypass is disabled in production)",
      );
    }
    return devHeaderAuthenticator;
  }
  throw new Error(`Unknown ADMIN_AUTH_MODE: ${mode} (expected "easyauth" or "dev")`);
}

function decodeEasyAuthPrincipal(raw: string | undefined): EasyAuthPrincipal | undefined {
  if (!raw) {
    return undefined;
  }
  try {
    const json = Buffer.from(raw, "base64").toString("utf8");
    const parsed: unknown = JSON.parse(json);
    if (typeof parsed !== "object" || parsed === null) {
      return undefined;
    }
    const record = parsed as Record<string, unknown>;
    const roleClaimType =
      typeof record.role_typ === "string" && record.role_typ.trim()
        ? record.role_typ.trim()
        : DEFAULT_ROLE_CLAIM_TYPE;
    return { roleClaimType, claims: parseClaims(record.claims) };
  } catch {
    return undefined;
  }
}

function parseClaims(raw: unknown): readonly EasyAuthClaim[] {
  if (!Array.isArray(raw)) {
    return [];
  }
  const claims: EasyAuthClaim[] = [];
  for (const entry of raw) {
    if (typeof entry !== "object" || entry === null) {
      continue;
    }
    const { typ, val } = entry as Record<string, unknown>;
    if (typeof typ === "string" && typeof val === "string") {
      claims.push({ typ, val });
    }
  }
  return claims;
}

function firstClaimValue(
  claims: readonly EasyAuthClaim[],
  types: readonly string[],
): string | undefined {
  for (const type of types) {
    const match = claims.find((claim) => claim.typ === type)?.val.trim();
    if (match) {
      return match;
    }
  }
  return undefined;
}

function toAdminRoles(values: readonly string[]): readonly AdminRole[] {
  const roles = new Set<AdminRole>();
  for (const value of values) {
    const role = value.trim();
    if (isAdminRole(role)) {
      roles.add(role);
    }
  }
  return [...roles];
}
