import { Card, CardHeader } from "@/components/ui/card";

export function CampusMap() {
  return (
    <Card className="row-span-3">
      <CardHeader className="flex-row items-start justify-between">
        <div>
          <h3 className="font-bold text-xl text-slate-950">Campus map</h3>
        </div>
      </CardHeader>
    </Card>
  );
}