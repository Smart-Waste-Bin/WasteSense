import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { AlertTriangle, CircleAlert } from "lucide-react";

type BinStatus = {
  id: number;
  label: string;
  count: number;
  color: string;
};

type StatusAlert = {
  id: number;
  title: string;
  description: string;
  time: string;
};

type StatusAlertsProps = {
  bins: BinStatus[];
  alerts: StatusAlert[];
};

export function StatusAlerts({ bins, alerts }: StatusAlertsProps) {
  return (
    <div>
      <Card className="">
        <CardHeader className="pb-2">
          <h3 className="text-xs font-medium uppercase tracking-wide text-slate-700">
            Bins by Status
          </h3>
        </CardHeader>
        <CardContent>
          <div className="flex h-2 gap-1 overflow-hidden rounded-full">
            {bins.map((bin) => (
              <div
                key={bin.id}
                className="min-w-0"
                style={{
                  backgroundColor: bin.color,
                  flexGrow: bin.count,
                }}
              />
            ))}
          </div>
          <ul className="mt-3 space-y-2">
            {bins.map((bin) => (
              <li
                key={bin.id}
                className="flex items-center justify-between text-xs text-slate-700"
              >
                <span className="flex items-center gap-2">
                  <span
                    className="size-2.5 rounded-full"
                    style={{ backgroundColor: bin.color }}
                  />
                  {bin.label}
                </span>
                <span className="font-bold text-slate-950">{bin.count}</span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
      <Card className="mt-2">
        <CardHeader>
          <h3 className="text-xs font-medium uppercase tracking-wide text-slate-700">
            Recent Alerts
          </h3>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {alerts.map((alert) => (
              <div key={alert.id} className="flex gap-3">
                <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-amber-50 text-amber-600">
                  {alert.title === "Bin Full" ? (
                    <AlertTriangle size={16} />
                  ) : (
                    <CircleAlert size={16} />
                  )}
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-bold text-slate-950">{alert.title}</p>
                  <p className="mt-1 text-xs text-slate-500">{alert.description}</p>
                  <p className="mt-1 text-[11px] text-slate-400">{alert.time}</p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export type { BinStatus, StatusAlert, StatusAlertsProps };
