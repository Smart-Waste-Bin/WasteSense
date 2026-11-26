import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Table, TableHead, TableHeader, TableRow } from "@/components/ui/table";

function Bins() {
  return (
    <main className="mx-auto w-full max-w-[1440px] min-w-0 px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
      <div className="mb-8 flex flex-col items-start justify-between gap-5 sm:flex-row sm:items-end">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">
            Bins
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            10 bins • 9 reporting • 5 need collection
          </p>
        </div>
        <Button className="rounded-xl">Add Bin</Button>
      </div>
      <section className="mb-8 flex flex-col items-start gap-2 sm:flex-row sm:items-center">
        <Input type="text" className="w-100" placeholder="Search bins..." />
        <DropdownMenu>
          <DropdownMenuTrigger>
            <Button className="ml-2 rounded-xl w-full" variant="outline">
              Bin Status
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuGroup>
              <DropdownMenuItem>All </DropdownMenuItem>
              <DropdownMenuItem>Urgent</DropdownMenuItem>
              <DropdownMenuItem>Normal</DropdownMenuItem>
              <DropdownMenuItem>Due</DropdownMenuItem>
              <DropdownMenuItem>Filling</DropdownMenuItem>
            </DropdownMenuGroup>
          </DropdownMenuContent>
        </DropdownMenu>
        <DropdownMenu>
          <DropdownMenuTrigger>
            <Button className="ml-2 rounded-xl w-20" variant="outline">
              Sort
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuGroup>
              <DropdownMenuItem>Low to High</DropdownMenuItem>
              <DropdownMenuItem>High to Low</DropdownMenuItem>
            </DropdownMenuGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      </section>
      <section>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Bin ID</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Location</TableHead>
              <TableHead>Fill Level</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Battery</TableHead>
              <TableHead>Last Seen</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
        </Table>
      </section>
    </main>
  );
}

export { Bins };
