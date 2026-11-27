import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { deleteBin, getBin, getBins, type BinRecord } from "@/auth";
import { BinFormDrawer } from "@/components/bins/bin-form-drawer";
import { BINS_QUERY_KEY } from "@/lib/bins";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Eye, MoreHorizontal, PenLine, Trash } from "lucide-react";
import { STATUS_THEME, type BinStatus } from "@/lib/theme";
import { formatRelativeTime } from "@/lib/relative-time";
import type { BinUpdate } from "@/lib/bins";
import { useLiveEvents } from "@/hooks/use-live-events";

type BinsProps = {
  userRole: string;
};

type DialogMode = "create" | "edit" | "view" | "delete" | null;

const PAGE_SIZE = 20;

const statusOptions = [
  { value: "", label: "All statuses" },
  { value: "urgent", label: "Urgent" },
  { value: "due", label: "Due" },
  { value: "filling", label: "Filling" },
  { value: "normal", label: "Normal" },
  { value: "offline", label: "Offline" },
  { value: "maintenance", label: "Maintenance" },
];

const sortOptions = [
  { value: "id", label: "Bin ID" },
  { value: "last_fill", label: "Fill: low to high" },
  { value: "-last_fill", label: "Fill: high to low" },
  { value: "last_seen_at", label: "Last seen: oldest" },
  { value: "-last_seen_at", label: "Last seen: newest" },
];

function FillLevel({ fill, status }: { fill: number | null; status: string }) {
  const color = STATUS_THEME[status as BinStatus]?.color ?? "#888780";
  return (
    <div className="flex items-center gap-3">
      <div className="h-1.5 w-24 overflow-hidden rounded-full bg-slate-100">
        {fill !== null && (
          <div
            className="h-full rounded-full"
            style={{ width: `${Math.min(100, Math.max(0, fill))}%`, backgroundColor: color }}
          />
        )}
      </div>
      <span className="w-10 text-right text-sm tabular-nums">
        {fill === null ? "—" : `${Math.round(fill)}%`}
      </span>
    </div>
  );
}

function formatLastSeen(value: string | null, now: number) {
  if (!value) return "Never";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : formatRelativeTime(value, now);
}

function Bins({ userRole }: BinsProps) {
  const canManageBins = userRole === "admin" || userRole === "supervisor";
  const [bins, setBins] = useState<BinRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [sort, setSort] = useState("id");
  const [page, setPage] = useState(1);
  const [refreshKey, setRefreshKey] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogMode, setDialogMode] = useState<DialogMode>(null);
  const [selectedBin, setSelectedBin] = useState<BinRecord | null>(null);
  const [dialogError, setDialogError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const queryClient = useQueryClient();

  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const intervalId = window.setInterval(() => setNow(Date.now()), 10_000);
    return () => window.clearInterval(intervalId);
  }, []);

  useLiveEvents(
    (event) => {
      if (event.type !== "bin_updated") return;
      const update = event.data as BinUpdate;
      setBins((current) =>
        current.map((bin) => (bin.id === update.id ? { ...bin, ...update } : bin)),
      );
      setSelectedBin((current) =>
        current && current.id === update.id ? { ...current, ...update } : current,
      );
    },
    () => setRefreshKey((current) => current + 1),
  );

  const refreshBins = () => {
    setRefreshKey((current) => current + 1);
    void queryClient.invalidateQueries({ queryKey: BINS_QUERY_KEY });
  };

  useEffect(() => {
    let isCurrent = true;
    const timeoutId = window.setTimeout(() => {
      setIsLoading(true);
      setError(null);
      getBins({ q: query, status, sort, page, size: PAGE_SIZE })
        .then((result) => {
          if (!isCurrent) return;
          setBins(result.items);
          setTotal(result.total);
        })
        .catch((loadError: unknown) => {
          if (!isCurrent) return;
          setError(
            loadError instanceof Error ? loadError.message : "Unable to load bins.",
          );
          setBins([]);
          setTotal(0);
        })
        .finally(() => {
          if (isCurrent) setIsLoading(false);
        });
    }, 250);

    return () => {
      isCurrent = false;
      window.clearTimeout(timeoutId);
    };
  }, [query, status, sort, page, refreshKey]);

  const closeDialog = () => {
    if (isSubmitting) return;
    setDialogMode(null);
    setSelectedBin(null);
    setDialogError(null);
  };

  const handleViewBin = async (bin: BinRecord) => {
    setSelectedBin(bin);
    setDialogMode("view");
    setDialogError(null);
    setIsDetailLoading(true);
    try {
      const details = await getBin(bin.id);
      setSelectedBin(details);
    } catch (loadError) {
      setDialogError(
        loadError instanceof Error ? loadError.message : "Unable to load bin details.",
      );
    } finally {
      setIsDetailLoading(false);
    }
  };

  const handleDeleteBin = async () => {
    if (!selectedBin) return;
    setIsSubmitting(true);
    setDialogError(null);
    try {
      await deleteBin(selectedBin.id);
      setDialogMode(null);
      setSelectedBin(null);
      void queryClient.invalidateQueries({ queryKey: BINS_QUERY_KEY });
      if (bins.length === 1 && page > 1) {
        setPage((current) => current - 1);
      } else {
        setRefreshKey((current) => current + 1);
      }
    } catch (deleteError) {
      setDialogError(
        deleteError instanceof Error ? deleteError.message : "Unable to delete this bin.",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const selectedStatus =
    statusOptions.find((option) => option.value === status)?.label ?? "All statuses";
  const selectedSort =
    sortOptions.find((option) => option.value === sort)?.label ?? "Bin ID";
  const firstResult = total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const lastResult = Math.min(page * PAGE_SIZE, total);

  return (
    <main className="mx-auto w-full max-w-[1440px] min-w-0 px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
      <div className="mb-8 flex flex-col items-start justify-between gap-5 sm:flex-row sm:items-end">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">Bins</h1>
          <p className="mt-2 text-sm text-slate-500">
            {isLoading && total === 0
              ? "Loading bins..."
              : `${total} ${total === 1 ? "bin" : "bins"} found`}
          </p>
        </div>
        {canManageBins && (
          <Button
            className="rounded-xl"
            onClick={() => {
              setSelectedBin(null);
              setDialogError(null);
              setDialogMode("create");
            }}
          >
            Add Bin
          </Button>
        )}
      </div>

      <section className="mb-8 flex flex-col items-start gap-2 sm:flex-row sm:items-center">
        <Input
          type="search"
          className="w-full sm:w-80"
          placeholder="Search bins..."
          aria-label="Search bins by ID or name"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setPage(1);
          }}
        />
        <DropdownMenu>
          <DropdownMenuTrigger
            render={
              <Button className="w-full rounded-xl sm:w-auto" variant="outline" />
            }
          >
            {selectedStatus}
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuGroup>
              {statusOptions.map((option) => (
                <DropdownMenuItem
                  key={option.value || "all"}
                  onClick={() => {
                    setStatus(option.value);
                    setPage(1);
                  }}
                >
                  {option.label}
                </DropdownMenuItem>
              ))}
            </DropdownMenuGroup>
          </DropdownMenuContent>
        </DropdownMenu>
        <DropdownMenu>
          <DropdownMenuTrigger
            render={<Button className="w-full rounded-xl sm:w-auto" variant="outline" />}
          >
            {selectedSort}
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuGroup>
              {sortOptions.map((option) => (
                <DropdownMenuItem
                  key={option.value}
                  onClick={() => {
                    setSort(option.value);
                    setPage(1);
                  }}
                >
                  {option.label}
                </DropdownMenuItem>
              ))}
            </DropdownMenuGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      </section>

      {error && (
        <p role="alert" className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
          Could not load bins: {error}
        </p>
      )}

      <section className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Bin ID</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Fill Level</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Battery</TableHead>
              <TableHead>Last Seen</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {bins.map((bin) => (
              <TableRow key={bin.id}>
                <TableCell className="font-medium">{bin.id}</TableCell>
                <TableCell>{bin.name}</TableCell>
                <TableCell>
                  <FillLevel fill={bin.last_fill} status={bin.status} />
                </TableCell>
                <TableCell className="capitalize">{bin.status.replace("_", " ")}</TableCell>
                <TableCell>
                  {bin.last_battery === null ? "—" : `${bin.last_battery}%`}
                </TableCell>
                <TableCell
                  title={bin.last_seen_at ? new Date(bin.last_seen_at).toLocaleString() : undefined}
                >
                  {formatLastSeen(bin.last_seen_at, now)}
                </TableCell>
                <TableCell>
                  <DropdownMenu>
                    <DropdownMenuTrigger
                      render={
                        <Button
                          type="button"
                          variant="ghost"
                          className="size-8 p-0"
                          aria-label={`Actions for ${bin.id}`}
                        />
                      }
                    >
                      <MoreHorizontal size={16} />
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuGroup>
                        <DropdownMenuItem onClick={() => void handleViewBin(bin)}>
                          <Eye /> View
                        </DropdownMenuItem>
                        {canManageBins && (
                          <>
                            <DropdownMenuItem
                              onClick={() => {
                                setSelectedBin(bin);
                                setDialogError(null);
                                setDialogMode("edit");
                              }}
                            >
                              <PenLine /> Edit
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              variant="destructive"
                              onClick={() => {
                                setSelectedBin(bin);
                                setDialogError(null);
                                setDialogMode("delete");
                              }}
                            >
                              <Trash /> Delete
                            </DropdownMenuItem>
                          </>
                        )}
                      </DropdownMenuGroup>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            ))}
            {!isLoading && bins.length === 0 && !error && (
              <TableRow>
                <TableCell colSpan={7} className="py-10 text-center text-slate-500">
                  No bins match your search.
                </TableCell>
              </TableRow>
            )}
            {isLoading && bins.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="py-10 text-center text-slate-500">
                  Loading bins...
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </section>

      <div className="mt-4 flex flex-col items-center justify-between gap-3 sm:flex-row">
        <p className="text-sm text-slate-500">
          Showing {firstResult}-{lastResult} of {total}
        </p>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="outline"
            disabled={page === 1 || isLoading}
            onClick={() => setPage((current) => Math.max(1, current - 1))}
          >
            Previous
          </Button>
          <Button
            type="button"
            variant="outline"
            disabled={page * PAGE_SIZE >= total || isLoading}
            onClick={() => setPage((current) => current + 1)}
          >
            Next
          </Button>
        </div>
      </div>

      <Dialog
        open={dialogMode === "view" || dialogMode === "delete"}
        onOpenChange={(open) => {
          if (!open) closeDialog();
        }}
      >
        <DialogContent>
          {dialogMode === "view" && (
            <>
              <DialogHeader>
                <DialogTitle>Bin details</DialogTitle>
                <DialogDescription>
                  {selectedBin ? `${selectedBin.id} - ${selectedBin.name}` : "Loading bin details."}
                </DialogDescription>
              </DialogHeader>
              {isDetailLoading && <p className="text-sm text-slate-500">Loading details...</p>}
              {selectedBin && !isDetailLoading && (
                <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
                  <dt className="text-slate-500">Status</dt>
                  <dd className="capitalize">{selectedBin.status.replace("_", " ")}</dd>
                  <dt className="text-slate-500">Fill level</dt>
                  <dd>{selectedBin.last_fill === null ? "—" : `${selectedBin.last_fill}%`}</dd>
                  <dt className="text-slate-500">Battery</dt>
                  <dd>
                    {selectedBin.last_battery === null
                      ? "—"
                      : `${selectedBin.last_battery}%`}
                  </dd>
                  <dt className="text-slate-500">Location</dt>
                  <dd>
                    {selectedBin.location.lat}, {selectedBin.location.lng}
                  </dd>
                  <dt className="text-slate-500">Bin capacity</dt>
                  <dd>
                    {selectedBin.depth_cm} cm / {selectedBin.volume_l} L
                  </dd>
                  <dt className="text-slate-500">Sensor ID</dt>
                  <dd>{selectedBin.sensor_id ?? "Not assigned"}</dd>
                  <dt className="text-slate-500">Last seen</dt>
                  <dd>{formatLastSeen(selectedBin.last_seen_at, now)}</dd>
                  <dt className="text-slate-500">Maintenance</dt>
                  <dd>{selectedBin.maintenance ? "On" : "Off"}</dd>
                </dl>
              )}
              {dialogError && (
                <p role="alert" className="text-sm text-red-700">{dialogError}</p>
              )}
            </>
          )}

          {dialogMode === "delete" && selectedBin && (
            <>
              <DialogHeader>
                <DialogTitle>
                  Delete {selectedBin.id} {selectedBin.name}?
                </DialogTitle>
                <DialogDescription>This cannot be undone.</DialogDescription>
              </DialogHeader>
              {dialogError && (
                <p role="alert" className="text-sm text-red-700">{dialogError}</p>
              )}
              <DialogFooter>
                <Button type="button" variant="outline" onClick={closeDialog} disabled={isSubmitting}>
                  Cancel
                </Button>
                <Button
                  type="button"
                  variant="destructive"
                  onClick={() => void handleDeleteBin()}
                  disabled={isSubmitting}
                >
                  {isSubmitting ? "Deleting..." : "Delete"}
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>

      <BinFormDrawer
        open={dialogMode === "create" || dialogMode === "edit"}
        bin={dialogMode === "edit" ? selectedBin : null}
        onClose={closeDialog}
        onSaved={() => {
          if (dialogMode === "create") setPage(1);
          setDialogMode(null);
          setSelectedBin(null);
          refreshBins();
        }}
      />
    </main>
  );
}

export { Bins };
