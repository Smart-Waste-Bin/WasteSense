import type { LucideIcon } from "lucide-react"
import { Card } from "../ui/card"

type MetricCardProps = {
  title: string
  value: string
  change: string
  suffix: string
  icon: LucideIcon
  iconColor: string
  iconBackground: string
}

function MetricCard({ title, value, change, suffix, icon: Icon, iconColor, iconBackground }: MetricCardProps) {
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between"><div><p className="text-sm font-medium text-slate-500">{title}</p><p className="mt-3 text-2xl font-bold tracking-tight text-slate-950">{value}</p></div><div className={`rounded-xl p-2.5 ${iconBackground}`}><Icon size={20} className={iconColor} /></div></div>
      <p className="mt-4 text-xs text-slate-400"><span className={`mr-1 font-bold ${change.startsWith("-") ? "text-rose-500" : "text-emerald-600"}`}>{change}</span>{suffix}</p>
    </Card>
  )
}

export { MetricCard }
