"""
Event Ticket Booking Dashboard
--------------------------------
Relational database app using SQLite + Tkinter (standard library only).

Tables  : customers -> bookings -> tickets  (one-to-many, one-to-many)
Rules   : ON DELETE CASCADE on both child relationships
          A seat can only be booked once per event (enforced by DB trigger
          AND by a friendly pre-check in the app)
Run     : python ticket_booking_app.py
"""

import os
import re
import math
import sqlite3
import tkinter as tk
from datetime import date
from tkinter import ttk, messagebox

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ticket_booking.db")


# ======================================================================
# DATABASE LAYER
# ======================================================================
class Database:
    def __init__(self, path=DB_FILE):
        self.conn = sqlite3.connect(path)
        # Foreign keys are OFF by default in SQLite and must be enabled
        # on every connection, otherwise CASCADE will not work.
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.create_schema()
        self.seed_if_empty()

    # ---------------------------- schema ----------------------------
    def create_schema(self):
        with self.conn:
            self.conn.executescript("""
                CREATE TABLE IF NOT EXISTS customers (
                    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    email       TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS bookings (
                    booking_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id  INTEGER NOT NULL,
                    event_name   TEXT NOT NULL,
                    booking_date TEXT NOT NULL,
                    FOREIGN KEY (customer_id)
                        REFERENCES customers(customer_id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS tickets (
                    ticket_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                    booking_id  INTEGER NOT NULL,
                    seat_number TEXT NOT NULL,
                    price       REAL NOT NULL CHECK (price >= 0),
                    FOREIGN KEY (booking_id)
                        REFERENCES bookings(booking_id)
                        ON DELETE CASCADE
                );

                -- A seat may be sold only once per event. Event name lives in
                -- 'bookings' and seat in 'tickets', so a plain UNIQUE
                -- constraint cannot express this; a trigger can.
                CREATE TRIGGER IF NOT EXISTS trg_unique_seat_per_event
                BEFORE INSERT ON tickets
                BEGIN
                    SELECT RAISE(ABORT, 'Seat already booked for this event')
                    WHERE EXISTS (
                        SELECT 1
                        FROM tickets t
                        JOIN bookings b ON b.booking_id = t.booking_id
                        WHERE t.seat_number = NEW.seat_number COLLATE NOCASE
                          AND b.event_name = (
                                SELECT event_name FROM bookings
                                WHERE booking_id = NEW.booking_id
                              ) COLLATE NOCASE
                    );
                END;
            """)

    def seed_if_empty(self):
        cur = self.conn.cursor()
        total = 0
        for table in ("customers", "bookings", "tickets"):
            total += cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        if total:
            return

        with self.conn:
            customers = [
                ("Aarav Sharma", "aarav.sharma@example.com"),
                ("Priya Nair", "priya.nair@example.com"),
                ("Rohan Mehta", "rohan.mehta@example.com"),
            ]
            cur.executemany("INSERT INTO customers (name, email) VALUES (?, ?)", customers)

            bookings = [
                (1, "Coldplay Live", "2026-10-02"),
                (1, "Stand-up Night", "2026-10-15"),
                (2, "Coldplay Live", "2026-10-05"),
                (3, "Jazz Evening", "2026-11-01"),
            ]
            cur.executemany(
                "INSERT INTO bookings (customer_id, event_name, booking_date) VALUES (?, ?, ?)",
                bookings,
            )

            tickets = [
                (1, "A12", 3500.00),
                (2, "C07", 899.50),
                (3, "A13", 3500.00),
                (4, "B03", 1200.00),
            ]
            cur.executemany(
                "INSERT INTO tickets (booking_id, seat_number, price) VALUES (?, ?, ?)",
                tickets,
            )

    # ---------------------------- helpers ---------------------------
    @staticmethod
    def make_placeholder_email(name):
        slug = re.sub(r"[^a-z0-9]+", ".", name.lower()).strip(".") or "customer"
        return f"{slug}@example.com"

    def seat_taken(self, event, seat):
        row = self.conn.execute(
            """SELECT 1 FROM tickets t
               JOIN bookings b ON b.booking_id = t.booking_id
               WHERE b.event_name = ? COLLATE NOCASE
                 AND t.seat_number = ? COLLATE NOCASE
               LIMIT 1""",
            (event, seat),
        ).fetchone()
        return row is not None

    # ---------------------------- insert ----------------------------
    def add_record(self, customer_name, event, seat, price):
        """Reuse the customer if the name exists, otherwise create them.
        Then create ONE booking and ONE ticket. All-or-nothing transaction."""
        with self.conn:  # commits on success, rolls back on exception
            row = self.conn.execute(
                "SELECT customer_id FROM customers WHERE name = ? COLLATE NOCASE",
                (customer_name,),
            ).fetchone()

            if row:
                customer_id = row[0]
                is_new_customer = False
            else:
                cur = self.conn.execute(
                    "INSERT INTO customers (name, email) VALUES (?, ?)",
                    (customer_name, self.make_placeholder_email(customer_name)),
                )
                customer_id = cur.lastrowid
                is_new_customer = True

            cur = self.conn.execute(
                "INSERT INTO bookings (customer_id, event_name, booking_date) VALUES (?, ?, ?)",
                (customer_id, event, date.today().isoformat()),
            )
            booking_id = cur.lastrowid

            self.conn.execute(
                "INSERT INTO tickets (booking_id, seat_number, price) VALUES (?, ?, ?)",
                (booking_id, seat, price),
            )
        return customer_id, booking_id, is_new_customer

    # ---------------------------- delete ----------------------------
    def delete_customer(self, customer_id):
        with self.conn:
            self.conn.execute("DELETE FROM customers WHERE customer_id = ?", (customer_id,))

    def delete_booking(self, booking_id):
        with self.conn:
            self.conn.execute("DELETE FROM bookings WHERE booking_id = ?", (booking_id,))

    def delete_ticket(self, ticket_id):
        with self.conn:
            self.conn.execute("DELETE FROM tickets WHERE ticket_id = ?", (ticket_id,))

    # ---------------------------- queries ---------------------------
    def fetch(self, sql):
        cur = self.conn.execute(sql)
        cols = [d[0] for d in cur.description]
        return cols, cur.fetchall()

    def joined_view(self):
        return self.fetch("""
            SELECT b.booking_id   AS "Booking ID",
                   c.name         AS "Customer Name",
                   b.event_name   AS "Event Name",
                   b.booking_date AS "Booking Date",
                   t.seat_number  AS "Seat Number",
                   t.price        AS "Price"
            FROM tickets t
            JOIN bookings  b ON b.booking_id  = t.booking_id
            JOIN customers c ON c.customer_id = b.customer_id
            ORDER BY b.booking_id, t.ticket_id
        """)

    def raw_table(self, table):
        # table name comes from a fixed internal list, never from user input
        assert table in ("customers", "bookings", "tickets")
        return self.fetch(f"SELECT * FROM {table} ORDER BY 1")

    def customer_options(self):
        rows = self.conn.execute(
            "SELECT customer_id, name, email FROM customers ORDER BY name"
        ).fetchall()
        return [(f"Customer {i} - {n} ({e})", i) for i, n, e in rows]

    def booking_options(self):
        rows = self.conn.execute(
            """SELECT b.booking_id, c.name, b.event_name, b.booking_date
               FROM bookings b JOIN customers c ON c.customer_id = b.customer_id
               ORDER BY b.booking_id"""
        ).fetchall()
        return [(f"Booking {i} - {n} | {ev} | {d}", i) for i, n, ev, d in rows]

    def ticket_options(self):
        rows = self.conn.execute(
            """SELECT t.ticket_id, t.seat_number, b.event_name, t.booking_id, t.price
               FROM tickets t JOIN bookings b ON b.booking_id = t.booking_id
               ORDER BY t.ticket_id"""
        ).fetchall()
        return [
            (f"Ticket {i} - Seat {s} | {ev} (Booking {bid}) | {p:.2f}", i)
            for i, s, ev, bid, p in rows
        ]

    def close(self):
        self.conn.close()


# ======================================================================
# GUI LAYER
# ======================================================================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Event Ticket Booking Dashboard")
        self.geometry("1050x700")
        self.minsize(900, 600)

        self.db = Database()

        # Tk variables for the insert panel
        self.var_customer = tk.StringVar()
        self.var_event = tk.StringVar()
        self.var_seat = tk.StringVar()
        self.var_price = tk.StringVar()

        # Tk variables for the delete panel + label -> id lookups
        self.var_del_customer = tk.StringVar()
        self.var_del_booking = tk.StringVar()
        self.var_del_ticket = tk.StringVar()
        self.customer_map, self.booking_map, self.ticket_map = {}, {}, {}

        self.trees = {}

        self._build_ui()
        self.refresh_all()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------ layout ------------------------------
    def _build_ui(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")
        top.columnconfigure(0, weight=1)
        top.columnconfigure(1, weight=2)

        self._build_insert_panel(top).grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self._build_delete_panel(top).grid(row=0, column=1, sticky="nsew")

        self._build_tabs()

    def _build_insert_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Insert Panel (new booking + ticket)", padding=10)
        frame.columnconfigure(1, weight=1)

        fields = [
            ("Customer Name:", self.var_customer),
            ("Event Name:", self.var_event),
            ("Seat Number:", self.var_seat),
            ("Ticket Price:", self.var_price),
        ]
        for r, (label, var) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=r, column=0, sticky="w", pady=3)
            entry = ttk.Entry(frame, textvariable=var, width=28)
            entry.grid(row=r, column=1, sticky="ew", pady=3, padx=(8, 0))
            if r == 0:
                self.first_entry = entry

        ttk.Button(frame, text="Add Record", command=self.on_add).grid(
            row=len(fields), column=0, columnspan=2, pady=(10, 0), sticky="ew"
        )
        return frame

    def _build_delete_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Delete Panel", padding=10)
        frame.columnconfigure(1, weight=1)

        rows = [
            ("Customer:", self.var_del_customer, "customer"),
            ("Booking:", self.var_del_booking, "booking"),
            ("Ticket:", self.var_del_ticket, "ticket"),
        ]
        self.combos = {}
        for r, (label, var, kind) in enumerate(rows):
            ttk.Label(frame, text=label).grid(row=r, column=0, sticky="w", pady=4)
            combo = ttk.Combobox(frame, textvariable=var, state="readonly", width=55)
            combo.grid(row=r, column=1, sticky="ew", padx=8, pady=4)
            ttk.Button(
                frame, text="Delete Selected",
                command=lambda k=kind: self.on_delete(k),
            ).grid(row=r, column=2, pady=4)
            self.combos[kind] = combo

        ttk.Label(
            frame,
            text="Deleting a customer removes their bookings and tickets.\n"
                 "Deleting a booking removes its tickets. Deleting a ticket removes only that seat.",
            foreground="#555555", justify="left",
        ).grid(row=len(rows), column=0, columnspan=3, sticky="w", pady=(6, 0))
        return frame

    def _build_tabs(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        for key, title in [
            ("joined", "Combined View (JOIN)"),
            ("customers", "Customers"),
            ("bookings", "Bookings"),
            ("tickets", "Tickets"),
        ]:
            tab = ttk.Frame(self.notebook)
            self.notebook.add(tab, text=title)

            tree = ttk.Treeview(tab, show="headings")
            vsb = ttk.Scrollbar(tab, orient="vertical", command=tree.yview)
            hsb = ttk.Scrollbar(tab, orient="horizontal", command=tree.xview)
            tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

            tree.grid(row=0, column=0, sticky="nsew")
            vsb.grid(row=0, column=1, sticky="ns")
            hsb.grid(row=1, column=0, sticky="ew")
            tab.rowconfigure(0, weight=1)
            tab.columnconfigure(0, weight=1)

            self.trees[key] = tree

    # ------------------------------ refresh ------------------------------
    def refresh_all(self):
        self.refresh_tables()
        self.refresh_dropdowns()

    def _fill_tree(self, tree, columns, rows):
        tree.delete(*tree.get_children())
        tree["columns"] = columns
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, anchor="center", width=140, minwidth=80, stretch=True)
        for row in rows:
            formatted = [
                f"{v:.2f}" if (isinstance(v, float) or col.lower() == "price") and v is not None else v
                for col, v in zip(columns, row)
            ]
            tree.insert("", "end", values=formatted)

    def refresh_tables(self):
        cols, rows = self.db.joined_view()
        self._fill_tree(self.trees["joined"], cols, rows)
        for table in ("customers", "bookings", "tickets"):
            cols, rows = self.db.raw_table(table)
            self._fill_tree(self.trees[table], cols, rows)

    def refresh_dropdowns(self):
        """Rebuild all three dropdowns from the DB and CLEAR the selections,
        so a combobox can never point at an ID that no longer exists
        (a customer delete also removes bookings/tickets, so all three
        are refreshed every time)."""
        sources = {
            "customer": (self.db.customer_options(), self.var_del_customer, "customer_map"),
            "booking": (self.db.booking_options(), self.var_del_booking, "booking_map"),
            "ticket": (self.db.ticket_options(), self.var_del_ticket, "ticket_map"),
        }
        for kind, (options, var, map_name) in sources.items():
            setattr(self, map_name, {label: _id for label, _id in options})
            self.combos[kind]["values"] = [label for label, _ in options]
            var.set("")

    # ------------------------------ add ------------------------------
    def _clear_inputs(self):
        for var in (self.var_customer, self.var_event, self.var_seat, self.var_price):
            var.set("")
        self.first_entry.focus_set()

    def on_add(self):
        customer = self.var_customer.get().strip()
        event = self.var_event.get().strip()
        seat = self.var_seat.get().strip().upper()
        price_text = self.var_price.get().strip()

        # ---- validation: blanks ----
        if not customer or not event or not seat or not price_text:
            messagebox.showwarning("Missing data", "All fields are required. Please fill in every box.")
            return

        # ---- validation: price must be a non-negative, finite number ----
        try:
            price = float(price_text)
        except ValueError:
            messagebox.showerror("Invalid price", "Ticket price must be a number (e.g. 499.50).")
            return
        if math.isnan(price) or math.isinf(price):
            messagebox.showerror("Invalid price", "Ticket price must be a normal number.")
            return
        if price < 0:
            messagebox.showerror("Invalid price", "Ticket price cannot be negative.")
            return
        price = round(price, 2)

        # ---- validation: seat not already booked for this event ----
        if self.db.seat_taken(event, seat):
            messagebox.showerror(
                "Seat unavailable",
                f"Seat {seat} is already booked for '{event}'.\nPlease choose a different seat.",
            )
            return

        try:
            cust_id, booking_id, is_new = self.db.add_record(customer, event, seat, price)
        except sqlite3.IntegrityError as exc:
            messagebox.showerror("Database error", f"Could not save the record:\n{exc}")
            return

        self._clear_inputs()
        self.refresh_all()
        who = "new customer created" if is_new else "existing customer reused"
        messagebox.showinfo(
            "Record added",
            f"Booking {booking_id} created for customer {cust_id} ({who}).",
        )

    # ------------------------------ delete ------------------------------
    def on_delete(self, kind):
        config = {
            "customer": (self.var_del_customer, self.customer_map, self.db.delete_customer,
                         "this customer AND all of their bookings and tickets"),
            "booking": (self.var_del_booking, self.booking_map, self.db.delete_booking,
                        "this booking AND all of its tickets"),
            "ticket": (self.var_del_ticket, self.ticket_map, self.db.delete_ticket,
                       "only this ticket (the booking and customer stay)"),
        }
        var, id_map, delete_fn, warning = config[kind]

        label = var.get()
        if not label or label not in id_map:
            messagebox.showwarning("Nothing selected", f"Please choose a {kind} to delete first.")
            return

        if not messagebox.askyesno("Confirm delete", f"This will permanently delete {warning}.\n\n{label}\n\nContinue?"):
            return

        try:
            delete_fn(id_map[label])
        except sqlite3.Error as exc:
            messagebox.showerror("Database error", f"Could not delete:\n{exc}")
            return

        self.refresh_all()  # tables update + all dropdown selections cleared

    # ------------------------------ exit ------------------------------
    def _on_close(self):
        self.db.close()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()