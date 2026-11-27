import { useQuery, useQueryClient } from "@tanstack/react-query"
import { applyBinUpdate, BINS_QUERY_KEY, fetchBins, type Bin, type BinUpdate } from "@/lib/bins"
import { useLiveEvents } from "./use-live-events"

// All bins, kept up to date by bin_updated events. The bins list page (WEB-04) should use
// this hook too, so the map and the list always show the same data.
export function useLiveBins() {
  const queryClient = useQueryClient()
  const query = useQuery({ queryKey: BINS_QUERY_KEY, queryFn: fetchBins })

  useLiveEvents(
    (event) => {
      if (event.type !== "bin_updated") return
      const update = event.data as BinUpdate
      const bins = queryClient.getQueryData<Bin[]>(BINS_QUERY_KEY)
      if (!bins) return
      const updated = applyBinUpdate(bins, update)
      if (updated) {
        queryClient.setQueryData(BINS_QUERY_KEY, updated)
      } else {
        // A bin we don't have yet. The event has no name or location, so load the list again.
        void queryClient.invalidateQueries({ queryKey: BINS_QUERY_KEY })
      }
    },
    () => void queryClient.invalidateQueries({ queryKey: BINS_QUERY_KEY }),
  )

  return query
}
