def solve_route(depot, bins):
    """Return the order in which the truck should visit the bins.

    depot: (lat, lon) of the starting point
    bins:  list of dicts like {"id": 1, "lat": 6.67, "lon": -1.57}

    TODO: build a distance matrix with OSRM and solve with OR-Tools.
    For now it just returns the bins in the order given.
    """
    return [b["id"] for b in bins]
