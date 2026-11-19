import { Map, Route } from "lucide-react";
import { Button } from "../ui/button";
import { MetricCard } from "./metric-card";
import { CampusMap } from "./campus-map";
import { ActiveCard } from "./active-card";
import { StatusAlerts } from "./status-alerts";

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
      <section className="my-4 grid grid-flow-col grid-rows-3 gap-2">
        <CampusMap />
        <ActiveCard />
        <StatusAlerts />
      </section>
    </main>
  );
}

export { Dashboard };
