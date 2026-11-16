import {
  ChevronDown,
  ChevronRight,
  Leaf,
  MapPin,
  PackageCheck,
  Recycle,
  Truck,
} from "lucide-react";
import { Button } from "../ui/button";
import { Card, CardContent, CardHeader } from "../ui/card";
import { MetricCard } from "./metric-card";

const metrics = [
  {
    title: "Total smart bins",
    value: "248",
    change: "+12.4%",
    suffix: "active",
    icon: PackageCheck,
    iconColor: "text-blue-600",
    iconBackground: "bg-blue-50",
  },
  {
    title: "Collected today",
    value: "1,284 kg",
    change: "+8.2%",
    suffix: "vs. yesterday",
    icon: Truck,
    iconColor: "text-emerald-600",
    iconBackground: "bg-emerald-50",
  },
  {
    title: "Avg. fill level",
    value: "64%",
    change: "-3.1%",
    suffix: "this week",
    icon: Recycle,
    iconColor: "text-violet-600",
    iconBackground: "bg-violet-50",
  },
  {
    title: "CO₂ emissions saved",
    value: "2.8 t",
    change: "+18.6%",
    suffix: "this month",
    icon: Leaf,
    iconColor: "text-amber-600",
    iconBackground: "bg-amber-50",
  },
];

const bins = [
  {
    name: "Bin #204 — Central Park",
    location: "North entrance",
    fill: 92,
    status: "Needs pickup",
    color: "bg-rose-500",
  },
  {
    name: "Bin #187 — Riverside",
    location: "East walkway",
    fill: 68,
    status: "Filling up",
    color: "bg-amber-500",
  },
  {
    name: "Bin #231 — Market Street",
    location: "Food court",
    fill: 41,
    status: "Healthy",
    color: "bg-emerald-500",
  },
];

function WasteChart() {
  const heights = [54, 68, 46, 78, 64, 88, 72];
  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between">
        <div>
          <h3 className="font-bold text-slate-950">Waste collected</h3>
          <p className="mt-1 text-sm text-slate-500">
            Total weight across all locations
          </p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="gap-1 text-xs font-bold text-slate-500"
        >
          This week <ChevronDown size={14} />
        </Button>
      </CardHeader>
      <CardContent>
        <div className="flex h-48 items-end gap-3 sm:gap-6">
          {heights.map((height, index) => (
            <div
              key={index}
              className="flex h-full flex-1 flex-col items-center justify-end gap-3"
            >
              <div
                className={`w-full max-w-10 rounded-t-lg ${index === 5 ? "bg-emerald-500" : "bg-emerald-100"}`}
                style={{ height: `${height}%` }}
              />
              <span className="text-xs font-medium text-slate-400">
                {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][index]}
              </span>
            </div>
          ))}
        </div>
        <div className="mt-5 border-t border-slate-100 pt-4 text-xs text-slate-400">
          Weekly average{" "}
          <span className="font-bold text-slate-700">1,042 kg</span>
        </div>
      </CardContent>
    </Card>
  );
}

function NetworkHealth() {
  const distribution = [
    ["Healthy", "158", "bg-emerald-500"],
    ["Filling up", "51", "bg-amber-500"],
    ["Needs pickup", "39", "bg-rose-500"],
  ];
  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between">
        <div>
          <h3 className="font-bold text-slate-950">Network health</h3>
          <p className="mt-1 text-sm text-slate-500">
            Current bin distribution
          </p>
        </div>
        <Button
          variant="link"
          className="p-0 text-xs font-bold text-emerald-600"
        >
          View details
        </Button>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-8">
          <div
            className="relative flex size-36 shrink-0 items-center justify-center rounded-full"
            style={{
              background:
                "conic-gradient(#10b981 0 64%, #f59e0b 64% 84%, #f43f5e 84% 100%)",
            }}
          >
            <div className="flex size-24 flex-col items-center justify-center rounded-full bg-white">
              <span className="text-2xl font-bold">248</span>
              <span className="text-[10px] text-slate-400">total bins</span>
            </div>
          </div>
          <div className="space-y-3 text-sm">
            {distribution.map(([label, count, color]) => (
              <div key={label} className="flex items-center gap-2">
                <span className={`size-2.5 rounded-full ${color}`} />
                <span className="w-20 text-slate-500">{label}</span>
                <b>{count}</b>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function AttentionBins() {
  return (
    <Card className="mt-6">
      <CardHeader className="mb-5 flex-row items-center justify-between">
        <div>
          <h3 className="font-bold text-slate-950">Bins requiring attention</h3>
          <p className="mt-1 text-sm text-slate-500">
            Prioritized by fill level
          </p>
        </div>
        <Button
          variant="link"
          className="gap-1 p-0 text-sm font-bold text-emerald-600"
        >
          View all <ChevronRight size={16} />
        </Button>
      </CardHeader>
      <CardContent>
        <div className="grid gap-3 md:grid-cols-3">
          {bins.map((bin) => (
            <div
              key={bin.name}
              className="rounded-xl border border-slate-100 bg-slate-50/60 p-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-bold text-slate-800">{bin.name}</p>
                  <p className="mt-1 flex items-center gap-1 text-xs text-slate-400">
                    <MapPin size={12} />
                    {bin.location}
                  </p>
                </div>
                <span className={`size-2 rounded-full ${bin.color}`} />
              </div>
              <div className="mt-4 flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-500">Fill level</span>
                <span className="font-bold text-slate-700">{bin.fill}%</span>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200">
                <div
                  className={`h-full rounded-full ${bin.color}`}
                  style={{ width: `${bin.fill}%` }}
                />
              </div>
              <p className="mt-3 text-xs font-semibold text-slate-500">
                {bin.status}
              </p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function Dashboard() {
  return (
    <main className="mx-auto max-w-[1440px] px-5 py-8 sm:px-8">
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-2 flex items-center gap-2 text-sm font-semibold text-emerald-600">
            <span className="size-2 rounded-full bg-emerald-500" /> All systems
            operational
          </p>
          <h2 className="text-3xl font-bold tracking-tight text-slate-950">
            Good morning, Jordan <span aria-hidden="true">👋</span>
          </h2>
          <p className="mt-2 text-sm text-slate-500">
            Here’s what’s happening across your waste network today.
          </p>
        </div>
        <Button
          variant="outline"
          className="gap-2 rounded-xl font-bold text-slate-600"
        >
          <MapPin size={16} /> All locations <ChevronDown size={15} />
        </Button>
      </div>
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => (
          <MetricCard key={metric.title} {...metric} />
        ))}
      </section>
      <section className="mt-6 grid gap-6 xl:grid-cols-[1.4fr_1fr]">
        <WasteChart />
        <NetworkHealth />
      </section>
      <AttentionBins />
    </main>
  );
}

export { Dashboard };
