import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { ChevronRight } from "lucide-react";

export function StatusAlerts() {
  return (
    <Card className="mt-6 col-span-2 row-span-2">
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
         
        </div>
      </CardContent>
    </Card>
  );
}
