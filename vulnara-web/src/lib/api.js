import { mockApi } from "./mockApi";
import { realApi } from "./realApi";

export const USE_MOCK = String(import.meta.env.VITE_USE_MOCK ?? "true") === "true";

// Every page/component imports `api` from here and never touches
// mockApi.js / realApi.js directly. Flip VITE_USE_MOCK in .env to switch
// the entire app's data source in one place.
export const api = USE_MOCK ? mockApi : realApi;
