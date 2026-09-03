import type { PersistOptions } from "zustand/middleware";

export const STORE_VERSION = 1;

/**
 * Persistence is deliberately opted into per store, and rehydration is skipped
 * during store creation. The first client render therefore matches what the
 * server produced, and `StoreHydrator` replays localStorage after mount — which
 * keeps refresh-durable CRUD without a hydration mismatch.
 */
export function persistConfig<T>(
  name: string,
  partialize?: PersistOptions<T, Partial<T>>["partialize"],
): PersistOptions<T, Partial<T>> {
  return {
    name: `margin.${name}`,
    version: STORE_VERSION,
    skipHydration: true,
    // Spreading an explicit `undefined` would overwrite zustand's own default
    // partializer, so the key is only present when a store actually narrows.
    ...(partialize ? { partialize } : {}),
  } as PersistOptions<T, Partial<T>>;
}
