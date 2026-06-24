import assert from "node:assert/strict";
import { beforeEach, describe, it } from "node:test";
import { handleAdminApiRequest } from "../src/http.js";
import { normalizeHeaders } from "../src/service.js";
import type {
  AdminApiStore,
  AdminCommand,
  DraftPostDetail,
  DraftPostSummary,
  EnqueueResult,
  NewAdminCommand,
} from "../src/types.js";

class FakeStore implements AdminApiStore {
  readonly enqueued: NewAdminCommand[] = [];
  private readonly drafts = new Map<string, DraftPostDetail>();
  private readonly commands = new Map<string, AdminCommand>();

  constructor() {
    const draft: DraftPostDetail = {
      draftId: "draft-1",
      title: "Security advisory",
      status: "review_requested",
      urgency: "high",
      updatedAt: "2026-06-24T00:00:00.000Z",
      validationWarnings: ["needs source review"],
      audience: "mixed",
      summaryForUsers: "Summary",
      impact: "Impact",
      advisoryIds: ["adv-1"],
      requiredActions: ["Apply update"],
      adminActions: ["Check inventory"],
      references: [{ url: "https://example.test/advisory" }],
      reviewComments: [],
    };
    this.drafts.set(draft.draftId, draft);
  }

  async listDrafts(): Promise<readonly DraftPostSummary[]> {
    return [...this.drafts.values()].map(
      ({ draftId, title, status, urgency, updatedAt, validationWarnings }) => ({
        draftId,
        title,
        status,
        urgency,
        updatedAt,
        validationWarnings,
      }),
    );
  }

  async getDraft(draftId: string): Promise<DraftPostDetail | undefined> {
    return this.drafts.get(draftId);
  }

  async listReviewEvents(): Promise<readonly []> {
    return [];
  }

  async listAuditEvents(): Promise<readonly []> {
    return [];
  }

  async getCommand(commandId: string): Promise<AdminCommand | undefined> {
    return this.commands.get(commandId);
  }

  async enqueueCommand(command: NewAdminCommand): Promise<EnqueueResult> {
    const existing = [...this.commands.values()].find(
      (candidate) => candidate.idempotencyKey === command.idempotencyKey,
    );
    if (existing) {
      return { command: existing, created: false };
    }
    this.enqueued.push(command);
    const stored: AdminCommand = { ...command, status: "pending" };
    this.commands.set(stored.commandId, stored);
    return { command: stored, created: true };
  }
}

let store: FakeStore;

beforeEach(() => {
  store = new FakeStore();
});

describe("Admin API skeleton", () => {
  it("returns DraftPost list without mutating state", async () => {
    const response = await handleAdminApiRequest(store, {
      method: "GET",
      path: "/api/drafts",
      headers: headers({ roles: "viewer" }),
    });

    assert.equal(response.status, 200);
    assert.equal(store.enqueued.length, 0);
    assert.deepEqual((response.body.data as DraftPostSummary[])[0]?.draftId, "draft-1");
  });

  it("treats empty pagination query parameters as defaults", async () => {
    const response = await handleAdminApiRequest(store, {
      method: "GET",
      path: "/api/drafts",
      query: new Map([
        ["limit", " "],
        ["offset", ""],
      ]),
      headers: headers({ roles: "viewer" }),
    });

    assert.equal(response.status, 200);
    assert.deepEqual(response.body.pagination, { limit: 100, offset: 0 });
  });

  it("requires a client Idempotency-Key for state-changing writes", async () => {
    const response = await handleAdminApiRequest(store, {
      method: "POST",
      path: "/api/drafts/draft-1/approve",
      headers: headers({ roles: "approver" }),
      body: {},
    });

    assert.equal(response.status, 400);
    assert.equal(store.enqueued.length, 0);
    assert.deepEqual(response.body, {
      success: false,
      error: {
        code: "missing_idempotency_key",
        message: "State-changing Admin API requests require an Idempotency-Key header",
      },
    });
  });

  it("requires an admin principal for read paths", async () => {
    const response = await handleAdminApiRequest(store, {
      method: "GET",
      path: "/api/drafts",
      headers: new Map(),
    });

    assert.equal(response.status, 401);
    assert.equal(store.enqueued.length, 0);
  });

  it("requires an admin principal for command status reads", async () => {
    const response = await handleAdminApiRequest(store, {
      method: "GET",
      path: "/api/commands/command-1",
      headers: new Map(),
    });

    assert.equal(response.status, 401);
  });

  it("enqueues approve as AdminCommand and exposes a status URL", async () => {
    const response = await handleAdminApiRequest(store, {
      method: "POST",
      path: "/api/drafts/draft-1/approve",
      headers: headers({ roles: "approver", idempotencyKey: "retry-1" }),
      body: { comment: "Reviewed" },
    });

    assert.equal(response.status, 202);
    assert.equal(store.enqueued.length, 1);
    assert.equal(store.enqueued[0]?.commandType, "approve");
    assert.equal(store.enqueued[0]?.targetDraftId, "draft-1");
    assert.equal(store.enqueued[0]?.requestedBy, "user-1");
    assert.match(store.enqueued[0]?.idempotencyKey ?? "", /^admin-api:[a-f0-9]{64}$/u);
    assert.deepEqual((response.body.data as { statusUrl: string }).statusUrl.startsWith("/api/commands/"), true);
  });

  it("deduplicates retries with the same Idempotency-Key", async () => {
    const request = {
      method: "POST",
      path: "/api/drafts/draft-1/reject",
      headers: headers({ roles: "reviewer", idempotencyKey: "retry-2" }),
      body: { comment: "Needs rewrite" },
    };

    const first = await handleAdminApiRequest(store, request);
    const second = await handleAdminApiRequest(store, request);

    assert.equal(first.status, 202);
    assert.equal(second.status, 202);
    assert.equal(store.enqueued.length, 1);
    assert.equal((second.body.data as { deduplicated: boolean }).deduplicated, true);
  });

  it("scopes idempotency keys by principal", async () => {
    const first = await handleAdminApiRequest(store, {
      method: "POST",
      path: "/api/drafts/draft-1/reject",
      headers: headers({ roles: "reviewer", idempotencyKey: "retry-3" }),
      body: { comment: "Needs rewrite" },
    });
    const second = await handleAdminApiRequest(store, {
      method: "POST",
      path: "/api/drafts/draft-1/reject",
      headers: headers({ user: "user-2", roles: "reviewer", idempotencyKey: "retry-3" }),
      body: { comment: "Needs rewrite" },
    });

    assert.equal(first.status, 202);
    assert.equal(second.status, 202);
    assert.equal(store.enqueued.length, 2);
    assert.notEqual(store.enqueued[0]?.idempotencyKey, store.enqueued[1]?.idempotencyKey);
  });

  it("treats malformed encoded path parameters as not found", async () => {
    const response = await handleAdminApiRequest(store, {
      method: "GET",
      path: "/api/drafts/%E0%A4%A",
      headers: headers({ roles: "viewer" }),
    });

    assert.equal(response.status, 404);
  });

  it("rejects publish request unless the principal has publisher role", async () => {
    const response = await handleAdminApiRequest(store, {
      method: "POST",
      path: "/api/drafts/draft-1/publish-request",
      headers: headers({ roles: "reviewer", idempotencyKey: "publish-1" }),
      body: {},
    });

    assert.equal(response.status, 403);
    assert.equal(store.enqueued.length, 0);
  });

  it("returns command status for async reviewer feedback", async () => {
    const enqueued = await handleAdminApiRequest(store, {
      method: "PATCH",
      path: "/api/drafts/draft-1",
      headers: headers({ roles: "reviewer", idempotencyKey: "edit-1" }),
      body: { title: "Updated title" },
    });
    const command = (enqueued.body.data as { command: AdminCommand }).command;

    const response = await handleAdminApiRequest(store, {
      method: "GET",
      path: `/api/commands/${command.commandId}`,
      headers: headers({ roles: "viewer" }),
    });

    assert.equal(response.status, 200);
    assert.deepEqual(response.body.data, {
      commandId: command.commandId,
      status: "pending",
      errorCode: undefined,
      errorMessage: undefined,
      processedAt: undefined,
    });
    assert.equal("payload" in (response.body.data as Record<string, unknown>), false);
  });

  it("rejects secret-looking AdminCommand payload keys", async () => {
    const response = await handleAdminApiRequest(store, {
      method: "PATCH",
      path: "/api/drafts/draft-1",
      headers: headers({ roles: "reviewer", idempotencyKey: "secret-payload-1" }),
      body: { nested: { access_token: "not-stored" } },
    });

    assert.equal(response.status, 400);
    assert.equal(store.enqueued.length, 0);
    assert.deepEqual(response.body, {
      success: false,
      error: {
        code: "secret_payload_key",
        message: "AdminCommand payload must not contain secret-looking keys",
      },
    });
  });

  it("joins multi-value HTTP headers before role parsing", async () => {
    const normalized = normalizeHeaders({
      "x-spautopost-user": "user-1",
      "x-spautopost-roles": ["viewer", "approver"],
    });

    const response = await handleAdminApiRequest(store, {
      method: "POST",
      path: "/api/drafts/draft-1/approve",
      headers: new Map([...normalized, ["idempotency-key", "multi-header-1"]]),
      body: {},
    });

    assert.equal(response.status, 202);
    assert.equal(store.enqueued[0]?.commandType, "approve");
  });
});

function headers(input: { roles: string; idempotencyKey?: string; user?: string }): Map<string, string> {
  const result = new Map<string, string>([
    ["x-spautopost-user", input.user ?? "user-1"],
    ["x-spautopost-roles", input.roles],
  ]);
  if (input.idempotencyKey) {
    result.set("idempotency-key", input.idempotencyKey);
  }
  return result;
}
