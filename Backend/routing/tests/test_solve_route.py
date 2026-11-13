from routing import solve_route


def test_solve_route_returns_bin_ids_in_order():
    bins = [
        {"id": 1, "lat": 6.67, "lon": -1.57},
        {"id": 2, "lat": 6.68, "lon": -1.56},
    ]
    assert solve_route((6.67, -1.57), bins) == [1, 2]
