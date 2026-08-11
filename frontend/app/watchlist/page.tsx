"use client";

import { useEffect, useMemo, useState } from "react";
import { FolderPlus, Plus, Power, Search, Tag, Trash2, X } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/EmptyState";
import { useLiveWebSocket } from "@/hooks/useLiveWebSocket";
import { apiFetch, cn } from "@/lib/utils";
import type { Segment, WatchlistItem } from "@/lib/types";

const UNCATEGORIZED = "uncategorized";
const ALL = "all";

const pillClass =
  "flex min-h-11 shrink-0 cursor-pointer items-center gap-1.5 rounded-md px-3 py-2 text-sm font-medium transition-colors duration-150";
const selectClass =
  "min-h-11 rounded-lg border border-border bg-surface-2 px-3 py-2 text-sm text-foreground focus:border-accent";

export default function WatchlistPage() {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [segments, setSegments] = useState<Segment[]>([]);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Array<{ instrument_key: string; trading_symbol: string; name: string }>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchError, setSearchError] = useState("");
  const [addToSegment, setAddToSegment] = useState("");
  const [filterSegment, setFilterSegment] = useState<string>(ALL);
  const [showNewSegment, setShowNewSegment] = useState(false);
  const [newSegmentName, setNewSegmentName] = useState("");
  const { connectionState } = useLiveWebSocket();

  const loadItems = () => {
    apiFetch<WatchlistItem[]>("/api/v1/watchlist")
      .then(setItems)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  const loadSegments = () => {
    apiFetch<Segment[]>("/api/v1/segments")
      .then(setSegments)
      .catch(() => {});
  };

  useEffect(() => {
    loadItems();
    loadSegments();
  }, []);

  useEffect(() => {
    if (query.length < 2) {
      setResults([]);
      setSearchError("");
      return;
    }
    const t = setTimeout(() => {
      setSearchError("");
      apiFetch<Array<{ instrument_key: string; trading_symbol: string; name: string }>>(
        `/api/v1/watchlist/instruments/search?q=${encodeURIComponent(query)}`
      )
        .then(setResults)
        .catch((e) => {
          setResults([]);
          setSearchError(e instanceof Error ? e.message : "Search failed");
        });
    }, 300);
    return () => clearTimeout(t);
  }, [query]);

  const addStock = async (inst: { instrument_key: string; trading_symbol: string; name: string }) => {
    await apiFetch("/api/v1/watchlist", {
      method: "POST",
      body: JSON.stringify({
        instrument_key: inst.instrument_key,
        trading_symbol: inst.trading_symbol,
        company_name: inst.name,
        segment_id: addToSegment ? Number(addToSegment) : null,
      }),
    });
    setQuery("");
    setResults([]);
    loadItems();
  };

  const toggle = async (item: WatchlistItem) => {
    await apiFetch(`/api/v1/watchlist/${item.id}`, {
      method: "PATCH",
      body: JSON.stringify({ enabled: !item.enabled }),
    });
    loadItems();
  };

  const remove = async (id: number) => {
    await apiFetch(`/api/v1/watchlist/${id}`, { method: "DELETE" });
    loadItems();
  };

  const changeSegment = async (item: WatchlistItem, segmentId: string) => {
    await apiFetch(`/api/v1/watchlist/${item.id}`, {
      method: "PATCH",
      body: JSON.stringify({ segment_id: segmentId ? Number(segmentId) : null }),
    });
    loadItems();
  };

  const createSegment = async () => {
    const name = newSegmentName.trim();
    if (!name) return;
    try {
      await apiFetch("/api/v1/segments", { method: "POST", body: JSON.stringify({ name }) });
      setNewSegmentName("");
      setShowNewSegment(false);
      loadSegments();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create segment");
    }
  };

  const deleteSegment = async (segment: Segment) => {
    if (!window.confirm(`Delete segment "${segment.name}"? Stocks in it become Uncategorized.`)) return;
    await apiFetch(`/api/v1/segments/${segment.id}`, { method: "DELETE" });
    if (filterSegment === String(segment.id)) setFilterSegment(ALL);
    if (addToSegment === String(segment.id)) setAddToSegment("");
    loadSegments();
    loadItems();
  };

  const segmentName = (id?: number | null) => segments.find((s) => s.id === id)?.name;

  const visibleItems = useMemo(() => {
    if (filterSegment === ALL) return items;
    if (filterSegment === UNCATEGORIZED) return items.filter((i) => !i.segment_id);
    return items.filter((i) => i.segment_id === Number(filterSegment));
  }, [items, filterSegment]);

  const groups = useMemo(() => {
    if (filterSegment !== ALL) {
      return [{ id: filterSegment, name: filterSegment === UNCATEGORIZED ? "Uncategorized" : segmentName(Number(filterSegment)) || "", items: visibleItems }];
    }
    const bySegment = new Map<string, WatchlistItem[]>();
    for (const item of items) {
      const key = item.segment_id ? String(item.segment_id) : UNCATEGORIZED;
      if (!bySegment.has(key)) bySegment.set(key, []);
      bySegment.get(key)!.push(item);
    }
    const named = segments
      .filter((s) => bySegment.has(String(s.id)))
      .map((s) => ({ id: String(s.id), name: s.name, items: bySegment.get(String(s.id))! }));
    const uncategorized = bySegment.get(UNCATEGORIZED);
    return uncategorized ? [...named, { id: UNCATEGORIZED, name: "Uncategorized", items: uncategorized }] : named;
  }, [items, segments, filterSegment, visibleItems]);

  return (
    <AppShell wsState={connectionState}>
      <div className="relative mb-4">
        <div className="flex flex-col gap-2 sm:flex-row">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-2" strokeWidth={2} />
            <input
              type="text"
              placeholder="Search NSE equities..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="min-h-11 w-full rounded-lg border border-border bg-surface py-2.5 pl-10 pr-4 text-sm text-foreground placeholder:text-muted-2 focus:border-accent"
            />
          </div>
          <label className="flex min-h-11 shrink-0 items-center gap-2 text-sm text-muted">
            Add to
            <select value={addToSegment} onChange={(e) => setAddToSegment(e.target.value)} className={selectClass}>
              <option value="">Uncategorized</option>
              {segments.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </label>
        </div>
        {searchError && <p className="mt-1 text-xs text-sell">{searchError}</p>}
        {results.length > 0 && (
          <ul className="absolute z-10 mt-1 w-full overflow-hidden rounded-lg border border-border bg-surface-2 shadow-lg sm:w-auto sm:min-w-[calc(100%-9rem)]">
            {results.map((r) => (
              <li
                key={r.instrument_key}
                className="flex cursor-pointer items-center justify-between gap-3 px-4 py-2.5 transition-colors hover:bg-surface"
                onClick={() => addStock(r)}
              >
                <div>
                  <span className="font-medium text-foreground">{r.trading_symbol}</span>
                  <span className="ml-2 text-xs text-muted">{r.name}</span>
                </div>
                <Plus className="h-4 w-4 shrink-0 text-accent" strokeWidth={2.25} />
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="mb-5 flex flex-wrap items-center gap-1.5">
        <button
          onClick={() => setFilterSegment(ALL)}
          className={cn(pillClass, filterSegment === ALL ? "bg-accent text-accent-foreground" : "bg-surface text-muted hover:text-foreground")}
        >
          All ({items.length})
        </button>
        <button
          onClick={() => setFilterSegment(UNCATEGORIZED)}
          className={cn(
            pillClass,
            filterSegment === UNCATEGORIZED ? "bg-accent text-accent-foreground" : "bg-surface text-muted hover:text-foreground"
          )}
        >
          Uncategorized ({items.filter((i) => !i.segment_id).length})
        </button>
        {segments.map((s) => (
          <div key={s.id} className="group relative">
            <button
              onClick={() => setFilterSegment(String(s.id))}
              className={cn(
                pillClass,
                "pr-7",
                filterSegment === String(s.id) ? "bg-accent text-accent-foreground" : "bg-surface text-muted hover:text-foreground"
              )}
            >
              <Tag className="h-3.5 w-3.5" strokeWidth={2.25} />
              {s.name} ({items.filter((i) => i.segment_id === s.id).length})
            </button>
            <button
              onClick={() => deleteSegment(s)}
              title={`Delete segment "${s.name}"`}
              aria-label={`Delete segment ${s.name}`}
              className={cn(
                "absolute right-1 top-1/2 flex h-6 w-6 -translate-y-1/2 cursor-pointer items-center justify-center rounded transition-colors hover:bg-sell-soft hover:text-sell",
                filterSegment === String(s.id) ? "text-accent-foreground/70" : "text-muted-2"
              )}
            >
              <X className="h-3.5 w-3.5" strokeWidth={2.5} />
            </button>
          </div>
        ))}
        {showNewSegment ? (
          <div className="flex min-h-11 items-center gap-1.5">
            <input
              autoFocus
              placeholder="Segment name"
              value={newSegmentName}
              onChange={(e) => setNewSegmentName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") createSegment();
                if (e.key === "Escape") {
                  setShowNewSegment(false);
                  setNewSegmentName("");
                }
              }}
              className="min-h-11 w-40 rounded-lg border border-border bg-surface-2 px-3 py-2 text-sm text-foreground focus:border-accent"
            />
            <button onClick={createSegment} className="min-h-11 cursor-pointer rounded-lg bg-accent px-3 py-2 text-sm font-medium text-accent-foreground hover:bg-accent-hover">
              Save
            </button>
            <button
              onClick={() => {
                setShowNewSegment(false);
                setNewSegmentName("");
              }}
              className="min-h-11 cursor-pointer rounded-lg px-2 text-sm text-muted hover:text-foreground"
            >
              Cancel
            </button>
          </div>
        ) : (
          <button onClick={() => setShowNewSegment(true)} className={cn(pillClass, "border border-dashed border-border text-muted hover:border-accent hover:text-accent")}>
            <FolderPlus className="h-3.5 w-3.5" strokeWidth={2.25} />
            New Segment
          </button>
        )}
      </div>

      {error && <ErrorState message={error} />}
      {loading && <LoadingSkeleton />}
      {!loading && items.length === 0 && (
        <EmptyState title="Watch list is empty" description="Search and add stocks to always include them in scanning." />
      )}
      {!loading && items.length > 0 && visibleItems.length === 0 && (
        <EmptyState title="No stocks in this segment" description="Add stocks here using the search bar above." />
      )}

      <div className="space-y-6">
        {groups.map((group) => (
          <div key={group.id}>
            {filterSegment === ALL && groups.length > 1 && (
              <h2 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-2">
                <Tag className="h-3.5 w-3.5" strokeWidth={2.25} />
                {group.name} <span className="font-mono-num normal-case">({group.items.length})</span>
              </h2>
            )}
            <div className="space-y-2">
              {group.items.map((item) => (
                <div
                  key={item.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-surface px-4 py-3 transition-colors hover:border-border-strong"
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium text-foreground">{item.trading_symbol}</p>
                    <p className="truncate text-xs text-muted">{item.company_name}</p>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <select
                      value={item.segment_id ?? ""}
                      onChange={(e) => changeSegment(item, e.target.value)}
                      title="Reassign segment"
                      className={cn(selectClass, "min-h-11")}
                    >
                      <option value="">Uncategorized</option>
                      {segments.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name}
                        </option>
                      ))}
                    </select>
                    <button
                      onClick={() => toggle(item)}
                      title={item.enabled ? "Enabled — click to disable" : "Disabled — click to enable"}
                      className={cn(
                        "flex min-h-11 cursor-pointer items-center gap-1.5 rounded-md px-3 py-2.5 text-xs font-medium transition-colors",
                        item.enabled ? "bg-buy-soft text-buy" : "bg-surface-2 text-muted"
                      )}
                    >
                      <Power className="h-3.5 w-3.5" strokeWidth={2.25} />
                      {item.enabled ? "Enabled" : "Disabled"}
                    </button>
                    <button
                      onClick={() => remove(item.id)}
                      title="Remove from watch list"
                      aria-label="Remove from watch list"
                      className="flex h-11 w-11 shrink-0 cursor-pointer items-center justify-center rounded-md text-muted transition-colors hover:bg-sell-soft hover:text-sell"
                    >
                      <Trash2 className="h-4 w-4" strokeWidth={2.25} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </AppShell>
  );
}
