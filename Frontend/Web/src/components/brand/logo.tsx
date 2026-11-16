import { Leaf } from "lucide-react"

function Logo() {
  return (
    <div className="flex items-center gap-3">
      <div className="flex size-10 items-center justify-center rounded-xl bg-emerald-500 text-white shadow-lg shadow-emerald-500/20">
        <Leaf size={22} strokeWidth={2.5} />
      </div>
      <div>
        <p className="text-[17px] font-bold tracking-tight text-slate-950">Waste<span className="text-emerald-500">Sense</span></p>
        <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400">Smart city platform</p>
      </div>
    </div>
  )
}

export { Logo }
