export type DraftStatus =
  | "created"
  | "generated"
  | "review_requested"
  | "reviewed"
  | "approved"
  | "rejected"
  | "regeneration_requested"
  | "publishing"
  | "published"
  | "failed"
  | "cancelled";

export type AdminCommandType =
  | "edit"
  | "approve"
  | "reject"
  | "request_regeneration"
  | "publish_request";

export type AdminCommandStatus =
  | "pending"
  | "processing"
  | "succeeded"
  | "failed"
  | "cancelled";

export type AdminRole = "viewer" | "reviewer" | "approver" | "publisher" | "admin";

export interface AdminPrincipal {
  readonly principalId: string;
  readonly displayName?: string | undefined;
  readonly roles: readonly AdminRole[];
}

export interface DraftPostSummary {
  readonly draftId: string;
  readonly title: string;
  readonly status: DraftStatus;
  readonly urgency: "emergency" | "high" | "normal" | "low";
  readonly updatedAt: string;
  readonly validationWarnings: readonly string[];
}

export interface DraftPostDetail extends DraftPostSummary {
  readonly audience: "general_users" | "administrators" | "mixed";
  readonly summaryForUsers: string;
  readonly impact: string;
  readonly advisoryIds: readonly string[];
  readonly requiredActions: readonly string[];
  readonly adminActions: readonly string[];
  readonly references: readonly Record<string, string>[];
  readonly reviewComments: readonly string[];
}

export interface ReviewEvent {
  readonly reviewEventId: string;
  readonly draftId: string;
  readonly reviewer: string;
  readonly action: "request_review" | "comment" | "approve" | "reject" | "request_regeneration";
  readonly createdAt: string;
  readonly comment?: string | undefined;
  readonly previousStatus?: DraftStatus | undefined;
  readonly nextStatus?: DraftStatus | undefined;
}

export interface AuditEvent {
  readonly auditEventId: string;
  readonly eventType: string;
  readonly correlationId: string;
  readonly result: "success" | "failure" | "skipped" | "warning";
  readonly createdAt: string;
  readonly actor?: string | undefined;
  readonly relatedIds?: Record<string, unknown> | undefined;
  readonly errorCode?: string | undefined;
  readonly errorMessage?: string | undefined;
}

export interface AdminCommand {
  readonly commandId: string;
  readonly commandType: AdminCommandType;
  readonly targetDraftId?: string | undefined;
  readonly requestedBy?: string | undefined;
  readonly payload: Record<string, unknown>;
  readonly idempotencyKey: string;
  readonly status: AdminCommandStatus;
  readonly errorCode?: string | undefined;
  readonly errorMessage?: string | undefined;
  readonly correlationId?: string | undefined;
  readonly createdAt: string;
  readonly processedAt?: string | undefined;
}

export interface NewAdminCommand {
  readonly commandId: string;
  readonly commandType: AdminCommandType;
  readonly targetDraftId: string;
  readonly requestedBy: string;
  readonly payload: Record<string, unknown>;
  readonly idempotencyKey: string;
  readonly correlationId: string;
  readonly createdAt: string;
}

export interface EnqueueResult {
  readonly command: AdminCommand;
  readonly created: boolean;
}

export interface AdminApiStore {
  listDrafts(params: { readonly limit: number; readonly offset: number }): Promise<readonly DraftPostSummary[]>;
  getDraft(draftId: string): Promise<DraftPostDetail | undefined>;
  listReviewEvents(draftId: string): Promise<readonly ReviewEvent[]>;
  listAuditEvents(draftId: string): Promise<readonly AuditEvent[]>;
  getCommand(commandId: string): Promise<AdminCommand | undefined>;
  enqueueCommand(command: NewAdminCommand): Promise<EnqueueResult>;
}
