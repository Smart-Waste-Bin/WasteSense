import { Map, Route } from "lucide-react";
import { Button } from "../ui/button";
import { MetricCard } from "./metric-card";
import { CampusMap } from "./campus-map";
import { ActiveCard } from "./active-card";
import { StatusAlerts, type BinStatus, type StatusAlert } from "./status-alerts";

const metrics = [
  {
    title: "Total bins",
    value: "10",
    change: "9",
    suffix: "reporting",
  },
  {
    title: "Need collection",
    value: "5",
    change: "2",
    suffix: "urgent",
  },
  {
    title: "Offline sensors",
    value: "1",
    change: "",
    suffix: "Pharmacy block",
  },
  {
    title: "Collection today",
    value: "12",
    change: "+3",
    suffix: "vs yesterday",
  },
  {
    title: "Distance saved this week",
    value: "18.4 km",
    change: "32%",
    suffix: "less than fixed route",
  },
];

const statusBins: BinStatus[] = [
  {
    id: 1,
    label: "Urgent",
    count: 2,
    color: "#ef4444",
  },
  {
    id: 2,
    label: "Due",
    count: 3,
    color: "#df5b2c",
  },
  {
    id: 3,
    label: "Filling",
    count: 1,
    color: "#f5a623",
  },
  {
    id: 4,
    label: "Normal",
    count: 3,
    color: "#5b9f1f",
  },
  {
    id: 5,
    label: "Offline",
    count: 1,
    color: "#8b8b85",
  },
];

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

function Dashboard() {
  return (
    <main className="mx-auto w-full max-w-[1440px] min-w-0 px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
      <div className="mb-8 flex flex-col items-start justify-between gap-5 sm:flex-row sm:items-end">
        <div className="min-w-0">
          <h2 className="text-3xl font-bold tracking-tight text-slate-950">
            Good morning, Jordan <span aria-hidden="true">👋</span>
          </h2>
          <p className="mt-2 text-sm text-slate-500">
            Monday, 12 February 2025 • 5 bins need collection today
          </p>
        </div>
        <div className="flex w-full flex-col gap-3 sm:w-auto sm:flex-row sm:items-center">
          <Button
            variant="outline"
            className="w-full gap-2 rounded-xl font-bold text-slate-600 sm:w-auto"
          >
            <Map size={16} /> Open live map
          </Button>
          <Button className="w-full rounded-xl sm:w-auto">
            <Route />
            Plan collection route
          </Button>
        </div>
      </div>
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
