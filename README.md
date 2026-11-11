Event Ticket Booking Dashboard

A desktop dashboard for managing event ticket bookings, built with Python, SQLite, and Tkinter. It replaces spreadsheet-based booking with a relational database that enforces data integrity through foreign keys and cascading deletes.

Features
Relational database with three linked tables: customers, bookings, and tickets
Cascading deletes: deleting a customer removes their bookings and tickets; deleting a booking removes its tickets
Insert panel that reuses existing customers by name or creates new ones automatically
Delete panel with three dropdowns (Customer, Booking, Ticket), each with its own delete button
Tabbed dashboard with four live views: a combined JOIN view, plus raw views of each table
Input validation: blank fields, non-numeric prices, and negative prices are rejected
Seat uniqueness: a seat can only be sold once per event, enforced in both the app and by a database trigger
Seed data: the database is populated with sample records on first run if it is empty
Standard library only: no third-party packages required
Tech Stack
Python 3.8+
SQLite (via the built-in sqlite3 module)
Tkinter / ttk (built-in GUI toolkit)
Project Structure
event-ticket-booking/
├── ticket_booking_app.py   # Database layer + Tkinter GUI (single file)
├── ticket_booking.db       # Created automatically on first run
└── README.md
Database Schema
customers (1) ──────< bookings (1) ──────< tickets
 customer_id PK        booking_id PK        ticket_id PK
                       customer_id FK       booking_id FK
                       (ON DELETE CASCADE)  (ON DELETE CASCADE)
Table	Key Columns
customers	customer_id, name (unique), email
bookings	booking_id, customer_id (FK), event_name, booking_date
tickets	ticket_id, booking_id (FK), seat_number, price

Foreign keys are enabled with PRAGMA foreign_keys = ON on every connection, which SQLite requires for cascades to work.

Getting Started
Prerequisites
Python 3.8 or newer, with Tkinter included (it ships with most Python installers on Windows and macOS; on Linux you may need sudo apt install python3-tk)
Run
bash
git clone https://github.com/<your-username>/event-ticket-booking.git
cd event-ticket-booking
python ticket_booking_app.py

The database file ticket_booking.db is created in the same folder as the script. On the first run it is seeded with sample customers, bookings, and tickets.

Running in VS Code
Open the project folder in VS Code.
Select your Python interpreter (Ctrl+Shift+P → Python: Select Interpreter).
Open ticket_booking_app.py and press F5 or click Run Python File.
How to Use

Add a booking (Insert Panel)

Enter a customer name, event name, seat number (e.g. A12), and ticket price.
Click Add Record. If the customer already exists, their existing profile is reused; otherwise a new one is created with a placeholder email such as priya.nair@example.com.
Each submission creates one booking and one ticket.

Delete records (Delete Panel)

Customer: removes the customer and all their bookings and tickets.
Booking: removes the booking and all its tickets.
Ticket: removes only that seat; the booking and customer remain.

All deletes ask for confirmation first.

View data (Tabs)

Combined View (JOIN): booking ID, customer name, event, date, seat, and price in one table.
Customers, Bookings, Tickets: raw views of each table.
Validation Rules
Input	Rule
All text boxes	Cannot be blank
Ticket price	Must be a finite, non-negative number
Seat number	Must be unique for the same event (case-insensitive)
Running Tests

No automated tests are included yet. Manual test cases to try:

Delete a customer and confirm their bookings and tickets disappear.
Delete a single ticket and confirm the booking and customer remain.
Book the same seat twice for the same event and confirm the error appears.
Enter -50 or abc as a price and confirm validation blocks the save.
Future Improvements
Let users enter a real email address in the Insert Panel
Allow editing of existing records
Export tables to CSV
Add automated unit tests for the database layer
License

This project is for academic purposes. Add a license of your choice before publishing publicly.

Author - Hemanth

Your Name – Hemanth.S
