import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Progress } from "./progress";

export function ActiveCard() {
  return (
    <Card className="">
      <CardHeader className="flex-row items-start justify-between">
        <div>
          <h3 className="text-xs font-medium uppercase tracking-wide text-slate-700">
            Active Route
          </h3>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex gap-2 -my-2">
          <div className="p-1">
            <h1 className="text-white items-center justify-center rounded-full bg-green-500 p-2.5 text-sm font-bold">
              JD
            </h1>
          </div>
          <div className="text-xs ">
            <p className="font-bold my-1 text-sm">Peter Owusu - 4 of 6 stops done</p>
            <p className="text-muted-foreground ">
              Truck GR-2041-24
              <p>Next • College of Engineering</p>
            </p>
          </div>
        </div>
        <div className="mt-6">
          <Progress value={56} className="" />
        </div>
        <div className="mt-2 flex items-center justify-between">
          <p className="text-[10px] text-slate-500">4.1 km of 6 km</p>
          <p className="text-[10px] text-slate-500">ETA 09:30 AM</p>
        </div>
      </CardContent>
    </Card>
  );
}
