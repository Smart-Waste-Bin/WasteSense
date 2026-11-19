
import { Card, CardContent, CardHeader } from "@/components/ui/card";

export function ActiveCard() {
 
  return (
    <Card className="col-span-3">
      <CardHeader className="flex-row items-start justify-between">
        <div>
          <h3 className="font-bold text-xl text-slate-950">Active bins</h3>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex gap-2 -my-2">
          <h1 className="text-white items-center justify-center rounded-full bg-green-500 p-2 text-sm font-bold">
            JD
          </h1>
          <div className="text-sm">
            <p className="font-bold ">
              Peter Owusu - 4 of 6 stops done
            </p>
            <p className="text-muted-foreground text-xs">
              Truck GR-2041-24 · next • College of Engineering
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
