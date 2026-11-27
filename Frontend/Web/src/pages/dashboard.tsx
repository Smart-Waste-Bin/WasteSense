import { useEffect, useState } from "react";
import { Map, Route } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Button } from "../components/ui/button";
import { MetricCard } from "../components/dashboard/metric-card";
import { CampusMap } from "../components/dashboard/campus-map";
import { ActiveCard } from "../components/dashboard/active-card";
import { StatusAlerts, type BinStatus, type StatusAlert } from "./../components/dashboard/status-alerts";
import { getOverviewStats, type OverviewStats } from "../auth";
import { useLiveBins } from "../hooks/use-live-bins";
import type { Bin } from "../lib/bins";
import { STATUS_THEME } from "../lib/theme";

// Most urgent first. Labels and colours come from lib/theme.ts, the same as the live map.
const STATUS_ORDER = ["urgent", "due", "filling", "normal", "offline", "maintenance"] as const;

// Counts the bins in each status. Bins come from GET /api/bins and stay live over the WebSocket.
function countByStatus(bins: Bin[]): BinStatus[] {
  return STATUS_ORDER.map((status, index) => ({
    id: index + 1,
    label: STATUS_THEME[status].label,
    count: bins.filter((bin) => bin.status === status).length,
    color: STATUS_THEME[status].color,
  }));
}

const statusAlerts: StatusAlert[] = [
  {
    id: 1,
    title: "Bin Full",
    description: "Library entrance bin is at 92% capacity",
    time: "8 minutes ago",
  },
  {
    id: 2,
    title: "Collection Delay",
    description: "Scheduled collection delayed by 30 minutes",
    time: "24 minutes ago",
  },
  {
    id: 3,
    title: "Route Deviation",
    description: "Driver has deviated from the planned route",
    time: "41 minutes ago",
  },
];

function formatDistanceSaved(distanceMeters: number) {
  const distanceKm = (distanceMeters / 1000).toFixed(2).replace(/\.?0+$/, "");
  return `${distanceKm} km`;
}

type DashboardProps = {
  userName: string;
};

function Dashboard({ userName }: DashboardProps) {
  const firstName = userName.trim().split(/\s+/)[0];
  const navigate = useNavigate();
  const { data: bins = [] } = useLiveBins();
  const statusBins = countByStatus(bins);

  const [stats, setStats] = useState<OverviewStats | null>(null);
  const [statsError, setStatsError] = useState<string | null>(null);

  useEffect(() => {
    let isCurrent = true;

    getOverviewStats()
      .then((overviewStats) => {
        if (isCurrent) setStats(overviewStats);
      })
      .catch((error: unknown) => {
        if (isCurrent) {
          setStatsError(
            error instanceof Error ? error.message : "Unable to load overview data.",
          );
        }
      });

    return () => {
      isCurrent = false;
    };
  }, []);

  const metrics = [
    {
      title: "Total bins",
      value: stats ? String(stats.total_bins) : "—",
      change: stats ? String(Math.max(0, stats.total_bins - stats.offline)) : "",
      suffix: "reporting",
    },
    {
      title: "Need collection",
      value: stats ? String(stats.needing_collection) : "—",
      change: "",
      suffix: "due or urgent",
    },
    {
      title: "Offline sensors",
      value: stats ? String(stats.offline) : "—",
      change: "",
      suffix: "currently offline",
    },
    {
      title: "Collection today",
      value: stats ? String(stats.collections_today) : "—",
      change: "",
      suffix: "completed",
    },
    {
      title: "Distance saved this week",
      value: stats ? formatDistanceSaved(stats.distance_saved_week_m) : "—",
      change: "",
      suffix: "this week",
    },
  ];

  return (
    <main className="mx-auto w-full max-w-[1440px] min-w-0 px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
      <div className="mb-8 flex flex-col items-start justify-between gap-5 sm:flex-row sm:items-end">
        <div className="min-w-0">
          <h2 className="text-3xl font-bold tracking-tight text-slate-950">
            Good morning, {firstName} <span aria-hidden="true">👋</span>
          </h2>
          <p className="mt-2 text-sm text-slate-500">
            {stats
              ? `${stats.needing_collection} bins need collection today`
              : statsError
                ? "Overview data unavailable"
                : "Loading overview data..."}
          </p>
        </div>
        <div className="flex w-full flex-col gap-3 sm:w-auto sm:flex-row sm:items-center">
          <Button
            variant="outline"
            className="w-full gap-2 rounded-xl font-bold text-slate-600 sm:w-auto"
            onClick={() => navigate("/live-map")}
          >
            <Map size={16} /> Open live map
          </Button>
          <Button className="w-full rounded-xl sm:w-auto">
            <Route />
            Plan collection route
          </Button>
        </div>
      </div>
      {statsError && (
        <p
          role="alert"
          className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          Could not load overview stats: {statsError}
        </p>
      )}
      <section className="grid gap-4 sm:grid-cols-3 xl:grid-cols-5">
        {metrics.map((metric) => (
          <MetricCard key={metric.title} {...metric} />
        ))}
      </section>
      <section className="my-4 grid grid-cols-1 md:grid-cols-3 gap-2">
        <CampusMap />
        <ActiveCard />
        <StatusAlerts bins={statusBins} alerts={statusAlerts} />
      </section>
    </main>
  );
}

export { Dashboard };
