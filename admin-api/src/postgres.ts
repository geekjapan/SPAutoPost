import pg from "pg";
import type {
  AdminApiStore,
  AdminCommand,
  AdminCommandType,
  AuditEvent,
  DraftPostDetail,
  DraftPostSummary,
  EnqueueResult,
  NewAdminCommand,
  ReviewEvent,
} from "./types.js";

const { Pool } = pg;

export class PostgresAdminApiStore implements AdminApiStore {
  private readonly pool: pg.Pool;

  constructor(databaseUrl: string) {
    this.pool = new Pool({ connectionString: databaseUrl });
    this.pool.on("error", (error) => {
      process.stderr.write(`Postgres pool idle client error: ${error.message}\n`);
    });
  }

  async listDrafts(params: { readonly limit: number; readonly offset: number }): Promise<readonly DraftPostSummary[]> {
    const result = await this.pool.query(
      `SELECT draft_id, title, status, urgency, updated_at, validation_warnings
       FROM draft_posts
       ORDER BY updated_at DESC, draft_id ASC
       LIMIT $1 OFFSET $2`,
      [params.limit, params.offset],
    );
    return result.rows.map(mapDraftSummary);
  }

  async getDraft(draftId: string): Promise<DraftPostDetail | undefined> {
    const result = await this.pool.query(
      `SELECT draft_id, title, audience, urgency, summary_for_users, impact, status,
              updated_at, advisory_ids, required_actions, admin_actions, "references",
              validation_warnings, review_comments
       FROM draft_posts
       WHERE draft_id = $1`,
      [draftId],
    );
    const row = result.rows[0] as Record<string, unknown> | undefined;
    return row ? mapDraftDetail(row) : undefined;
  }

  async listReviewEvents(draftId: string): Promise<readonly ReviewEvent[]> {
    const result = await this.pool.query(
      `SELECT review_event_id, draft_id, reviewer, action, created_at, comment,
              previous_status, next_status
       FROM review_events
       WHERE draft_id = $1
       ORDER BY created_at ASC, review_event_id ASC`,
      [draftId],
    );
    return result.rows.map(mapReviewEvent);
  }

  async listAuditEvents(draftId: string): Promise<readonly AuditEvent[]> {
    const result = await this.pool.query(
      `SELECT audit_event_id, event_type, correlation_id, result, created_at, actor,
              related_ids, error_code, error_message
       FROM audit_events
       WHERE related_ids ->> 'draft_id' = $1
       ORDER BY created_at ASC, audit_event_id ASC`,
      [draftId],
    );
    return result.rows.map(mapAuditEvent);
  }

  async getCommand(commandId: string): Promise<AdminCommand | undefined> {
    const result = await this.pool.query(
      `SELECT command_id, command_type, target_draft_id, requested_by, payload,
              idempotency_key, status, error_code, error_message, correlation_id,
              created_at, processed_at
       FROM admin_commands
       WHERE command_id = $1`,
      [commandId],
    );
    const row = result.rows[0] as Record<string, unknown> | undefined;
    return row ? mapAdminCommand(row) : undefined;
  }

  async enqueueCommand(command: NewAdminCommand): Promise<EnqueueResult> {
    const inserted = await this.pool.query(
      `INSERT INTO admin_commands (
          command_id, command_type, target_draft_id, requested_by, payload,
          idempotency_key, status, correlation_id, created_at
       )
       VALUES ($1, $2, $3, $4, $5::jsonb, $6, 'pending', $7, $8)
       ON CONFLICT (idempotency_key) DO NOTHING
       RETURNING command_id, command_type, target_draft_id, requested_by, payload,
                 idempotency_key, status, error_code, error_message, correlation_id,
                 created_at, processed_at`,
      [
        command.commandId,
        command.commandType,
        command.targetDraftId,
        command.requestedBy,
        JSON.stringify(command.payload),
        command.idempotencyKey,
        command.correlationId,
        command.createdAt,
      ],
    );
    const insertedRow = inserted.rows[0] as Record<string, unknown> | undefined;
    if (insertedRow) {
      return { command: mapAdminCommand(insertedRow), created: true };
    }

    const existing = await this.pool.query(
      `SELECT command_id, command_type, target_draft_id, requested_by, payload,
              idempotency_key, status, error_code, error_message, correlation_id,
              created_at, processed_at
       FROM admin_commands
       WHERE idempotency_key = $1`,
      [command.idempotencyKey],
    );
    const existingRow = existing.rows[0] as Record<string, unknown> | undefined;
    if (!existingRow) {
      throw new Error("AdminCommand idempotency conflict could not be read");
    }
    return { command: mapAdminCommand(existingRow), created: false };
  }

  async close(): Promise<void> {
    await this.pool.end();
  }
}

function mapDraftSummary(row: Record<string, unknown>): DraftPostSummary {
  return {
    draftId: stringValue(row.draft_id),
    title: stringValue(row.title),
    status: stringValue(row.status) as DraftPostSummary["status"],
    urgency: stringValue(row.urgency) as DraftPostSummary["urgency"],
    updatedAt: dateString(row.updated_at),
    validationWarnings: stringArray(row.validation_warnings),
  };
}

function mapDraftDetail(row: Record<string, unknown>): DraftPostDetail {
  return {
    ...mapDraftSummary(row),
    audience: stringValue(row.audience) as DraftPostDetail["audience"],
    summaryForUsers: stringValue(row.summary_for_users),
    impact: stringValue(row.impact),
    advisoryIds: stringArray(row.advisory_ids),
    requiredActions: stringArray(row.required_actions),
    adminActions: stringArray(row.admin_actions),
    references: objectArray(row.references),
    reviewComments: stringArray(row.review_comments),
  };
}

function mapReviewEvent(row: Record<string, unknown>): ReviewEvent {
  return {
    reviewEventId: stringValue(row.review_event_id),
    draftId: stringValue(row.draft_id),
    reviewer: stringValue(row.reviewer),
    action: stringValue(row.action) as ReviewEvent["action"],
    createdAt: dateString(row.created_at),
    comment: optionalString(row.comment),
    previousStatus: optionalString(row.previous_status) as ReviewEvent["previousStatus"],
    nextStatus: optionalString(row.next_status) as ReviewEvent["nextStatus"],
  };
}

function mapAuditEvent(row: Record<string, unknown>): AuditEvent {
  return {
    auditEventId: stringValue(row.audit_event_id),
    eventType: stringValue(row.event_type),
    correlationId: stringValue(row.correlation_id),
    result: stringValue(row.result) as AuditEvent["result"],
    createdAt: dateString(row.created_at),
    actor: optionalString(row.actor),
    relatedIds: objectValue(row.related_ids),
    errorCode: optionalString(row.error_code),
    errorMessage: optionalString(row.error_message),
  };
}

function mapAdminCommand(row: Record<string, unknown>): AdminCommand {
  return {
    commandId: stringValue(row.command_id),
    commandType: stringValue(row.command_type) as AdminCommandType,
    targetDraftId: optionalString(row.target_draft_id),
    requestedBy: optionalString(row.requested_by),
    payload: objectValue(row.payload) ?? {},
    idempotencyKey: stringValue(row.idempotency_key),
    status: stringValue(row.status) as AdminCommand["status"],
    errorCode: optionalString(row.error_code),
    errorMessage: optionalString(row.error_message),
    correlationId: optionalString(row.correlation_id),
    createdAt: dateString(row.created_at),
    processedAt: optionalDateString(row.processed_at),
  };
}

function stringValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "";
  }
  if (typeof value === "string") {
    return value;
  }
  if (value instanceof Date) {
    return value.toISOString();
  }
  return String(value);
}

function optionalString(value: unknown): string | undefined {
  return value === null || value === undefined ? undefined : stringValue(value);
}

function dateString(value: unknown): string {
  return value instanceof Date ? value.toISOString() : stringValue(value);
}

function optionalDateString(value: unknown): string | undefined {
  return value === null || value === undefined ? undefined : dateString(value);
}

function stringArray(value: unknown): readonly string[] {
  return arrayValue(value).filter((item): item is string => typeof item === "string");
}

function objectArray(value: unknown): readonly Record<string, string>[] {
  return arrayValue(value).filter(isStringRecord);
}

function arrayValue(value: unknown): readonly unknown[] {
  if (Array.isArray(value)) {
    return value;
  }
  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value) as unknown;
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }
  return [];
}

function objectValue(value: unknown): Record<string, unknown> | undefined {
  if (isRecord(value)) {
    return value;
  }
  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value) as unknown;
      return isRecord(parsed) ? parsed : undefined;
    } catch {
      return undefined;
    }
  }
  return undefined;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isStringRecord(value: unknown): value is Record<string, string> {
  return isRecord(value) && Object.values(value).every((nested) => typeof nested === "string");
}
