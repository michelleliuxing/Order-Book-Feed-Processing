import sys
import message
from orderbook import OrderBook
from pnl import PnLTracker, compute_mid_price


def main():
    depth = int(sys.argv[1]) if len(sys.argv) > 1 else 5

    books: dict[str, OrderBook] = {}
    trackers: dict[str, PnLTracker] = {}
    last_snapshots: dict[str, tuple] = {}

    for header, msg in message.gen_from(sys.stdin.buffer):
        symbol = msg.symbol

        if symbol not in books:
            books[symbol] = OrderBook()
            trackers[symbol] = PnLTracker()

        book = books[symbol]
        tracker = trackers[symbol]

        if header.msg_type == "A":
            book.add(msg.order_id, msg.side, msg.price, msg.volume)
        elif header.msg_type == "U":
            book.update(msg.order_id, msg.side, msg.price, msg.volume)
        elif header.msg_type == "D":
            book.delete(msg.order_id, msg.side)
        elif header.msg_type == "E":
            trade_price = book.trade(msg.order_id, msg.side, msg.volume)
            if trade_price is not None:
                tracker.on_trade(msg.side, trade_price, msg.volume)

        bids, asks = book.depth(depth)
        mid = compute_mid_price(bids, asks)

        full_snapshot = (bids, asks, tracker.position, tracker.realized_pnl,
                         tracker.unrealized_pnl(mid))

        if full_snapshot != last_snapshots.get(symbol):
            last_snapshots[symbol] = full_snapshot
            print(
                f"{header.seq_num}, {symbol}, {bids}, {asks}, "
                f"{tracker.position}, {tracker.realized_pnl}, "
                f"{tracker.unrealized_pnl(mid)}"
            )


if __name__ == "__main__":
    main()