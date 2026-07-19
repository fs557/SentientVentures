/** Server-only configuration names shared by later API phases. */
export const SERVER_ENV_KEYS = [
  "SV_DATA_ROOT", "SV_ALLOWED_ORIGINS", "SV_MAX_FILE_BYTES",
  "SV_MAX_AGGREGATE_FILE_BYTES", "SV_OCR_ENABLED", "SV_OCR_TEXT_THRESHOLD",
  "SV_LLM_PROVIDER", "SV_LLM_MODEL", "SV_LLM_TIMEOUT_SECONDS",
  "SV_LOG_LEVEL", "SV_ENABLE_DEV_RESET", "SV_DEMO_RESET_TOKEN",
  "OPENAI_API_KEY", "ANTHROPIC_API_KEY"
] as const;

export type ServerEnvKey = (typeof SERVER_ENV_KEYS)[number];
export const DEFAULT_ALLOWED_ORIGINS = ["http://localhost:8080", "http://localhost:8081"] as const;
export const DEFAULT_MAX_FILE_BYTES = 25 * 1024 * 1024;
export const DEFAULT_MAX_AGGREGATE_FILE_BYTES = 75 * 1024 * 1024;
