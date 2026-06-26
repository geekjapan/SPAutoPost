import type { IncomingMessage, ServerResponse } from "node:http";
import {
  ApiError,
  enqueueDraftCommand,
  getCommandStatus,
  getDraft,
  listAuditEvents,
  listDrafts,
  normalizeHeaders,
  parsePrincipal,
  type ApiResponse,
} from "./service.js";
import type { AdminApiStore, AdminCommandType } from "./types.js";

const MAX_JSON_BODY_BYTES = 1_048_576;

export interface HttpRequest {
  readonly method: string;
  readonly path: string;
  readonly query?: ReadonlyMap<string, string>;
  readonly headers: ReadonlyMap<string, string>;
  readonly body?: unknown;
}

export async function handleAdminApiRequest(
  store: AdminApiStore,
  request: HttpRequest,
): Promise<ApiResponse> {
  try {
    if (request.method === "GET" && request.path === "/api/drafts") {
      return await listDrafts(store, contextFrom(request), pageParams(request.query));
    }

    const commandMatch = matchCommandPath(request.path);
    if (request.method === "GET" && commandMatch) {
      return await getCommandStatus(store, contextFrom(request), commandMatch.commandId);
    }

    const auditMatch = matchDraftAuditPath(request.path);
    if (request.method === "GET" && auditMatch) {
      return await listAuditEvents(store, contextFrom(request), auditMatch.draftId);
    }

    const draftMatch = matchDraftPath(request.path);
    if (request.method === "GET" && draftMatch) {
      return await getDraft(store, contextFrom(request), draftMatch.draftId);
    }

    if (request.method === "PATCH" && draftMatch) {
      return await enqueueDraftCommand(store, contextFrom(request), {
        draftId: draftMatch.draftId,
        commandType: "edit",
        payload: objectBody(request.body),
      });
    }

    const actionMatch = matchDraftActionPath(request.path);
    if (request.method === "POST" && actionMatch) {
      return await enqueueDraftCommand(store, contextFrom(request), {
        draftId: actionMatch.draftId,
        commandType: commandTypeFromRoute(actionMatch.action),
        payload: objectBody(request.body),
      });
    }

    throw new ApiError(404, "route_not_found", `Route ${request.method} ${request.path} not found`);
  } catch (error) {
    return errorResponse(error);
  }
}

export function createNodeHandler(store: AdminApiStore) {
  return async (request: IncomingMessage, response: ServerResponse): Promise<void> => {
    const url = new URL(request.url ?? "/", "http://localhost");
    const apiResponse = await responseForNodeRequest(store, request, url);
    response.writeHead(apiResponse.status, { "content-type": "application/json; charset=utf-8" });
    response.end(JSON.stringify(apiResponse.body));
  };
}

async function responseForNodeRequest(
  store: AdminApiStore,
  request: IncomingMessage,
  url: URL,
): Promise<ApiResponse> {
  try {
    return await handleAdminApiRequest(store, {
      method: request.method ?? "GET",
      path: url.pathname,
      query: new Map(url.searchParams.entries()),
      headers: normalizeHeaders(request.headers),
      body: await readJsonBody(request),
    });
  } catch (error) {
    return errorResponse(error);
  }
}

function contextFrom(request: HttpRequest) {
  return {
    principal: parsePrincipal(request.headers),
    headers: request.headers,
  };
}

function errorResponse(error: unknown): ApiResponse {
  if (error instanceof ApiError) {
    return {
      status: error.status,
      body: { success: false, error: { code: error.code, message: error.message } },
    };
  }
  return {
    status: 500,
    body: { success: false, error: { code: "internal_error", message: "Internal server error" } },
  };
}

function pageParams(query: ReadonlyMap<string, string> | undefined): {
  readonly limit?: number;
  readonly offset?: number;
} {
  const limit = numberFromQuery(query, "limit");
  const offset = numberFromQuery(query, "offset");
  return {
    ...(limit === undefined ? {} : { limit }),
    ...(offset === undefined ? {} : { offset }),
  };
}

function numberFromQuery(query: ReadonlyMap<string, string> | undefined, key: string): number | undefined {
  const value = query?.get(key)?.trim();
  if (value === undefined || value === "") {
    return undefined;
  }
  const parsed = Number(value);
  return Number.isNaN(parsed) ? undefined : parsed;
}

function matchCommandPath(path: string): { readonly commandId: string } | undefined {
  const match = /^\/api\/commands\/([^/]+)$/u.exec(path);
  const commandId = match?.[1] ? safeDecodeURIComponent(match[1]) : undefined;
  return commandId ? { commandId } : undefined;
}

function matchDraftPath(path: string): { readonly draftId: string } | undefined {
  const match = /^\/api\/drafts\/([^/]+)$/u.exec(path);
  const draftId = match?.[1] ? safeDecodeURIComponent(match[1]) : undefined;
  return draftId ? { draftId } : undefined;
}

function matchDraftAuditPath(path: string): { readonly draftId: string } | undefined {
  const match = /^\/api\/drafts\/([^/]+)\/audit-events$/u.exec(path);
  const draftId = match?.[1] ? safeDecodeURIComponent(match[1]) : undefined;
  return draftId ? { draftId } : undefined;
}

function matchDraftActionPath(
  path: string,
): { readonly draftId: string; readonly action: string } | undefined {
  const match = /^\/api\/drafts\/([^/]+)\/(approve|reject|regenerate|publish-request)$/u.exec(path);
  const draftId = match?.[1] ? safeDecodeURIComponent(match[1]) : undefined;
  const action = match?.[2] ? safeDecodeURIComponent(match[2]) : undefined;
  return draftId && action ? { draftId, action } : undefined;
}

function safeDecodeURIComponent(value: string): string | undefined {
  try {
    return decodeURIComponent(value);
  } catch {
    return undefined;
  }
}

function commandTypeFromRoute(routeValue: string): AdminCommandType {
  if (routeValue === "regenerate") {
    return "request_regeneration";
  }
  if (routeValue === "publish-request") {
    return "publish_request";
  }
  if (routeValue === "approve" || routeValue === "reject") {
    return routeValue;
  }
  throw new ApiError(404, "route_not_found", `Unknown command route ${routeValue}`);
}

function objectBody(body: unknown): Record<string, unknown> {
  if (body === undefined || body === null) {
    return {};
  }
  if (typeof body === "object" && !Array.isArray(body)) {
    return body as Record<string, unknown>;
  }
  throw new ApiError(400, "invalid_json_body", "Request body must be a JSON object");
}

async function readJsonBody(request: IncomingMessage): Promise<unknown> {
  if (request.method === "GET" || request.method === "HEAD") {
    return undefined;
  }
  const chunks: Buffer[] = [];
  let receivedBytes = 0;
  for await (const chunk of request) {
    const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    receivedBytes += buffer.byteLength;
    if (receivedBytes > MAX_JSON_BODY_BYTES) {
      throw new ApiError(413, "request_body_too_large", "Request body must be 1 MiB or smaller");
    }
    chunks.push(buffer);
  }
  if (chunks.length === 0) {
    return undefined;
  }
  const raw = Buffer.concat(chunks).toString("utf8").trim();
  if (!raw) {
    return undefined;
  }
  try {
    return JSON.parse(raw) as unknown;
  } catch {
    throw new ApiError(400, "invalid_json_body", "Request body must be valid JSON");
  }
}
