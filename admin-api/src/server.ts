import { createServer } from "node:http";
import { resolveAuthenticator } from "./auth.js";
import { createNodeHandler } from "./http.js";
import { PostgresAdminApiStore } from "./postgres.js";

export function startAdminApiServer(): void {
  const databaseUrl = process.env.SPAUTOPOST_DATABASE_URL ?? process.env.DATABASE_URL;
  if (!databaseUrl) {
    throw new Error("SPAUTOPOST_DATABASE_URL or DATABASE_URL is required for Admin API");
  }
  // Resolve the authenticator at startup so a misconfigured dev bypass
  // (ADMIN_AUTH_MODE=dev with NODE_ENV=production) fails closed immediately.
  const authenticate = resolveAuthenticator();
  const port = parsePort(process.env.PORT ?? "3000");
  const store = new PostgresAdminApiStore(databaseUrl);
  const server = createServer(createNodeHandler(store, authenticate));
  server.listen(port, () => {
    process.stdout.write(`SPAutoPost Admin API listening on http://127.0.0.1:${port}\n`);
  });
}

function parsePort(raw: string): number {
  const port = Number(raw);
  if (!Number.isInteger(port) || port < 1 || port > 65_535) {
    throw new Error("PORT must be an integer between 1 and 65535");
  }
  return port;
}
