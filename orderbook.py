class OrderBook:
    """
    Maintains all orders for a single symbol and computes price depth snapshots.
    Two flat dictionaries (one per side) mapping order_id -> (price, volume). 
    This gives O(1) lookup for add, update, delete, and trade operations, which all reference orders by their ID.
    """

    def __init__(self):
        # order_id -> (price, volume)
        self._bids: dict[int, tuple[int, int]] = {}
        self._asks: dict[int, tuple[int, int]] = {}

    # Private method for quick order dict return based on side char ('B' or 'S')
    def _side(self, side: str) -> dict[int, tuple[int, int]]:
        return self._bids if side == "B" else self._asks

    # Insert a new order into the book - 'A'
    def add(self, order_id: int, side: str, price: int, volume: int) -> None:
        self._side(side)[order_id] = (price, volume)

    # Update an existing order by replacing its price and volume - 'U'
    def update(self, order_id: int, side: str, price: int, volume: int) -> None:
        self._side(side)[order_id] = (price, volume)

    # Remove an order entirely from the book - 'D'
    def delete(self, order_id: int, side: str) -> None:
        # Use pop to delete order with non-existent order handling
        self._side(side).pop(order_id, None)

    # Reduce an order's volumn by traded amount - 'E'
    def trade(self, order_id: int, side: str, traded_volume: int) -> None:
        orders = self._side(side)
        if order_id not in orders:
            return
        price, current_volume = orders[order_id]
        remaining = current_volume - traded_volume
        if remaining <= 0:
            # Fully traded — remove from book
            del orders[order_id]
        else:
            # Partially traded — update with reduced volume, same price
            orders[order_id] = (price, remaining)

    def depth(self, levels: int) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
        # Return top-N (bids, asks) aggregated by price
        bids = _aggregate(self._bids, True, levels)  # Bids: descending price
        asks = _aggregate(self._asks, False, levels)  # Asks: ascending price
        return bids, asks


# Aggregate individual orders into price-level depth entries.
def _aggregate(
    orders: dict[int, tuple[int, int]], reverse: bool, limit: int
) -> list[tuple[int, int]]:
    # Step 1: aggregate volumes by price
    totals: dict[int, int] = {}
    for price, volume in orders.values():
        totals[price] = totals.get(price, 0) + volume

    # Step 2: filter out price levels with zero volume
    filtered = []
    for price, volume in totals.items():
        if volume != 0:
            filtered.append((price, volume))

    # Step 3: sort by price
    sorted_levels = sorted(filtered, reverse=reverse)

    # Step 4: take only the top N levels
    return sorted_levels[:limit]


# Aggregate individual orders into price-level depth entries.
def _aggregate(
    orders: dict[int, tuple[int, int]], reverse: bool, limit: int
) -> list[tuple[int, int]]:
    # Step 1: aggregate volumes by price
    totals: dict[int, int] = {}
    for price, volume in orders.values():
        totals[price] = totals.get(price, 0) + volume

    # Step 2: filter out price levels with zero volume
    filtered = []
    for price, volume in totals.items():
        if volume != 0:
            filtered.append((price, volume))

    # Step 3: sort by price
    sorted_levels = sorted(filtered, reverse=reverse)

    # Step 4: take only the top N levels
    return sorted_levels[:limit]
