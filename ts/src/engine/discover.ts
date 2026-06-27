/**
 * `gigaphone discover` — Phase A (DESIGN §8.2/§8.3).
 *
 * Deterministic heuristic discovery: run each language pack's `discover` over the scoped files
 * and union the proposed descriptors. The head-less fallback the e2e uses; the harness-driven
 * discovery protocol can supersede or confirm these before they are committed (ADR-0004/0006).
 */

import type { Descriptor } from "../core/model.js";
import { packForPath } from "../packs/registry.js";
import { read, scan } from "./project.js";

export function discover(root: string, scope?: string): Descriptor[] {
  const found = new Map<string, Descriptor>();
  for (const sf of scan(root, scope)) {
    const pack = packForPath(sf.absPath);
    if (pack === null) continue;
    for (const d of pack.discover(sf.relPath, read(sf))) {
      if (!found.has(d.matchCall)) found.set(d.matchCall, d);
    }
  }
  // stable order: gateways first, then tools, by id
  return [...found.values()].sort((a, b) =>
    a.kind !== b.kind ? a.kind.localeCompare(b.kind) : a.id.localeCompare(b.id),
  );
}
