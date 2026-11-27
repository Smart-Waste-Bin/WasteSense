import { useEffect, useState, type FormEvent } from "react";
import {
  createBin,
  deleteBin,
  getBin,
  getBins,
  updateBin,
  type BinRecord,
} from "@/auth";
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
import { Eye, PenLine, Trash } from "lucide-react";

type BinsProps = {
  userRole: string;
};

type DialogMode = "create" | "edit" | "view" | "delete" | null;

type BinFormValues = {
  id: string;
  name: string;
  lat: string;
  lng: string;
  depth_cm: string;
  volume_l: string;
  sensor_id: string;
  is_physical: boolean;
  maintenance: boolean;
  due_threshold: string;
  urgent_threshold: string;
};

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

function emptyForm(): BinFormValues {
  return {
    id: "",
    name: "",
    lat: "",
    lng: "",
    depth_cm: "",
    volume_l: "",
    sensor_id: "",
    is_physical: false,
    maintenance: false,
    due_threshold: "",
    urgent_threshold: "",
  };
}

function formFromBin(bin: BinRecord): BinFormValues {
  return {
    id: bin.id,
    name: bin.name,
    lat: String(bin.location.lat),
    lng: String(bin.location.lng),
    depth_cm: String(bin.depth_cm),
    volume_l: String(bin.volume_l),
    sensor_id: bin.sensor_id ?? "",
    is_physical: bin.is_physical,
    maintenance: bin.maintenance,
    due_threshold: bin.due_threshold === null ? "" : String(bin.due_threshold),
    urgent_threshold: bin.urgent_threshold === null ? "" : String(bin.urgent_threshold),
  };
}

function formatLastSeen(value: string | null) {
  if (!value) return "Never";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString();
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
  const [form, setForm] = useState<BinFormValues>(emptyForm);
  const [dialogError, setDialogError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDetailLoading, setIsDetailLoading] = useState(false);

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

  const updateForm = <K extends keyof BinFormValues,>(
    key: K,
    value: BinFormValues[K],
  ) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

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

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setDialogError(null);

    const input = {
      name: form.name.trim(),
      location: { lat: Number(form.lat), lng: Number(form.lng) },
      depth_cm: Number(form.depth_cm),
      volume_l: Number(form.volume_l),
      sensor_id: form.sensor_id.trim() || null,
      is_physical: form.is_physical,
      due_threshold: form.due_threshold.trim() ? Number(form.due_threshold) : null,
      urgent_threshold: form.urgent_threshold.trim()
        ? Number(form.urgent_threshold)
        : null,
    };

    try {
      if (dialogMode === "create") {
        await createBin({
          ...input,
          ...(form.id.trim() ? { id: form.id.trim() } : {}),
        });
        setPage(1);
      } else if (dialogMode === "edit" && selectedBin) {
        await updateBin(selectedBin.id, {
          ...input,
          maintenance: form.maintenance,
        });
      } else {
        return;
      }

      setDialogMode(null);
      setSelectedBin(null);
      setRefreshKey((current) => current + 1);
    } catch (saveError) {
      setDialogError(
        saveError instanceof Error ? saveError.message : "Unable to save this bin.",
      );
    } finally {
      setIsSubmitting(false);
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
              setForm(emptyForm());
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
              <TableHead>Location</TableHead>
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
                  {bin.location.lat.toFixed(5)}, {bin.location.lng.toFixed(5)}
                </TableCell>
                <TableCell>{bin.last_fill === null ? "—" : `${bin.last_fill}%`}</TableCell>
                <TableCell className="capitalize">{bin.status.replace("_", " ")}</TableCell>
                <TableCell>
                  {bin.last_battery === null ? "—" : `${bin.last_battery}%`}
                </TableCell>
                <TableCell>{formatLastSeen(bin.last_seen_at)}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      className="size-8 p-0"
                      aria-label={`View ${bin.id}`}
                      title="View bin"
                      onClick={() => void handleViewBin(bin)}
                    >
                      <Eye size={16} />
                    </Button>
                    {canManageBins && (
                      <>
                        <Button
                          type="button"
                          variant="outline"
                          className="size-8 p-0"
                          aria-label={`Edit ${bin.id}`}
                          title="Edit bin"
                          onClick={() => {
                            setSelectedBin(bin);
                            setForm(formFromBin(bin));
                            setDialogError(null);
                            setDialogMode("edit");
                          }}
                        >
                          <PenLine size={16} />
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          className="size-8 p-0"
                          aria-label={`Delete ${bin.id}`}
                          title="Delete bin"
                          onClick={() => {
                            setSelectedBin(bin);
                            setDialogError(null);
                            setDialogMode("delete");
                          }}
                        >
                          <Trash size={16} />
                        </Button>
                      </>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))}
            {!isLoading && bins.length === 0 && !error && (
              <TableRow>
                <TableCell colSpan={8} className="py-10 text-center text-slate-500">
                  No bins match your search.
                </TableCell>
              </TableRow>
            )}
            {isLoading && bins.length === 0 && (
              <TableRow>
                <TableCell colSpan={8} className="py-10 text-center text-slate-500">
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
        open={dialogMode !== null}
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
                  <dd>{formatLastSeen(selectedBin.last_seen_at)}</dd>
                  <dt className="text-slate-500">Maintenance</dt>
                  <dd>{selectedBin.maintenance ? "On" : "Off"}</dd>
                </dl>
              )}
              {dialogError && (
                <p role="alert" className="text-sm text-red-700">{dialogError}</p>
              )}
            </>
          )}

          {(dialogMode === "create" || dialogMode === "edit") && (
            <>
              <DialogHeader>
                <DialogTitle>{dialogMode === "create" ? "Add bin" : "Edit bin"}</DialogTitle>
                <DialogDescription>
                  Enter the bin's location and capacity details.
                </DialogDescription>
              </DialogHeader>
              <form id="bin-form" onSubmit={handleSubmit} className="space-y-4">
                {dialogMode === "create" && (
                  <label className="block space-y-1.5 text-sm font-medium">
                    Bin ID (optional)
                    <Input
                      value={form.id}
                      placeholder="Auto-assign if blank"
                      onChange={(event) => updateForm("id", event.target.value)}
                    />
                  </label>
                )}
                <label className="block space-y-1.5 text-sm font-medium">
                  Name
                  <Input
                    required
                    value={form.name}
                    onChange={(event) => updateForm("name", event.target.value)}
                  />
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <label className="block space-y-1.5 text-sm font-medium">
                    Latitude
                    <Input
                      required
                      type="number"
                      min="-90"
                      max="90"
                      step="any"
                      value={form.lat}
                      onChange={(event) => updateForm("lat", event.target.value)}
                    />
                  </label>
                  <label className="block space-y-1.5 text-sm font-medium">
                    Longitude
                    <Input
                      required
                      type="number"
                      min="-180"
                      max="180"
                      step="any"
                      value={form.lng}
                      onChange={(event) => updateForm("lng", event.target.value)}
                    />
                  </label>
                  <label className="block space-y-1.5 text-sm font-medium">
                    Depth (cm)
                    <Input
                      required
                      type="number"
                      min="0.01"
                      step="any"
                      value={form.depth_cm}
                      onChange={(event) => updateForm("depth_cm", event.target.value)}
                    />
                  </label>
                  <label className="block space-y-1.5 text-sm font-medium">
                    Capacity (L)
                    <Input
                      required
                      type="number"
                      min="0.01"
                      step="any"
                      value={form.volume_l}
                      onChange={(event) => updateForm("volume_l", event.target.value)}
                    />
                  </label>
                </div>
                <label className="block space-y-1.5 text-sm font-medium">
                  Sensor ID (optional)
                  <Input
                    value={form.sensor_id}
                    onChange={(event) => updateForm("sensor_id", event.target.value)}
                  />
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <label className="block space-y-1.5 text-sm font-medium">
                    Due threshold (%)
                    <Input
                      type="number"
                      min="0"
                      max="100"
                      step="any"
                      value={form.due_threshold}
                      onChange={(event) => updateForm("due_threshold", event.target.value)}
                    />
                  </label>
                  <label className="block space-y-1.5 text-sm font-medium">
                    Urgent threshold (%)
                    <Input
                      type="number"
                      min="0"
                      max="100"
                      step="any"
                      value={form.urgent_threshold}
                      onChange={(event) => updateForm("urgent_threshold", event.target.value)}
                    />
                  </label>
                </div>
                <div className="flex flex-wrap gap-5 text-sm">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={form.is_physical}
                      onChange={(event) => updateForm("is_physical", event.target.checked)}
                    />
                    Physical bin
                  </label>
                  {dialogMode === "edit" && (
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={form.maintenance}
                        onChange={(event) => updateForm("maintenance", event.target.checked)}
                      />
                      Maintenance mode
                    </label>
                  )}
                </div>
                {dialogError && (
                  <p role="alert" className="text-sm text-red-700">{dialogError}</p>
                )}
              </form>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={closeDialog} disabled={isSubmitting}>
                  Cancel
                </Button>
                <Button type="submit" form="bin-form" disabled={isSubmitting}>
                  {isSubmitting
                    ? "Saving..."
                    : dialogMode === "create"
                      ? "Create bin"
                      : "Save changes"}
                </Button>
              </DialogFooter>
            </>
          )}

          {dialogMode === "delete" && selectedBin && (
            <>
              <DialogHeader>
                <DialogTitle>Delete bin?</DialogTitle>
                <DialogDescription>
                  {selectedBin.id} ({selectedBin.name}) will be removed from the active bins list.
                  Existing readings will be kept.
                </DialogDescription>
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
                  {isSubmitting ? "Deleting..." : "Delete bin"}
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </main>
  );
}

export { Bins };
