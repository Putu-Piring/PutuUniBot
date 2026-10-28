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
                telegram_user_id INTEGER,
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
                order_status TEXT NOT NULL DEFAULT 'confirmed' CHECK(order_status IN ('confirmed', 'delivering', 'completed', 'cancelled')),
                rating INTEGER,
                rating_notes TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(orders)")
    cols = [row[1] for row in cursor.fetchall()]
    if "telegram_user_id" not in cols:
      conn.execute("ALTER TABLE orders ADD COLUMN telegram_user_id INTEGER")
    if "rating" not in cols:
      conn.execute("ALTER TABLE orders ADD COLUMN rating INTEGER")
    if "rating_notes" not in cols:
      conn.execute("ALTER TABLE orders ADD COLUMN rating_notes TEXT")

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(order_status)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(telegram_user_id)"
    )
    conn.commit()
  print(f"[OK] Database initialized successfully at: {db_path}")


def generate_order_number(conn: sqlite3.Connection, order_date: str) -> str:
  date_compact = order_date.replace("-", "")
  cursor = conn.cursor()
  cursor.execute(
      """
      SELECT MAX(CAST(SUBSTR(order_number, -3) AS INTEGER))
      FROM orders
      WHERE order_date = ?
      """,
      (order_date,),
  )
  row = cursor.fetchone()
  max_seq = row[0] if (row and row[0] is not None) else 0
  return f"PPU-{date_compact}-{max_seq + 1:03d}"


def add_order(
    customer_name: str,
    customer_phone: str,
    quantity: int = 1,
    fulfillment_type: str = "delivery",
    delivery_zone: str = "",
    delivery_address: str = "",
    telegram_user: str = "",
    telegram_user_id: int | None = None,
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
                order_number, order_date, telegram_user, telegram_user_id, customer_name, customer_phone,
                package_id, package_name, quantity, unit_price, food_subtotal,
                fulfillment_type, delivery_zone, delivery_address, delivery_fee,
                total_amount, payment_method, payment_status, order_status, notes,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            order_number,
            order_date,
            telegram_user,
            telegram_user_id,
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
      "unit_price": unit_price,
      "food_subtotal": subtotal,
      "delivery_fee": fee,
      "total_amount": total,
      "fulfillment_type": fulfillment_type,
      "delivery_address": delivery_address,
      "telegram_user": telegram_user,
      "telegram_user_id": telegram_user_id,
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
    order_date: str | None = None,
    user: str | None = None,
    db_path: Path = DB_PATH,
) -> list[dict]:
  with get_connection(db_path) as conn:
    cursor = conn.cursor()
    if user:
      clean_user = user.strip()
      clean_no_at = clean_user.lstrip("@")
      user_id = int(clean_user) if clean_user.isdigit() else None
      if order_date:
        if user_id is not None:
          cursor.execute(
              """
              SELECT * FROM orders 
              WHERE order_date = ? AND (telegram_user_id = ? OR LOWER(telegram_user) = ? OR LOWER(telegram_user) = ?)
              ORDER BY id DESC LIMIT 50
              """,
              (order_date, user_id, clean_user.lower(), f"@{clean_no_at}".lower()),
          )
        else:
          cursor.execute(
              """
              SELECT * FROM orders 
              WHERE order_date = ? AND (LOWER(telegram_user) = ? OR LOWER(telegram_user) = ?)
              ORDER BY id DESC LIMIT 50
              """,
              (order_date, clean_user.lower(), f"@{clean_no_at}".lower()),
          )
      else:
        if user_id is not None:
          cursor.execute(
              """
              SELECT * FROM orders 
              WHERE telegram_user_id = ? OR LOWER(telegram_user) = ? OR LOWER(telegram_user) = ?
              ORDER BY id DESC LIMIT 50
              """,
              (user_id, clean_user.lower(), f"@{clean_no_at}".lower()),
          )
        else:
          cursor.execute(
              """
              SELECT * FROM orders 
              WHERE LOWER(telegram_user) = ? OR LOWER(telegram_user) = ?
              ORDER BY id DESC LIMIT 50
              """,
              (clean_user.lower(), f"@{clean_no_at}".lower()),
          )
    elif order_date:
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

    # Breakdown by order status
    cursor.execute(
        """
            SELECT order_status, COUNT(*) as count
            FROM orders
            WHERE order_date = ?
            GROUP BY order_status
        """,
        (order_date,),
    )
    summary["status_breakdown"] = {r["order_status"]: r["count"] for r in cursor.fetchall()}
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


def dispatch_order(order_ref: str, notes: str | None = None, db_path: Path = DB_PATH) -> dict | None:
  """Mark an order as delivering (runner out for delivery or ready for pickup). Returns updated order dict."""
  now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  with get_connection(db_path) as conn:
    cursor = conn.cursor()
    if notes:
      cursor.execute(
          """
          UPDATE orders
          SET order_status = 'delivering', notes = CASE WHEN notes IS NULL OR notes = '' THEN ? ELSE notes || ' | ' || ? END, updated_at = ?
          WHERE order_number = ? OR id = ?
          """,
          (notes, notes, now_iso, order_ref, order_ref if order_ref.isdigit() else -1),
      )
    else:
      cursor.execute(
          """
          UPDATE orders
          SET order_status = 'delivering', updated_at = ?
          WHERE order_number = ? OR id = ?
          """,
          (now_iso, order_ref, order_ref if order_ref.isdigit() else -1),
      )
    conn.commit()
    if cursor.rowcount > 0:
      return get_order(order_ref, db_path)
    return None


def complete_order(order_ref: str, notes: str | None = None, db_path: Path = DB_PATH) -> dict | None:
  """Mark an order as completed when customer confirms receipt of goods. Returns updated order dict."""
  now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  with get_connection(db_path) as conn:
    cursor = conn.cursor()
    if notes:
      cursor.execute(
          """
          UPDATE orders
          SET order_status = 'completed', notes = CASE WHEN notes IS NULL OR notes = '' THEN ? ELSE notes || ' | ' || ? END, updated_at = ?
          WHERE order_number = ? OR id = ?
          """,
          (notes, notes, now_iso, order_ref, order_ref if order_ref.isdigit() else -1),
      )
    else:
      cursor.execute(
          """
          UPDATE orders
          SET order_status = 'completed', updated_at = ?
          WHERE order_number = ? OR id = ?
          """,
          (now_iso, order_ref, order_ref if order_ref.isdigit() else -1),
      )
    conn.commit()
    if cursor.rowcount > 0:
      return get_order(order_ref, db_path)
    return None


def rate_order(
    order_ref: str,
    rating: int,
    feedback: str | None = None,
    db_path: Path = DB_PATH,
) -> dict | None:
  """Record a 1-5 star customer satisfaction rating and optional feedback notes for an order."""
  if not (1 <= rating <= 5):
    return None

  now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  with get_connection(db_path) as conn:
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE orders
        SET rating = ?, rating_notes = ?, updated_at = ?
        WHERE order_number = ? OR id = ?
        """,
        (rating, feedback, now_iso, order_ref, order_ref if order_ref.isdigit() else -1),
    )
    conn.commit()
    if cursor.rowcount > 0:
      return get_order(order_ref, db_path)
  return None


def reorder(
    order_ref: str,
    telegram_user_id: int | None = None,
    order_date: str | None = None,
    db_path: Path = DB_PATH,
) -> dict | None:
  """Create a fresh new order for today based on an existing previous order."""
  prev = get_order(order_ref, db_path)
  if not prev:
    return None

  new_tg_id = telegram_user_id if telegram_user_id is not None else prev.get("telegram_user_id")
  new_order = add_order(
      customer_name=prev["customer_name"],
      customer_phone=prev["customer_phone"],
      quantity=prev["quantity"],
      fulfillment_type=prev["fulfillment_type"],
      delivery_zone=prev.get("delivery_zone", ""),
      delivery_address=prev.get("delivery_address", ""),
      telegram_user=prev.get("telegram_user", ""),
      telegram_user_id=new_tg_id,
      payment_method="DuitNow QR",
      payment_status="pending",
      notes=f"Reorder from {prev['order_number']}",
      order_date=order_date,
      db_path=db_path,
  )
  return new_order


def update_order(
    order_ref: str,
    quantity: int | None = None,
    fulfillment_type: str | None = None,
    delivery_zone: str | None = None,
    delivery_address: str | None = None,
    notes: str | None = None,
    db_path: Path = DB_PATH,
) -> dict | None:
  """Update an existing uncompleted order's details (quantity, fulfillment, address). Recalculates pricing."""
  order = get_order(order_ref, db_path)
  if not order:
    return None

  if order["order_status"] in ("cancelled", "completed"):
    return None

  new_qty = quantity if quantity is not None else order["quantity"]
  new_ful = (fulfillment_type or order["fulfillment_type"]).lower()
  new_zone = delivery_zone if delivery_zone is not None else order["delivery_zone"]
  new_addr = delivery_address if delivery_address is not None else order["delivery_address"]
  new_notes = notes if notes is not None else order["notes"]

  unit_price = order["unit_price"]
  subtotal = new_qty * unit_price
  fee = 0.50 if new_ful == "delivery" else 0.00
  total = subtotal + fee
  now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

  with get_connection(db_path) as conn:
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE orders
        SET quantity = ?, food_subtotal = ?, fulfillment_type = ?,
            delivery_zone = ?, delivery_address = ?, delivery_fee = ?,
            total_amount = ?, notes = ?, updated_at = ?
        WHERE order_number = ? OR id = ?
        """,
        (
            new_qty,
            subtotal,
            new_ful,
            new_zone,
            new_addr,
            fee,
            total,
            new_notes,
            now_iso,
            order_ref,
            order_ref if order_ref.isdigit() else -1,
        ),
    )
    conn.commit()
    if cursor.rowcount > 0:
      return get_order(order_ref, db_path)
    return None


def check_cutoff(check_time: datetime | None = None) -> dict:
  """Check operating status and cut-off schedule against Malaysian Time (MYT / UTC+8)."""
  if not check_time:
    check_time = datetime.now()

  days_map = {
      6: "Ahad",     # Sunday
      0: "Isnin",    # Monday
      1: "Selasa",   # Tuesday
      2: "Rabu",     # Wednesday
      3: "Khamis",   # Thursday
      4: "Jumaat",   # Friday
      5: "Sabtu",    # Saturday
  }

  day_name = days_map.get(check_time.weekday(), "Lain")
  is_operating_day = day_name in ("Ahad", "Isnin", "Selasa", "Khamis")

  if not is_operating_day:
    return {
        "is_open": False,
        "day_name": day_name,
        "is_operating_day": False,
        "is_past_cutoff": True,
        "cutoff_time": "Tutup",
        "message": f"Hari ini ({day_name}) adalah hari cuti operasi. Sila buat pra-pesanan untuk hari operasi seterusnya (Ahad, Isnin, Selasa, Khamis).",
    }

  if day_name == "Ahad":
    cutoff_hour, cutoff_minute = 9, 30
    cutoff_str = "9:30 AM"
  else:
    cutoff_hour, cutoff_minute = 17, 0
    cutoff_str = "5:00 PM"

  cutoff_dt = check_time.replace(hour=cutoff_hour, minute=cutoff_minute, second=0, microsecond=0)
  is_past_cutoff = check_time > cutoff_dt

  if is_past_cutoff:
    return {
        "is_open": False,
        "day_name": day_name,
        "is_operating_day": True,
        "is_past_cutoff": True,
        "cutoff_time": cutoff_str,
        "message": f"Masa tempahan untuk hari ini ({day_name}) telah ditutup pada jam {cutoff_str}. Sila buat pra-pesanan untuk hari operasi seterusnya.",
    }

  return {
      "is_open": True,
      "day_name": day_name,
      "is_operating_day": True,
      "is_past_cutoff": False,
      "cutoff_time": cutoff_str,
      "message": f"Tempahan dibuka untuk hari ini ({day_name}) sehingga jam {cutoff_str}.",
  }


def get_latest_order_for_user(
    telegram_user: str | None = None,
    telegram_user_id: int | None = None,
    db_path: Path = DB_PATH,
) -> dict | None:
  """Retrieve the most recent active order for a telegram user by handle or numeric ID."""
  if not telegram_user and not telegram_user_id:
    return None

  clean_user = (telegram_user or "").strip()
  clean_no_at = clean_user.lstrip("@")
  user_id = telegram_user_id
  if user_id is None and clean_user.isdigit():
    user_id = int(clean_user)

  with get_connection(db_path) as conn:
    cursor = conn.cursor()
    # 1. First try to find active uncompleted orders
    if user_id is not None and clean_user and not clean_user.isdigit():
      cursor.execute(
          """
          SELECT * FROM orders
          WHERE (telegram_user_id = ? OR LOWER(telegram_user) = ? OR LOWER(telegram_user) = ?)
            AND order_status != 'cancelled'
          ORDER BY CASE WHEN order_status != 'completed' THEN 0 ELSE 1 END, id DESC
          LIMIT 1
          """,
          (user_id, clean_user.lower(), f"@{clean_no_at}".lower()),
      )
    elif user_id is not None:
      cursor.execute(
          """
          SELECT * FROM orders
          WHERE telegram_user_id = ? AND order_status != 'cancelled'
          ORDER BY CASE WHEN order_status != 'completed' THEN 0 ELSE 1 END, id DESC
          LIMIT 1
          """,
          (user_id,),
      )
    else:
      cursor.execute(
          """
          SELECT * FROM orders
          WHERE (LOWER(telegram_user) = ? OR LOWER(telegram_user) = ?) AND order_status != 'cancelled'
          ORDER BY CASE WHEN order_status != 'completed' THEN 0 ELSE 1 END, id DESC
          LIMIT 1
          """,
          (clean_user.lower(), f"@{clean_no_at}".lower()),
      )

    row = cursor.fetchone()
    if row:
      return dict(row)

    # 2. Fallback to any order including cancelled/completed
    if user_id is not None:
      cursor.execute(
          "SELECT * FROM orders WHERE telegram_user_id = ? ORDER BY id DESC LIMIT 1",
          (user_id,),
      )
    else:
      cursor.execute(
          "SELECT * FROM orders WHERE LOWER(telegram_user) = ? OR LOWER(telegram_user) = ? ORDER BY id DESC LIMIT 1",
          (clean_user.lower(), f"@{clean_no_at}".lower()),
      )
    row = cursor.fetchone()
    return dict(row) if row else None


def get_order(order_ref: str, db_path: Path = DB_PATH) -> dict | None:
  with get_connection(db_path) as conn:
    cursor = conn.cursor()
    cursor.execute(
        """
            SELECT * FROM orders
            WHERE order_number = ? OR id = ?
        """,
        (order_ref, order_ref if order_ref.isdigit() else -1),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def update_payment(
    order_ref: str,
    payment_status: str,
    payment_method: str | None = None,
    notes: str | None = None,
    db_path: Path = DB_PATH,
) -> bool:
  now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  with get_connection(db_path) as conn:
    cursor = conn.cursor()
    if payment_method and notes:
      cursor.execute(
          """
                UPDATE orders
                SET payment_status = ?, payment_method = ?, notes = ?, updated_at = ?
                WHERE order_number = ? OR id = ?
            """,
          (
              payment_status,
              payment_method,
              notes,
              now_iso,
              order_ref,
              order_ref if order_ref.isdigit() else -1,
          ),
      )
    elif payment_method:
      cursor.execute(
          """
                UPDATE orders
                SET payment_status = ?, payment_method = ?, updated_at = ?
                WHERE order_number = ? OR id = ?
            """,
          (
              payment_status,
              payment_method,
              now_iso,
              order_ref,
              order_ref if order_ref.isdigit() else -1,
          ),
      )
    else:
      cursor.execute(
          """
                UPDATE orders
                SET payment_status = ?, updated_at = ?
                WHERE order_number = ? OR id = ?
            """,
          (
              payment_status,
              now_iso,
              order_ref,
              order_ref if order_ref.isdigit() else -1,
          ),
      )
    conn.commit()
    return cursor.rowcount > 0


def main():
  parser = argparse.ArgumentParser(description="Putu Piring Uni Order Manager")
  subparsers = parser.add_subparsers(dest="cmd", required=True)

  subparsers.add_parser("init", help="Initialize the database")

  add_p = subparsers.add_parser("add", help="Add a new pre-order")
  add_p.add_argument("--customer", required=True, help="Customer name")
  add_p.add_argument("--phone", required=True, help="Customer phone number")
  add_p.add_argument("--qty", type=int, default=1, help="Quantity of sets")
  add_p.add_argument(
      "--type",
      choices=["delivery", "pickup"],
      required=True,
      help="Fulfillment type",
  )
  add_p.add_argument("--zone", default="", help="Delivery zone")
  add_p.add_argument(
      "--address", default="", help="Delivery address or pickup point"
  )
  add_p.add_argument("--telegram", default="", help="Telegram username/handle")
  add_p.add_argument("--telegram-id", type=int, default=None, help="Telegram numeric User ID")
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
  list_p.add_argument("--user", default=None, help="Filter by Telegram username or numeric ID")

  sum_p = subparsers.add_parser("summary", help="Sales and runner summary")
  sum_p.add_argument("--date", default=None, help="Date (YYYY-MM-DD)")

  can_p = subparsers.add_parser("cancel", help="Cancel an order")
  can_p.add_argument(
      "--ref", required=True, help="Order number or ID to cancel"
  )

  get_p = subparsers.add_parser("get", help="Get order details by reference")
  get_p.add_argument("--ref", default=None, help="Order number or ID")
  get_p.add_argument("--user", default=None, help="Telegram user handle or ID")

  upd_p = subparsers.add_parser("update-payment", help="Update order payment status")
  upd_p.add_argument("--ref", required=True, help="Order number or ID")
  upd_p.add_argument(
      "--status",
      choices=["pending", "paid", "cod"],
      required=True,
      help="New payment status",
  )
  upd_p.add_argument("--payment", default=None, help="Payment method override")
  upd_p.add_argument("--notes", default=None, help="Payment/verification notes")

  upd_ord_p = subparsers.add_parser("update-order", help="Update order details (quantity, address, etc.)")
  upd_ord_p.add_argument("--ref", required=True, help="Order number or ID")
  upd_ord_p.add_argument("--qty", type=int, default=None, help="New quantity")
  upd_ord_p.add_argument("--type", choices=["delivery", "pickup"], default=None, help="Fulfillment type")
  upd_ord_p.add_argument("--zone", default=None, help="Delivery zone")
  upd_ord_p.add_argument("--address", default=None, help="Delivery address or meeting point")
  upd_ord_p.add_argument("--notes", default=None, help="Additional notes")

  subparsers.add_parser("cutoff", help="Check current operating schedule and cut-off status")

  comp_p = subparsers.add_parser("complete", help="Mark order as completed/received")
  comp_p.add_argument("--ref", default=None, help="Order number or ID")
  comp_p.add_argument("--user", default=None, help="Telegram user handle or ID")
  comp_p.add_argument("--notes", default=None, help="Completion notes")

  disp_p = subparsers.add_parser("dispatch", help="Mark order as out for delivery")
  disp_p.add_argument("--ref", default=None, help="Order number or ID")
  disp_p.add_argument("--user", default=None, help="Telegram user handle or ID")
  disp_p.add_argument("--notes", default=None, help="Dispatch notes")

  rate_p = subparsers.add_parser("rate", help="Record customer 1-5 star rating for an order")
  rate_p.add_argument("--ref", required=True, help="Order number or ID")
  rate_p.add_argument("--stars", type=int, choices=[1, 2, 3, 4, 5], required=True, help="Star rating (1-5)")
  rate_p.add_argument("--feedback", default=None, help="Optional feedback text")

  reord_p = subparsers.add_parser("reorder", help="Reorder past order in 1-click")
  reord_p.add_argument("--ref", required=True, help="Previous order number or ID")
  reord_p.add_argument("--telegram-id", type=int, default=None, help="Telegram user ID")

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
        telegram_user_id=args.telegram_id,
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
    orders = list_orders(args.date, user=args.user)
    print(json.dumps(orders, indent=2))
  elif args.cmd == "summary":
    summary = get_summary(args.date)
    print(json.dumps(summary, indent=2))
  elif args.cmd == "cancel":
    ok = cancel_order(args.ref)
    print(f"Order cancellation {'successful' if ok else 'failed (not found)'}")
  elif args.cmd == "get":
    ref = args.ref
    if not ref and args.user:
      latest = get_latest_order_for_user(args.user)
      if latest:
        ref = latest.get("order_number")
    if not ref:
      print(json.dumps({"error": "No order reference or user found"}, indent=2))
    else:
      order = get_order(ref)
      if order:
        print(json.dumps(order, indent=2))
      else:
        print(json.dumps({"error": f"Order {ref} not found"}, indent=2))
  elif args.cmd == "update-payment":
    ok = update_payment(
        order_ref=args.ref,
        payment_status=args.status,
        payment_method=args.payment,
        notes=args.notes,
    )
    print(
        f"Payment update {'successful' if ok else 'failed (order not found)'}"
    )
  elif args.cmd == "update-order":
    order = update_order(
        order_ref=args.ref,
        quantity=args.qty,
        fulfillment_type=args.type,
        delivery_zone=args.zone,
        delivery_address=args.address,
        notes=args.notes,
    )
    if order:
      print(json.dumps(order, indent=2))
    else:
      print(json.dumps({"error": f"Failed to update order {args.ref} (not found or already completed/cancelled)"}, indent=2))
  elif args.cmd == "cutoff":
    status = check_cutoff()
    print(json.dumps(status, indent=2))
  elif args.cmd == "complete":
    ref = args.ref
    if not ref and args.user:
      latest = get_latest_order_for_user(args.user)
      if latest:
        ref = latest.get("order_number")
    if not ref:
      print(json.dumps({"error": "No order reference or matching user found"}, indent=2))
    else:
      order = complete_order(order_ref=ref, notes=args.notes)
      if order:
        print(json.dumps(order, indent=2))
      else:
        print(json.dumps({"error": f"Failed to complete order {ref}"}, indent=2))
  elif args.cmd == "dispatch":
    ref = args.ref
    if not ref and args.user:
      latest = get_latest_order_for_user(args.user)
      if latest:
        ref = latest.get("order_number")
    if not ref:
      print(json.dumps({"error": "No order reference or matching user found"}, indent=2))
    else:
      order = dispatch_order(order_ref=ref, notes=args.notes)
      if order:
        print(json.dumps(order, indent=2))
      else:
        print(json.dumps({"error": f"Failed to dispatch order {ref}"}, indent=2))
  elif args.cmd == "rate":
    order = rate_order(order_ref=args.ref, rating=args.stars, feedback=args.feedback)
    if order:
      print(json.dumps(order, indent=2))
    else:
      print(json.dumps({"error": f"Failed to record rating for {args.ref}"}, indent=2))
  elif args.cmd == "reorder":
    order = reorder(order_ref=args.ref, telegram_user_id=args.telegram_id)
    if order:
      print(json.dumps(order, indent=2))
    else:
      print(json.dumps({"error": f"Failed to reorder from {args.ref}"}, indent=2))
  else:
    parser.print_help()


if __name__ == "__main__":
  main()
