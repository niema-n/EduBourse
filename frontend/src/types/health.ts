export type ApiComponentStatus = "ok" | "unavailable";
export type ApiOverallStatus = "ok" | "degraded" | "unavailable";
export type CollectionStatus = "present" | "missing" | "unknown";
export type UiStatus = "loading" | "fetching" | "healthy" | "degraded" | "unavailable" | "error";

export type HealthResponse = {
  status: ApiOverallStatus;
  app: string;
  version: string;
  environment: string;
  postgres: {
    status: ApiComponentStatus;
  };
  chroma: {
    status: ApiComponentStatus;
    collection: string;
    collection_status: CollectionStatus;
    document_count: number;
  };
};
