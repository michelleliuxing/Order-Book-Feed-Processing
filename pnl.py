class PnLTracker:
    """
    Tracks position, realized PnL, and unrealized PnL per symbol
    using average cost basis.

    Trade interpretation (resting order perspective):
      - side='B' (bid filled) → we bought
      - side='S' (ask filled) → we sold
    """

    def __init__(self):
        self.position: int = 0
        self._total_cost: float = 0.0
        self.realized_pnl: int = 0

    @property
    def avg_cost(self) -> float:
        if self.position == 0:
            return 0.0
        return self._total_cost / abs(self.position)

    def on_trade(self, side: str, price: int, volume: int) -> None:
        signed_qty = volume if side == "B" else -volume
        new_position = self.position + signed_qty

        if self.position == 0:
            self._total_cost = price * volume
        elif (self.position > 0) == (signed_qty > 0):
            self._total_cost += price * volume
        else:
            close_qty = min(abs(signed_qty), abs(self.position))
            avg = self._total_cost / abs(self.position)

            if self.position > 0:
                self.realized_pnl += int(close_qty * (price - avg))
            else:
                self.realized_pnl += int(close_qty * (avg - price))

            remaining_old = abs(self.position) - close_qty
            flip_qty = abs(signed_qty) - close_qty

            if flip_qty > 0:
                self._total_cost = price * flip_qty
            elif remaining_old > 0:
                self._total_cost = avg * remaining_old
            else:
                self._total_cost = 0.0

        self.position = new_position

    def unrealized_pnl(self, mid_price: int) -> int:
        if self.position == 0 or mid_price == 0:
            return 0
        avg = self.avg_cost
        if self.position > 0:
            return int(self.position * (mid_price - avg))
        return int(abs(self.position) * (avg - mid_price))

    def total_pnl(self, mid_price: int) -> int:
        return self.realized_pnl + self.unrealized_pnl(mid_price)


def compute_mid_price(
    bids: list[tuple[int, int]], asks: list[tuple[int, int]]
) -> int:
    """Derive a mid-price from the top-of-book levels.
    Falls back to whichever side is available, or 0 if the book is empty."""
    best_bid = bids[0][0] if bids else 0
    best_ask = asks[0][0] if asks else 0
    if best_bid and best_ask:
        return (best_bid + best_ask) // 2
    return best_bid or best_ask
