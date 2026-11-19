import { Card } from "../ui/card";

type MetricCardProps = {
  title: string;
  value: string;
  change: string;
  suffix: string;
};

function MetricCard({ title, value, change, suffix }: MetricCardProps) {
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-base text-gray-500">{title}</p>
          <p className="mt-3 text-4xl font-bold tracking-tight text-slate-950">
            {value}
          </p>
        </div>
      </div>
      <p className="mt-4 text-xs font-small text-slate-500">
        <span
          className={`mr-1 font-bold ${change.startsWith("-") ? "text-rose-500" : "text-emerald-600"}`}
        >
          {change}
        </span>
        {suffix}
      </p>
    </Card>
  );
}

export { MetricCard };
