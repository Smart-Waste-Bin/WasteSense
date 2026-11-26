import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { BinMap } from "@/components/map/bin-map";
import { useLiveBins } from "@/hooks/use-live-bins";

// A small live map of every bin. Same data as the Live Map page (one shared query and socket).
export function CampusMap() {
  const { data: bins = [], isPending, isError } = useLiveBins();

  return (
    <Card className="flex flex-col md:col-span-2 md:row-span-2">
      <CardHeader className="flex-row items-start justify-between">
        <h3 className="font-bold text-xl text-slate-950">Campus map</h3>
        <Link to="/live-map" className="text-sm font-semibold text-emerald-700 hover:underline">
          Open live map
        </Link>
      </CardHeader>
      {/* The map grows to fill the card (the card is as tall as the cards beside it), 360px at least. */}
      <CardContent className="flex-1">
        <div className="relative h-full min-h-[360px] overflow-hidden rounded-xl border border-slate-200">
          <div className="absolute inset-0">
            <BinMap bins={bins} />
          </div>
          {(isPending || isError) && (
            <p className="absolute inset-0 z-[1000] flex items-center justify-center bg-white/60 text-sm font-semibold text-slate-600">
              {isPending ? "Loading bins..." : "Could not load bins."}
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
