import sys
import message
from orderbook import OrderBook


def main():
    # Parse the depth (N) from command-line args. default to 5 if not provided
    depth = int(sys.argv[1]) if len(sys.argv) > 1 else 5

    # One OrderBook per symbol (e.g. 'VC0', 'VC2', 'VC5', etc.)
    books: dict[str, OrderBook] = {}

    # Stores the last printed snapshot per symbol for change detection
    last_snapshots: dict[str, tuple] = {}

    # Process every message from the binary input stream
    for header, msg in message.gen_from(sys.stdin.buffer):
        symbol = msg.symbol
        # Create a new order book for every new symbok
        book = books.get(symbol)
        if book is None:
            book = OrderBook()
            books[symbol] = book

        if header.msg_type == "A":  # Add order
            book.add(msg.order_id, msg.side, msg.price, msg.volume)
        elif header.msg_type == "U":  # Update order
            book.update(msg.order_id, msg.side, msg.price, msg.volume)
        elif header.msg_type == "D":  # Delete order
            book.delete(msg.order_id, msg.side)
        elif header.msg_type == "E":  # Trade order
            book.trade(msg.order_id, msg.side, msg.volume)

        # Compute the new top-N depth snapshot for the affected symbol
        snapshot = book.depth(depth)

        # Only output if the snapshot differs from the last one we printed.
        if snapshot != last_snapshots.get(symbol):
            last_snapshots[symbol] = snapshot
            bids, asks = snapshot
            print(f"{header.seq_num}, {symbol}, {bids}, {asks}")


if __name__ == "__main__":
    main()