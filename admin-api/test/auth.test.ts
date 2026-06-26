import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  devHeaderAuthenticator,
  easyAuthAuthenticator,
  resolveAuthenticator,
} from "../src/auth.js";
import { ApiError } from "../src/service.js";

interface EasyAuthClaim {
  readonly typ: string;
  readonly val: string;
}

function easyAuthHeader(
  claims: readonly EasyAuthClaim[],
  roleTyp = "roles",
): Map<string, string> {
  const principal = {
    auth_typ: "aad",
    name_typ: "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
    role_typ: roleTyp,
    claims,
  };
  const encoded = Buffer.from(JSON.stringify(principal), "utf8").toString("base64");
  return new Map([["x-ms-client-principal", encoded]]);
}

const OID = "http://schemas.microsoft.com/identity/claims/objectidentifier";

describe("easyAuthAuthenticator", () => {
  it("resolves principal id, display name, and roles from X-MS-CLIENT-PRINCIPAL", () => {
    const principal = easyAuthAuthenticator(
      easyAuthHeader([
        { typ: OID, val: "oid-123" },
        { typ: "name", val: "Alice Example" },
        { typ: "roles", val: "approver" },
        { typ: "roles", val: "reviewer" },
      ]),
    );

    assert.equal(principal.principalId, "oid-123");
    assert.equal(principal.displayName, "Alice Example");
    assert.deepEqual([...principal.roles].sort(), ["approver", "reviewer"]);
  });

  it("drops Entra role values that do not map to an admin role", () => {
    const principal = easyAuthAuthenticator(
      easyAuthHeader([
        { typ: OID, val: "oid-1" },
        { typ: "roles", val: "approver" },
        { typ: "roles", val: "Some.Unknown.Role" },
      ]),
    );

    assert.deepEqual(principal.roles, ["approver"]);
  });

  it("falls back to the x-ms-client-principal-id header when oid claim is absent", () => {
    const headers = easyAuthHeader([{ typ: "roles", val: "viewer" }]);
    headers.set("x-ms-client-principal-id", "header-oid-9");

    const principal = easyAuthAuthenticator(headers);

    assert.equal(principal.principalId, "header-oid-9");
    assert.deepEqual(principal.roles, ["viewer"]);
  });

  it("rejects requests without an EasyAuth principal header (401)", () => {
    assert.throws(
      () => easyAuthAuthenticator(new Map()),
      (error: unknown) => error instanceof ApiError && error.status === 401,
    );
  });

  it("rejects a malformed EasyAuth principal header as unauthenticated (401, not 500)", () => {
    assert.throws(
      () => easyAuthAuthenticator(new Map([["x-ms-client-principal", "not-valid-base64-json"]])),
      (error: unknown) => error instanceof ApiError && error.status === 401,
    );
  });

  it("rejects an authenticated principal that maps to no admin role (403)", () => {
    assert.throws(
      () =>
        easyAuthAuthenticator(
          easyAuthHeader([
            { typ: OID, val: "oid-2" },
            { typ: "roles", val: "Unmapped.Role" },
          ]),
        ),
      (error: unknown) => error instanceof ApiError && error.status === 403,
    );
  });

  it("resolves principal id from short oid claim type", () => {
    const principal = easyAuthAuthenticator(
      easyAuthHeader([
        { typ: "oid", val: "short-oid-1" },
        { typ: "roles", val: "viewer" },
      ]),
    );

    assert.equal(principal.principalId, "short-oid-1");
  });

  it("uses role_typ field from EasyAuth payload to resolve roles", () => {
    const CUSTOM_ROLE_TYPE = "http://schemas.microsoft.com/ws/2008/06/identity/claims/role";
    const principal = easyAuthAuthenticator(
      easyAuthHeader(
        [
          { typ: OID, val: "oid-custom" },
          { typ: CUSTOM_ROLE_TYPE, val: "reviewer" },
        ],
        CUSTOM_ROLE_TYPE,
      ),
    );

    assert.deepEqual(principal.roles, ["reviewer"]);
  });
});

describe("resolveAuthenticator", () => {
  it("defaults to EasyAuth when no auth mode is configured", () => {
    const authenticate = resolveAuthenticator({});
    assert.throws(
      () => authenticate(new Map()),
      (error: unknown) => error instanceof ApiError && error.status === 401,
    );
  });

  it("uses dev header auth when explicitly enabled outside production", () => {
    const authenticate = resolveAuthenticator({ ADMIN_AUTH_MODE: "dev", NODE_ENV: "test" });
    const principal = authenticate(
      new Map([
        ["x-spautopost-user", "dev-user"],
        ["x-spautopost-roles", "reviewer"],
      ]),
    );
    assert.equal(principal.principalId, "dev-user");
    assert.deepEqual(principal.roles, ["reviewer"]);
  });

  it("fails closed when dev auth is requested with NODE_ENV=production", () => {
    assert.throws(() => resolveAuthenticator({ ADMIN_AUTH_MODE: "dev", NODE_ENV: "production" }));
  });

  it("rejects an unknown auth mode", () => {
    assert.throws(() => resolveAuthenticator({ ADMIN_AUTH_MODE: "magic" }));
  });

  it("exposes the dev header authenticator for skeleton compatibility", () => {
    const principal = devHeaderAuthenticator(
      new Map([
        ["x-spautopost-user", "u1"],
        ["x-spautopost-roles", "admin"],
      ]),
    );
    assert.equal(principal.principalId, "u1");
    assert.deepEqual(principal.roles, ["admin"]);
  });
});
