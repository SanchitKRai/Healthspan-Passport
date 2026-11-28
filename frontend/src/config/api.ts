const configuredApiUrl = process.env.NEXT_PUBLIC_API_URL?.trim().replace(/\/+$/, "") || "";
const isProductionBuild = process.env.NODE_ENV === "production";

export const API_CONFIG_ERROR: string | null =
  isProductionBuild && !configuredApiUrl
    ? "Backend URL is not configured (NEXT_PUBLIC_API_URL missing in production build)."
    : null;

export const API_BASE_URL: string =
  configuredApiUrl || (isProductionBuild ? "" : "http://127.0.0.1:8000");

export const BACKEND_UNREACHABLE_MESSAGE =
  "Backend unreachable, retry (cold start may take ~1 min).";

export function isNetworkUnreachableError(err: unknown): boolean {
  if (!API_BASE_URL) return true;
  if (err instanceof TypeError) return true;
  const msg = err instanceof Error ? err.message.toLowerCase() : String(err).toLowerCase();
  return msg.includes("failed to fetch") || msg.includes("networkerror") || msg.includes("load failed");
}
