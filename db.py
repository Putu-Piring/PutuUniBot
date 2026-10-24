"""Putu Piring Uni - SQLite Order Management Database.

Stores and manages customer pre-orders for operations and ENT300 reporting.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sqlite3
import sys

DB_PATH = Path(__file__).parent / "orders.db"


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
  conn = sqlite3.connect(str(db_path))
  conn.row_factory = sqlite3.Row
  return conn


def init_db(db_path: Path = DB_PATH) -> None:
  """Initialize SQLite schema for orders."""
  with get_connection(db_path) as conn:
    conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_number TEXT UNIQUE NOT NULL,
                order_date TEXT NOT NULL,
                telegram_user TEXT,
                customer_name TEXT NOT NULL,
                customer_phone TEXT NOT NULL,
                package_id TEXT NOT NULL DEFAULT 'pakej-1',
                package_name TEXT NOT NULL DEFAULT 'Pakej 1: Putu Piring Asli (2 biji)',
                quantity INTEGER NOT NULL DEFAULT 1,
                unit_price REAL NOT NULL DEFAULT 2.00,
                food_subtotal REAL NOT NULL,
                fulfillment_type TEXT NOT NULL CHECK(fulfillment_type IN ('delivery', 'pickup')),
                delivery_zone TEXT,
                delivery_address TEXT,
                delivery_fee REAL NOT NULL DEFAULT 0.00,
                total_amount REAL NOT NULL,
                payment_method TEXT NOT NULL DEFAULT 'Cash',
                payment_status TEXT NOT NULL DEFAULT 'pending' CHECK(payment_status IN ('pending', 'paid', 'cod')),
                order_status TEXT NOT NULL DEFAULT 'confirmed' CHECK(order_status IN ('confirmed', 'cancelled', 'completed')),
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(order_status)"
    )
    conn.commit()
  print(f"[OK] Database initialized successfully at: {db_path}")


def generate_order_number(conn: sqlite3.Connection, order_date: str) -> str:
  date_compact = order_date.replace("-", "")
  cursor = conn.cursor()
  cursor.execute(
      "SELECT COUNT(*) FROM orders WHERE order_date = ?", (order_date,)
  )
  count = cursor.fetchone()[0] + 1
  return f"PPU-{date_compact}-{count:03d}"


def add_order(
    customer_name: str,
    customer_phone: str,
    quantity: int = 1,
    fulfillment_type: str = "delivery",
    delivery_zone: str = "",
    delivery_address: str = "",
    telegram_user: str = "",
    payment_method: str = "Cash",
    payment_status: str = "pending",
    notes: str = "",
    order_date: str | None = None,
    db_path: Path = DB_PATH,
) -> dict:
  if not order_date:
    order_date = datetime.now().strftime("%Y-%m-%d")

  now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  unit_price = 2.00
  subtotal = quantity * unit_price
  fee = 0.50 if fulfillment_type.lower() == "delivery" else 0.00
  total = subtotal + fee

  with get_connection(db_path) as conn:
    order_number = generate_order_number(conn, order_date)
    conn.execute(
        """
            INSERT INTO orders (
                order_number, order_date, telegram_user, customer_name, customer_phone,
                package_id, package_name, quantity, unit_price, food_subtotal,
                fulfillment_type, delivery_zone, delivery_address, delivery_fee,
                total_amount, payment_method, payment_status, order_status, notes,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            order_number,
            order_date,
            telegram_user,
            customer_name,
            customer_phone,
            "pakej-1",
            "Pakej 1: Putu Piring Asli (2 biji)",
            quantity,
            unit_price,
            subtotal,
            fulfillment_type.lower(),
            delivery_zone,
            delivery_address,
            fee,
            total,
            payment_method,
            payment_status,
            "confirmed",
            notes,
            now_iso,
            now_iso,
        ),
    )
    conn.commit()

  return {
      "order_number": order_number,
      "order_date": order_date,
      "customer_name": customer_name,
      "customer_phone": customer_phone,
      "quantity": quantity,
      "subtotal": subtotal,
      "delivery_fee": fee,
      "total_amount": total,
      "fulfillment_type": fulfillment_type,
      "delivery_address": delivery_address,
      "payment_method": payment_method,
      "payment_status": payment_status,
  }


def count_today_sets(
    order_date: str | None = None, db_path: Path = DB_PATH
) -> int:
  if not order_date:
    order_date = datetime.now().strftime("%Y-%m-%d")
  with get_connection(db_path) as conn:
    cursor = conn.cursor()
    cursor.execute(
        """
            SELECT COALESCE(SUM(quantity), 0)
            FROM orders
            WHERE order_date = ? AND order_status != 'cancelled'
        """,
        (order_date,),
    )
    return int(cursor.fetchone()[0])


def list_orders(
    order_date: str | None = None, db_path: Path = DB_PATH
) -> list[dict]:
  with get_connection(db_path) as conn:
    cursor = conn.cursor()
    if order_date:
      cursor.execute(
          "SELECT * FROM orders WHERE order_date = ? ORDER BY id ASC",
          (order_date,),
      )
    else:
      cursor.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 50")
    return [dict(row) for row in cursor.fetchall()]


def get_summary(
    order_date: str | None = None, db_path: Path = DB_PATH
) -> dict:
  if not order_date:
    order_date = datetime.now().strftime("%Y-%m-%d")
  with get_connection(db_path) as conn:
    cursor = conn.cursor()
    cursor.execute(
        """
            SELECT 
                COUNT(*) as total_orders,
                COALESCE(SUM(quantity), 0) as total_sets,
                COALESCE(SUM(food_subtotal), 0) as total_food_sales,
                COALESCE(SUM(delivery_fee), 0) as total_runner_fees,
                COALESCE(SUM(total_amount), 0) as grand_total
            FROM orders
            WHERE order_date = ? AND order_status != 'cancelled'
        """,
        (order_date,),
    )
    summary = dict(cursor.fetchone())

    # Breakdown by fulfillment
    cursor.execute(
        """
            SELECT fulfillment_type, COUNT(*) as orders, SUM(quantity) as sets, SUM(total_amount) as total
            FROM orders
            WHERE order_date = ? AND order_status != 'cancelled'
            GROUP BY fulfillment_type
        """,
        (order_date,),
    )
    summary["fulfillment_breakdown"] = [dict(r) for r in cursor.fetchall()]
    return summary


def cancel_order(order_ref: str, db_path: Path = DB_PATH) -> bool:
  now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  with get_connection(db_path) as conn:
    cursor = conn.cursor()
    cursor.execute(
        """
            UPDATE orders
            SET order_status = 'cancelled', updated_at = ?
            WHERE (order_number = ? OR id = ?) AND order_status != 'cancelled'
        """,
        (now_iso, order_ref, order_ref if order_ref.isdigit() else -1),
    )
    conn.commit()
    return cursor.rowcount > 0


def main():
  parser = argparse.ArgumentParser(description="Putu Piring Uni SQLite CLI")
  subparsers = parser.add_subparsers(dest="cmd")

  subparsers.add_parser("init", help="Initialize the SQLite database schema")

  add_p = subparsers.add_parser("add", help="Add a new customer order")
  add_p.add_argument("--customer", required=True, help="Customer name")
  add_p.add_argument("--phone", required=True, help="Phone number")
  add_p.add_argument(
      "--qty", type=int, default=1, help="Quantity of sets (default 1)"
  )
  add_p.add_argument(
      "--type",
      choices=["delivery", "pickup"],
      default="delivery",
      help="Fulfillment type",
  )
  add_p.add_argument("--zone", default="", help="Delivery zone (UiTM/RPTU/Fasa 5)")
  add_p.add_argument(
      "--address", default="", help="Delivery address or meeting point"
  )
  add_p.add_argument("--telegram", default="", help="Telegram username/handle")
  add_p.add_argument("--payment", default="Cash", help="Payment method")
  add_p.add_argument(
      "--pay-status",
      choices=["pending", "paid", "cod"],
      default="pending",
      help="Payment status",
  )
  add_p.add_argument("--notes", default="", help="Additional notes")
  add_p.add_argument("--date", default=None, help="Order date (YYYY-MM-DD)")

  cnt_p = subparsers.add_parser("count", help="Count sets ordered for a date")
  cnt_p.add_argument("--date", default=None, help="Date (YYYY-MM-DD)")

  list_p = subparsers.add_parser("list", help="List orders")
  list_p.add_argument("--date", default=None, help="Filter date (YYYY-MM-DD)")

  sum_p = subparsers.add_parser("summary", help="Sales and runner summary")
  sum_p.add_argument("--date", default=None, help="Date (YYYY-MM-DD)")

  can_p = subparsers.add_parser("cancel", help="Cancel an order")
  can_p.add_argument(
      "--ref", required=True, help="Order number or ID to cancel"
  )

  args = parser.parse_args()

  if args.cmd == "init":
    init_db()
  elif args.cmd == "add":
    init_db()
    res = add_order(
        customer_name=args.customer,
        customer_phone=args.phone,
        quantity=args.qty,
        fulfillment_type=args.type,
        delivery_zone=args.zone,
        delivery_address=args.address,
        telegram_user=args.telegram,
        payment_method=args.payment,
        payment_status=args.pay_status,
        notes=args.notes,
        order_date=args.date,
    )
    print(json.dumps(res, indent=2))
  elif args.cmd == "count":
    count = count_today_sets(args.date)
    print(f"Total sets ordered: {count}")
  elif args.cmd == "list":
    orders = list_orders(args.date)
    print(json.dumps(orders, indent=2))
  elif args.cmd == "summary":
    summary = get_summary(args.date)
    print(json.dumps(summary, indent=2))
  elif args.cmd == "cancel":
    ok = cancel_order(args.ref)
    print(f"Order cancellation {'successful' if ok else 'failed (not found)'}")
  else:
    parser.print_help()


if __name__ == "__main__":
  main()
