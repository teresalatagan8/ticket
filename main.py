import sys
import json
import uuid
import math
import tkinter as tk
from tkinter import ttk, messagebox
import firebase_admin
from firebase_admin import credentials, firestore

try:
    if not firebase_admin._apps:
        cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as err:
    print(f"[CRITICAL] Database initialization failed: {err}")
    sys.exit(1)


THEME = {
    "bg_root": "#0B0C10",
    "bg_card": "#12080A",
    "bg_panel": "#1A0F12",
    "bg_input": "#2A1418",
    "text_main": "#F1FAEE",
    "text_muted": "#A89A9D",
    "accent": "#E63946",
    "accent_hover": "#D62828",
    "vip_gold": "#FFB703",
    "success": "#2A9D8F",
    "danger": "#E63946",
    "font_main": "Segoe UI"
}


class ActionButton(tk.Button):
    def __init__(self, master, bg_color=THEME["accent"], hover_color=THEME["accent_hover"], text_color=THEME["text_main"], **kwargs):
        super().__init__(master, **kwargs)
        self.default_bg = bg_color
        self.hover_bg = hover_color
        self.configure(
            bg=self.default_bg,
            fg=text_color,
            activebackground=self.hover_bg,
            activeforeground=text_color,
            bd=0,
            relief="flat",
            cursor="hand2",
            font=(THEME["font_main"], 10, "bold")
        )
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _on_enter(self, e):
        if self['state'] != 'disabled':
            self['bg'] = self.hover_bg

    def _on_leave(self, e):
        if self['state'] != 'disabled':
            self['bg'] = self.default_bg


class TicketBookingSystem(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Event Ticketing Portal")
        self.geometry("1024x780")
        self.configure(bg=THEME["bg_root"])

        self.user = None
        self.active_event = None
        self.selected_seats = []
        self.seat_buttons = {}
        self.active_booking_id = None
        self.active_ref = None
        self.active_payment_method = "Bank Transfer"

        self._init_styles()
        self._bootstrap_db()
        self.render_role_selector()

    def _init_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        
        style.configure("Treeview",
                        background=THEME["bg_panel"],
                        foreground=THEME["text_main"],
                        fieldbackground=THEME["bg_panel"],
                        rowheight=32,
                        font=(THEME["font_main"], 10))
        
        style.configure("Treeview.Heading",
                        background=THEME["bg_input"],
                        foreground=THEME["accent"],
                        font=(THEME["font_main"], 10, "bold"))
        style.map("Treeview", background=[("selected", THEME["accent"])])

        style.configure("TCombobox",
                        fieldbackground=THEME["bg_input"],
                        background=THEME["bg_input"],
                        foreground=THEME["text_main"],
                        arrowcolor=THEME["accent"],
                        bordercolor=THEME["bg_input"],
                        font=(THEME["font_main"], 10))
        style.map("TCombobox",
                  fieldbackground=[("readonly", THEME["bg_input"])],
                  selectbackground=[("readonly", THEME["bg_input"])],
                  selectforeground=[("readonly", THEME["text_main"])])

    def clear_view(self):
        for w in self.winfo_children():
            w.destroy()

    def _bootstrap_db(self):
        try:
            users_ref = db.collection("users")
            if not list(users_ref.limit(1).stream()):
                users_ref.document("admin").set({"password": "admin", "role": "ADMIN"})
                users_ref.document("staff").set({"password": "staff", "role": "STAFF"})
                users_ref.document("customer").set({"password": "123", "role": "CUSTOMER"})

            events_ref = db.collection("events")
            if not list(events_ref.limit(1).stream()):
                sample_seats = {}
                for r in range(3):
                    row_let = chr(65 + r)
                    for c in range(1, 6):
                        code = f"{row_let}{c}"
                        stype = "VIP" if r == 0 else "Normal"
                        sample_seats[code] = {"status": "available", "type": stype}

                events_ref.document("E1").set({
                    "name": "Rock Festival 2026",
                    "normal_price": 1000.0,
                    "vip_price": 2500.0,
                    "date_time": "November 20, 2026 - 08:00 PM",
                    "ticket_limit": 15,
                    "seats": sample_seats
                })
        except Exception as e:
            print(f"[WARN] Database bootstrap skipped: {e}")

    # ------------------------------------------------------------------
    # AUTHENTICATION & ACCESS CONTROL
    # ------------------------------------------------------------------
    def render_role_selector(self):
        self.clear_view()
        frame = tk.Frame(self, bg=THEME["bg_root"])
        frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(frame, text="TICKET PORTAL", font=(THEME["font_main"], 26, "bold"),
                 fg=THEME["accent"], bg=THEME["bg_root"]).pack(pady=(0, 2))
        tk.Label(frame, text="Select authentication gate to proceed", font=(THEME["font_main"], 10),
                 fg=THEME["text_muted"], bg=THEME["bg_root"]).pack(pady=(0, 25))

        for role in ["CUSTOMER", "STAFF", "ADMIN"]:
            ActionButton(
                frame, text=f"{role} ACCESS", width=26, height=2,
                command=lambda r=role: self.render_login(r)
            ).pack(pady=5)

        tk.Frame(frame, bg=THEME["bg_input"], height=1, width=240).pack(pady=15)

        ActionButton(
            frame, text="NEW ACCOUNT", width=26, height=2,
            bg_color=THEME["bg_panel"], hover_color=THEME["bg_input"],
            command=self.render_register
        ).pack()

    def render_register(self):
        self.clear_view()
        card = tk.Frame(self, bg=THEME["bg_card"], padx=40, pady=35)
        card.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(card, text="ACCOUNT REGISTRATION", font=(THEME["font_main"], 16, "bold"),
                 fg=THEME["text_main"], bg=THEME["bg_card"]).pack(pady=(0, 15))

        tk.Label(card, text="Username", font=(THEME["font_main"], 9, "bold"), fg=THEME["text_muted"], bg=THEME["bg_card"], anchor="w").pack(fill="x")
        username_input = tk.Entry(card, font=(THEME["font_main"], 11), bg=THEME["bg_input"], fg=THEME["text_main"], insertbackground=THEME["accent"], bd=0)
        username_input.pack(fill="x", ipady=7, pady=(3, 10))

        tk.Label(card, text="Role Level", font=(THEME["font_main"], 9, "bold"), fg=THEME["text_muted"], bg=THEME["bg_card"], anchor="w").pack(fill="x")
        role_select = ttk.Combobox(card, values=["CUSTOMER", "STAFF", "ADMIN"], state="readonly")
        role_select.set("CUSTOMER")
        role_select.pack(fill="x", ipady=4, pady=(3, 10))

        tk.Label(card, text="Password", font=(THEME["font_main"], 9, "bold"), fg=THEME["text_muted"], bg=THEME["bg_card"], anchor="w").pack(fill="x")
        pass_input = tk.Entry(card, show="*", font=(THEME["font_main"], 11), bg=THEME["bg_input"], fg=THEME["text_main"], insertbackground=THEME["accent"], bd=0)
        pass_input.pack(fill="x", ipady=7, pady=(3, 10))

        tk.Label(card, text="Confirm Password", font=(THEME["font_main"], 9, "bold"), fg=THEME["text_muted"], bg=THEME["bg_card"], anchor="w").pack(fill="x")
        confirm_pass_input = tk.Entry(card, show="*", font=(THEME["font_main"], 11), bg=THEME["bg_input"], fg=THEME["text_main"], insertbackground=THEME["accent"], bd=0)
        confirm_pass_input.pack(fill="x", ipady=7, pady=(3, 18))

        def handle_signup():
            u = username_input.get().strip()
            r = role_select.get().strip()
            p = pass_input.get().strip()
            cp = confirm_pass_input.get().strip()

            if not u or not p:
                messagebox.showerror("Error", "Required fields cannot be empty.")
                return
            if p != cp:
                messagebox.showerror("Error", "Password confirmation mismatch.")
                return

            try:
                if db.collection("users").document(u).get().exists:
                    messagebox.showerror("Error", "Username is already registered.")
                    return

                db.collection("users").document(u).set({"password": p, "role": r})
                messagebox.showinfo("Success", f"Account created successfully for {u}.")
                self.user = {"username": u, "role": r}
                self.route_dashboard()
            except Exception as ex:
                messagebox.showerror("Error", f"Failed to complete registration: {ex}")

        ActionButton(card, text="REGISTER ACCOUNT", command=handle_signup, width=25, height=2).pack(pady=(0, 8))
        ActionButton(card, text="Cancel", command=self.render_role_selector, bg_color=THEME["bg_input"], hover_color="#3A1C21", width=25, height=2).pack()

    def render_login(self, target_role):
        self.clear_view()
        card = tk.Frame(self, bg=THEME["bg_card"], padx=40, pady=40)
        card.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(card, text=f"{target_role} AUTHENTICATION", font=(THEME["font_main"], 16, "bold"),
                 fg=THEME["accent"], bg=THEME["bg_card"]).pack(pady=(0, 20))

        tk.Label(card, text="Username", font=(THEME["font_main"], 9, "bold"), fg=THEME["text_muted"], bg=THEME["bg_card"], anchor="w").pack(fill="x")
        user_input = tk.Entry(card, font=(THEME["font_main"], 11), bg=THEME["bg_input"], fg=THEME["text_main"], insertbackground=THEME["accent"], bd=0)
        user_input.pack(fill="x", ipady=7, pady=(3, 15))

        tk.Label(card, text="Password", font=(THEME["font_main"], 9, "bold"), fg=THEME["text_muted"], bg=THEME["bg_card"], anchor="w").pack(fill="x")
        pass_input = tk.Entry(card, show="*", font=(THEME["font_main"], 11), bg=THEME["bg_input"], fg=THEME["text_main"], insertbackground=THEME["accent"], bd=0)
        pass_input.pack(fill="x", ipady=7, pady=(3, 20))

        def handle_login():
            u = user_input.get().strip()
            p = pass_input.get().strip()

            try:
                doc = db.collection("users").document(u).get()
                if doc.exists:
                    payload = doc.to_dict()
                    if payload.get("password") == p and payload.get("role") == target_role:
                        self.user = {"username": u, "role": target_role}
                        self.route_dashboard()
                        return
                messagebox.showerror("Access Denied", "Invalid login details or insufficient permissions.")
            except Exception as ex:
                messagebox.showerror("Error", f"Authentication error: {ex}")

        ActionButton(card, text="LOG IN", command=handle_login, width=25, height=2).pack(pady=(0, 8))
        ActionButton(card, text="Back", command=self.render_role_selector, bg_color=THEME["bg_input"], hover_color="#3A1C21", width=25, height=2).pack()

    def route_dashboard(self):
        role = self.user["role"]
        if role == "CUSTOMER":
            self.render_customer_view()
        elif role == "STAFF":
            self.render_staff_view()
        elif role == "ADMIN":
            self.render_admin_view()

    def terminate_session(self):
        self.user = None
        self.active_event = None
        self.selected_seats = []
        self.seat_buttons = {}
        self.active_booking_id = None
        self.active_ref = None
        self.active_payment_method = "Bank Transfer"
        self.render_role_selector()

    # ------------------------------------------------------------------
    # CUSTOMER INTERFACE
    # ------------------------------------------------------------------
    def render_customer_view(self):
        self.clear_view()

        header = tk.Frame(self, bg=THEME["bg_card"], padx=20, pady=15)
        header.pack(fill="x")
        tk.Label(header, text=f"Active User: {self.user['username']}", font=(THEME["font_main"], 12, "bold"),
                 fg=THEME["text_main"], bg=THEME["bg_card"]).pack(side="left")

        actions = tk.Frame(header, bg=THEME["bg_card"])
        actions.pack(side="right")
        ActionButton(actions, text="My Tickets", command=self.render_saved_tickets, bg_color=THEME["bg_panel"], hover_color=THEME["bg_input"], width=12).pack(side="left", padx=5)
        ActionButton(actions, text="Logout", command=self.terminate_session, bg_color=THEME["danger"], hover_color=THEME["accent_hover"], width=10).pack(side="left")

        layout = tk.Frame(self, bg=THEME["bg_root"], padx=15, pady=15)
        layout.pack(fill="both", expand=True)

        left_col = tk.Frame(layout, bg=THEME["bg_card"], padx=15, pady=15)
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 8))

        right_col = tk.Frame(layout, bg=THEME["bg_card"], padx=15, pady=15)
        right_col.pack(side="right", fill="both", expand=True, padx=(8, 0))

        tk.Label(left_col, text="Upcoming Events", font=(THEME["font_main"], 12, "bold"), fg=THEME["accent"], bg=THEME["bg_card"]).pack(anchor="w", pady=(0, 8))

        search_bar = tk.Entry(left_col, font=(THEME["font_main"], 10), bg=THEME["bg_input"], fg=THEME["text_main"], insertbackground=THEME["accent"], bd=0)
        search_bar.pack(fill="x", ipady=5, pady=(0, 8))

        grid = ttk.Treeview(left_col, columns=("ID", "Name", "Date", "Normal", "VIP"), show="headings", height=12)
        grid.heading("ID", text="ID")
        grid.heading("Name", text="Event Name")
        grid.heading("Date", text="Schedule")
        grid.heading("Normal", text="Normal Price")
        grid.heading("VIP", text="VIP Price")

        grid.column("ID", width=35)
        grid.column("Name", width=110)
        grid.column("Date", width=110)
        grid.column("Normal", width=75)
        grid.column("VIP", width=65)
        grid.pack(fill="both", expand=True)

        cache = {}

        def fetch_events():
            for item in grid.get_children():
                grid.delete(item)
            cache.clear()
            term = search_bar.get().strip().lower()
            try:
                for doc in db.collection("events").stream():
                    data = doc.to_dict()
                    if not term or term in data.get("name", "").lower():
                        cache[str(doc.id)] = data
                        grid.insert("", "end", iid=str(doc.id), values=(
                            str(doc.id), data.get("name"), data.get("date_time"),
                            f"₱{data.get('normal_price', 0.0):.2f}", f"₱{data.get('vip_price', 0.0):.2f}"
                        ))
            except Exception as ex:
                print(f"[ERROR] Event fetch failed: {ex}")

        search_bar.bind("<KeyRelease>", lambda e: fetch_events())

        seat_box = tk.Frame(right_col, bg=THEME["bg_card"])
        seat_box.pack(fill="both", expand=True)

        tk.Label(seat_box, text="Seat Selection Map", font=(THEME["font_main"], 12, "bold"), fg=THEME["accent"], bg=THEME["bg_card"]).pack(anchor="w", pady=(0, 5))
        
        legend_frame = tk.Frame(seat_box, bg=THEME["bg_card"])
        legend_frame.pack(anchor="w", pady=(0, 5))
        tk.Label(legend_frame, text="■ VIP (Gold)", fg=THEME["vip_gold"], bg=THEME["bg_card"], font=(THEME["font_main"], 9, "bold")).pack(side="left", padx=(0, 10))
        tk.Label(legend_frame, text="■ Normal", fg=THEME["text_muted"], bg=THEME["bg_card"], font=(THEME["font_main"], 9, "bold")).pack(side="left")

        # Scrollable area for seats
        canvas_container = tk.Frame(seat_box, bg=THEME["bg_card"])
        canvas_container.pack(fill="both", expand=True, pady=5)

        seat_canvas = tk.Canvas(canvas_container, bg=THEME["bg_card"], highlightthickness=0)
        seat_scrollbar = ttk.Scrollbar(canvas_container, orient="vertical", command=seat_canvas.yview)
        seat_canvas_frame = tk.Frame(seat_canvas, bg=THEME["bg_card"])

        seat_canvas_frame.bind(
            "<Configure>",
            lambda e: seat_canvas.configure(scrollregion=seat_canvas.bbox("all"))
        )
        seat_canvas.create_window((0, 0), window=seat_canvas_frame, anchor="nw")
        seat_canvas.configure(yscrollcommand=seat_scrollbar.set)

        seat_canvas.pack(side="left", fill="both", expand=True)
        seat_scrollbar.pack(side="right", fill="y")

        summary_label = tk.Label(seat_box, text="Selected Seats: None\nTotal: ₱0.00", font=(THEME["font_main"], 10, "bold"), fg=THEME["text_main"], bg=THEME["bg_card"], anchor="w")
        summary_label.pack(anchor="w", pady=(5, 10))

        def update_summary():
            data = self.active_event[1] if self.active_event else {}
            n_price = data.get("normal_price", 0.0)
            v_price = data.get("vip_price", 0.0)
            seats_dict = data.get("seats", {})

            total = 0.0
            for scode in self.selected_seats:
                stype = seats_dict.get(scode, {}).get("type", "Normal")
                total += v_price if stype == "VIP" else n_price

            s_text = ", ".join(self.selected_seats) if self.selected_seats else "None"
            summary_label.config(text=f"Selected Seats: {s_text} ({len(self.selected_seats)} tickets)\nTotal: ₱{total:.2f}")

        def toggle_seat(code):
            seats_dict = self.active_event[1].get("seats", {})
            styp = seats_dict.get(code, {}).get("type", "Normal")

            if code in self.selected_seats:
                self.selected_seats.remove(code)
                btn = self.seat_buttons[code]
                if styp == "VIP":
                    btn.config(bg=THEME["vip_gold"], fg="#000000")
                else:
                    btn.config(bg=THEME["bg_panel"], fg=THEME["text_main"])
            else:
                self.selected_seats.append(code)
                btn = self.seat_buttons[code]
                btn.config(bg=THEME["accent"], fg=THEME["text_main"])
            update_summary()

        def handle_event_click(e):
            selected = grid.selection()
            if not selected:
                return
            eid = selected[0]
            
            if eid not in cache:
                return

            self.active_event = (eid, cache[eid])
            self.selected_seats.clear()

            for w in seat_canvas_frame.winfo_children():
                w.destroy()

            self.seat_buttons.clear()
            seats_map = cache[eid].get("seats", {})
            
            r, c = 0, 0
            for seat_code, info in sorted(seats_map.items()):
                status = info.get("status", "available")
                stype = info.get("type", "Normal")

                if status == "available":
                    bg_col = THEME["vip_gold"] if stype == "VIP" else THEME["bg_panel"]
                    fg_col = "#000000" if stype == "VIP" else THEME["text_main"]
                    btn = tk.Button(
                        seat_canvas_frame, text=seat_code, bg=bg_col, fg=fg_col,
                        width=5, height=2, bd=0, relief="flat", cursor="hand2",
                        font=(THEME["font_main"], 9, "bold"),
                        command=lambda s=seat_code: toggle_seat(s)
                    )
                    self.seat_buttons[seat_code] = btn
                else:
                    btn = tk.Button(
                        seat_canvas_frame, text=seat_code, bg=THEME["bg_input"], fg=THEME["text_muted"],
                        width=5, height=2, bd=0, relief="flat", state="disabled",
                        font=(THEME["font_main"], 9)
                    )

                btn.grid(row=r, column=c, padx=3, pady=3)
                c += 1
                if c > 7:
                    c = 0
                    r += 1
            update_summary()

        grid.bind("<<TreeviewSelect>>", handle_event_click)
        fetch_events()

        def submit_booking():
            if not self.active_event or not self.selected_seats:
                messagebox.showerror("Incomplete Form", "Please pick an event and select at least one seat before proceeding.")
                return

            eid, data = self.active_event
            if not db.collection("events").document(str(eid)).get().exists:
                messagebox.showerror("Error", "This event has been deleted by the administrator.")
                fetch_events()
                return

            seats_dict = data.get("seats", {})
            n_price = data.get("normal_price", 0.0)
            v_price = data.get("vip_price", 0.0)

            total_amount = sum(v_price if seats_dict.get(s, {}).get("type") == "VIP" else n_price for s in self.selected_seats)

            try:
                ref = db.collection("bookings").document()
                self.active_booking_id = ref.id
                self.active_ref = f"REF-{uuid.uuid4().hex[:8].upper()}"

                ref.set({
                    "ref_no": self.active_ref,
                    "customer": self.user["username"],
                    "event_id": str(eid),
                    "event_name": data["name"],
                    "date_time": data.get("date_time", "N/A"),
                    "seats": list(self.selected_seats),
                    "seats_count": len(self.selected_seats),
                    "amount": total_amount,
                    "payment_method": "Pending",
                    "status": "Pending Payment",
                    "verified": False
                })
                self.render_checkout()
            except Exception as ex:
                messagebox.showerror("Error", f"Failed to generate transaction: {ex}")

        ActionButton(right_col, text="Proceed to Payment", command=submit_booking, width=22, height=2).pack(side="bottom", pady=8)

    def render_saved_tickets(self):
        self.clear_view()

        header = tk.Frame(self, bg=THEME["bg_card"], padx=20, pady=15)
        header.pack(fill="x")
        tk.Label(header, text="Purchased E-Tickets", font=(THEME["font_main"], 14, "bold"), fg=THEME["text_main"], bg=THEME["bg_card"]).pack(side="left")
        ActionButton(header, text="Back to Dashboard", command=self.render_customer_view, bg_color=THEME["bg_input"], hover_color="#3A1C21", width=16).pack(side="right")

        body = tk.Frame(self, bg=THEME["bg_root"], padx=20, pady=20)
        body.pack(fill="both", expand=True)

        grid = ttk.Treeview(body, columns=("RefNo", "Event", "Schedule", "Seats", "Method", "Amount", "Status"), show="headings")
        grid.heading("RefNo", text="Reference")
        grid.heading("Event", text="Event")
        grid.heading("Schedule", text="Date & Time")
        grid.heading("Seats", text="Seats")
        grid.heading("Method", text="Payment")
        grid.heading("Amount", text="Paid")
        grid.heading("Status", text="Status")

        grid.column("RefNo", width=100)
        grid.column("Event", width=120)
        grid.column("Schedule", width=120)
        grid.column("Seats", width=90)
        grid.column("Method", width=85)
        grid.column("Amount", width=75)
        grid.column("Status", width=80)
        grid.pack(fill="both", expand=True)

        try:
            records = db.collection("bookings").where("customer", "==", self.user["username"]).stream()
            for doc in records:
                b = doc.to_dict()
                b_status = b.get("status", "Pending")
                if b_status == "Cancelled by Staff":
                    status_display = "Cancelled by Staff"
                else:
                    eid = str(b.get("event_id"))
                    event_exists = db.collection("events").document(eid).get().exists
                    status_display = b_status if event_exists else "Event Cancelled"

                seats_str = ", ".join(b.get("seats", []))
                grid.insert("", "end", values=(
                    b.get("ref_no", doc.id), b.get("event_name"), b.get("date_time"),
                    seats_str, b.get("payment_method", "N/A"), f"₱{b.get('amount', 0.0):.2f}", status_display
                ))
        except Exception as ex:
            messagebox.showerror("Error", f"Could not load ticket history: {ex}")

    def render_checkout(self):
        self.clear_view()
        card = tk.Frame(self, bg=THEME["bg_card"], padx=40, pady=30)
        card.place(relx=0.5, rely=0.5, anchor="center")

        data = self.active_event[1]
        n_price = data.get("normal_price", 0.0)
        v_price = data.get("vip_price", 0.0)
        seats_dict = data.get("seats", {})
        amt = sum(v_price if seats_dict.get(s, {}).get("type") == "VIP" else n_price for s in self.selected_seats)

        tk.Label(card, text="CHECKOUT CONFIRMATION", font=(THEME["font_main"], 16, "bold"), fg=THEME["text_main"], bg=THEME["bg_card"]).pack(pady=(0, 6))
        tk.Label(card, text=f"Reference: {self.active_ref}", font=(THEME["font_main"], 10, "bold"), fg=THEME["text_muted"], bg=THEME["bg_card"]).pack(pady=(0, 2))
        tk.Label(card, text=f"Seats: {', '.join(self.selected_seats)}", font=(THEME["font_main"], 10), fg=THEME["text_muted"], bg=THEME["bg_card"]).pack(pady=(0, 2))
        tk.Label(card, text=f"Total Payable: ₱{amt:.2f}", font=(THEME["font_main"], 14, "bold"), fg=THEME["accent"], bg=THEME["bg_card"]).pack(pady=(0, 10))

        tk.Label(card, text="Select Payment Method:", font=(THEME["font_main"], 9, "bold"), fg=THEME["text_muted"], bg=THEME["bg_card"], anchor="w").pack(fill="x")
        payment_combo = ttk.Combobox(card, values=["Cash", "Bank Transfer", "E-Wallet (GCash/Maya)"], state="readonly")
        payment_combo.set("Bank Transfer")
        payment_combo.pack(fill="x", ipady=4, pady=(3, 12))

        tk.Label(card, text="Authorization Pin (Use '1234' for Sandbox test):", font=(THEME["font_main"], 9), fg=THEME["text_muted"], bg=THEME["bg_card"], anchor="w").pack(fill="x")
        code_input = tk.Entry(card, font=(THEME["font_main"], 12), bg=THEME["bg_input"], fg=THEME["text_main"], insertbackground=THEME["accent"], bd=0, justify="center")
        code_input.pack(fill="x", ipady=6, pady=(3, 15))

        def execute_payment():
            if code_input.get().strip() == "1234":
                self.active_payment_method = payment_combo.get()
                try:
                    db.collection("bookings").document(self.active_booking_id).update({
                        "status": "Paid",
                        "payment_method": self.active_payment_method
                    })
                    eid = str(self.active_event[0])
                    event_ref = db.collection("events").document(eid)
                    event_doc = event_ref.get()
                    if event_doc.exists:
                        edata = event_doc.to_dict()
                        seats_map = edata.get("seats", {})
                        for s in self.selected_seats:
                            if s in seats_map:
                                seats_map[s]["status"] = "booked"
                        event_ref.update({"seats": seats_map})

                    messagebox.showinfo("Success", f"Payment confirmed via {self.active_payment_method}. E-Tickets generated.")
                    self.render_pass_screen()
                except Exception as ex:
                    messagebox.showerror("Error", f"Transaction failure: {ex}")
            else:
                messagebox.showerror("Denied", "Invalid authorization pin.")

        ActionButton(card, text="Authorize Payment", command=execute_payment, width=25, height=2).pack(pady=(0, 8))
        ActionButton(card, text="Cancel Transaction", command=self.render_customer_view, bg_color=THEME["bg_input"], hover_color="#3A1C21", width=25, height=2).pack()

    def render_pass_screen(self):
        self.clear_view()
        card = tk.Frame(self, bg=THEME["bg_card"], padx=35, pady=35)
        card.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(card, text="PASS GENERATED", font=(THEME["font_main"], 16, "bold"), fg=THEME["accent"], bg=THEME["bg_card"]).pack(pady=(0, 15))

        box = tk.Frame(card, bg=THEME["bg_panel"], padx=20, pady=18)
        box.pack(fill="x", pady=(0, 20))

        data = self.active_event[1]
        n_price = data.get("normal_price", 0.0)
        v_price = data.get("vip_price", 0.0)
        seats_dict = data.get("seats", {})
        total_amt = sum(v_price if seats_dict.get(s, {}).get("type") == "VIP" else n_price for s in self.selected_seats)

        pass_data = [
            ("Reference:", self.active_ref),
            ("Account Holder:", self.user['username']),
            ("Event:", data['name']),
            ("Schedule:", data.get('date_time', 'N/A')),
            ("Seats:", ", ".join(self.selected_seats)),
            ("Payment Method:", self.active_payment_method),
            ("Total Paid:", f"₱{total_amt:.2f}"),
            ("Status:", "PAID")
        ]

        for k, v in pass_data:
            row = tk.Frame(box, bg=THEME["bg_panel"])
            row.pack(fill="x", pady=2)
            tk.Label(row, text=k, font=(THEME["font_main"], 9, "bold"), fg=THEME["text_muted"], bg=THEME["bg_panel"], width=16, anchor="w").pack(side="left")
            tk.Label(row, text=v, font=(THEME["font_main"], 9), fg=THEME["text_main"], bg=THEME["bg_panel"], anchor="w").pack(side="left")

        ActionButton(card, text="Back to Dashboard", command=self.render_customer_view, width=22, height=2).pack()

    # ------------------------------------------------------------------
    # STAFF INTERFACE
    # ------------------------------------------------------------------
    def render_staff_view(self):
        self.clear_view()

        header = tk.Frame(self, bg=THEME["bg_card"], padx=20, pady=15)
        header.pack(fill="x")
        tk.Label(header, text=f"Staff Control Dashboard ({self.user['username']})", font=(THEME["font_main"], 12, "bold"), fg=THEME["text_main"], bg=THEME["bg_card"]).pack(side="left")
        ActionButton(header, text="Logout", command=self.terminate_session, bg_color=THEME["danger"], hover_color=THEME["accent_hover"], width=10).pack(side="right")

        content = tk.Frame(self, bg=THEME["bg_root"], padx=20, pady=20)
        content.pack(fill="both", expand=True)

        verify_card = tk.Frame(content, bg=THEME["bg_card"], padx=20, pady=20)
        verify_card.pack(fill="x", pady=(0, 15))

        tk.Label(verify_card, text="Ticket Check-in System", font=(THEME["font_main"], 11, "bold"), fg=THEME["accent"], bg=THEME["bg_card"]).pack(anchor="w", pady=(0, 8))

        bar = tk.Frame(verify_card, bg=THEME["bg_card"])
        bar.pack(fill="x")

        code_input = tk.Entry(bar, font=(THEME["font_main"], 11), bg=THEME["bg_input"], fg=THEME["text_main"], insertbackground=THEME["accent"], bd=0)
        code_input.pack(side="left", fill="x", expand=True, ipady=7, padx=(0, 10))

        out_msg = tk.Label(verify_card, text="", font=(THEME["font_main"], 10, "bold"), bg=THEME["bg_card"], anchor="w")
        out_msg.pack(fill="x", pady=(8, 0))

        def run_verification():
            val = code_input.get().strip()
            if not val:
                messagebox.showerror("Error", "Please input a valid Reference code.")
                return
            try:
                matches = list(db.collection("bookings").where("ref_no", "==", val).stream())
                target = matches[0] if matches else db.collection("bookings").document(val).get()

                if target and (isinstance(target, firestore.DocumentSnapshot) and target.exists or matches):
                    payload = target.to_dict()
                    if payload.get("status") == "Cancelled by Staff":
                        out_msg.config(text="REJECTED: This ticket has been cancelled by staff.", fg=THEME["danger"])
                        return

                    eid = str(payload.get("event_id"))
                    if not db.collection("events").document(eid).get().exists:
                        out_msg.config(text="REJECTED: Associated event has been deleted by admin.", fg=THEME["danger"])
                        return

                    db.collection("bookings").document(target.id).update({"verified": True})
                    out_msg.config(
                        text=f"VALIDATED — Ref: {payload.get('ref_no', 'N/A')} | Holder: {payload.get('customer')} | Seats: {', '.join(payload.get('seats', []))}",
                        fg="#2A9D8F"
                    )
                    reload_logs()
                else:
                    out_msg.config(text="REJECTED: Booking reference not found.", fg=THEME["danger"])
            except Exception as ex:
                messagebox.showerror("Error", f"Verification exception: {ex}")

        ActionButton(bar, text="Verify Ticket", command=run_verification, width=14, height=2).pack(side="right")

        logs_card = tk.Frame(content, bg=THEME["bg_card"], padx=20, pady=20)
        logs_card.pack(fill="both", expand=True)

        log_top_frame = tk.Frame(logs_card, bg=THEME["bg_card"])
        log_top_frame.pack(fill="x", pady=(0, 8))

        tk.Label(log_top_frame, text="Transaction Audit Log (1st click = Cancel, 2nd click = Permanent Delete)", font=(THEME["font_main"], 11, "bold"), fg=THEME["text_main"], bg=THEME["bg_card"]).pack(side="left")

        def handle_delete_or_cancel_ticket():
            selected = grid.selection()
            if not selected:
                messagebox.showerror("Error", "Please select a ticket/booking row first.")
                return
            
            row_item = grid.item(selected[0])
            doc_id = selected[0]
            ref_val = row_item['values'][0]
            current_status = row_item['values'][5]

            try:
                doc_ref = db.collection("bookings").document(str(doc_id))
                doc_snap = doc_ref.get()

                if not doc_snap.exists:
                    query_matches = list(db.collection("bookings").where("ref_no", "==", ref_val).stream())
                    if query_matches:
                        doc_ref = query_matches[0].reference
                        doc_snap = query_matches[0]
                    else:
                        grid.delete(selected[0])
                        messagebox.showinfo("Success", "Orphaned log entry removed from view.")
                        return

                b_data = doc_snap.to_dict()

                if current_status == "Cancelled by Staff" or current_status == "Event Deleted" or ref_val == "N/A":
                    if messagebox.askyesno("Confirm Permanent Deletion", f"Do you want to permanently remove this ticket entry?"):
                        doc_ref.delete()
                        messagebox.showinfo("Success", "Ticket permanently deleted.")
                        reload_logs()
                else:
                    if messagebox.askyesno("Confirm Cancellation", f"Do you want to cancel ticket {ref_val}? (Clicking delete again later will permanently remove it)."):
                        doc_ref.update({"status": "Cancelled by Staff"})

                        eid = str(b_data.get("event_id"))
                        event_doc_ref = db.collection("events").document(eid)
                        event_doc = event_doc_ref.get()
                        if event_doc.exists:
                            edata = event_doc.to_dict()
                            seats_map = edata.get("seats", {})
                            for s in b_data.get("seats", []):
                                if s in seats_map:
                                    seats_map[s]["status"] = "available"
                            event_doc_ref.update({"seats": seats_map})

                        messagebox.showinfo("Success", "Ticket has been cancelled. Click delete again to remove permanently.")
                        reload_logs()
            except Exception as ex:
                messagebox.showerror("Error", f"Failed to process ticket: {ex}")

        ActionButton(log_top_frame, text="Delete/Cancel Ticket", command=handle_delete_or_cancel_ticket, bg_color=THEME["danger"], hover_color="#90242D", width=22).pack(side="right")

        grid = ttk.Treeview(logs_card, columns=("RefNo", "User", "Event", "Seats", "Method", "Status", "Verified"), show="headings")
        grid.heading("RefNo", text="Reference")
        grid.heading("User", text="User")
        grid.heading("Event", text="Event")
        grid.heading("Seats", text="Seats")
        grid.heading("Method", text="Payment")
        grid.heading("Status", text="Status")
        grid.heading("Verified", text="Checked-In")

        grid.column("RefNo", width=100)
        grid.column("User", width=80)
        grid.column("Event", width=110)
        grid.column("Seats", width=90)
        grid.column("Method", width=85)
        grid.column("Status", width=95)
        grid.column("Verified", width=70)
        grid.pack(fill="both", expand=True)

        def on_log_click(event):
            selected = grid.selection()
            if selected:
                row_item = grid.item(selected[0])
                ref_val = row_item['values'][0]
                code_input.delete(0, 'end')
                code_input.insert(0, str(ref_val))

        grid.bind("<<TreeviewSelect>>", on_log_click)

        def reload_logs():
            for i in grid.get_children():
                grid.delete(i)
            try:
                for doc in db.collection("bookings").stream():
                    b = doc.to_dict()
                    b_status = b.get("status", "Pending")
                    if b_status == "Cancelled by Staff":
                        status_val = "Cancelled by Staff"
                    else:
                        eid = str(b.get("event_id"))
                        event_exists = db.collection("events").document(eid).get().exists
                        status_val = b_status if event_exists else "Event Deleted"

                    grid.insert("", "end", iid=str(doc.id), values=(
                        b.get("ref_no", doc.id), b.get("customer"), b.get("event_name"),
                        ", ".join(b.get("seats", [])), b.get("payment_method", "N/A"), status_val, b.get("verified", False)
                    ))
            except Exception as ex:
                print(f"[ERROR] Failed loading log data: {ex}")

        reload_logs()

    # ------------------------------------------------------------------
    # ADMIN INTERFACE
    # ------------------------------------------------------------------
    def render_admin_view(self):
        self.clear_view()

        header = tk.Frame(self, bg=THEME["bg_card"], padx=20, pady=15)
        header.pack(fill="x")
        tk.Label(header, text=f"Administrator Operations Center ({self.user['username']})", font=(THEME["font_main"], 12, "bold"), fg=THEME["text_main"], bg=THEME["bg_card"]).pack(side="left")
        ActionButton(header, text="Logout", command=self.terminate_session, bg_color=THEME["danger"], hover_color=THEME["accent_hover"], width=10).pack(side="right")

        container = tk.Frame(self, bg=THEME["bg_root"], padx=20, pady=20)
        container.pack(fill="both", expand=True)

        panel = tk.Frame(container, bg=THEME["bg_root"])
        panel.place(relx=0.5, rely=0.4, anchor="center")

        def modal_add_event():
            win = tk.Toplevel(self)
            win.title("Create Event & Generate Seats")
            win.geometry("450x600")
            win.configure(bg=THEME["bg_card"])
            win.grab_set()

            tk.Label(win, text="EVENT CONFIGURATION", font=(THEME["font_main"], 12, "bold"), fg=THEME["accent"], bg=THEME["bg_card"]).pack(pady=(15, 10))

            tk.Label(win, text="Event ID", font=(THEME["font_main"], 8, "bold"), fg=THEME["text_muted"], bg=THEME["bg_card"], anchor="w").pack(fill="x", padx=28)
            eid_ent = tk.Entry(win, font=(THEME["font_main"], 10), bg=THEME["bg_input"], fg=THEME["text_main"], bd=0)
            eid_ent.pack(fill="x", padx=28, ipady=5, pady=(2, 6))

            tk.Label(win, text="Event Name", font=(THEME["font_main"], 8, "bold"), fg=THEME["text_muted"], bg=THEME["bg_card"], anchor="w").pack(fill="x", padx=28)
            name_ent = tk.Entry(win, font=(THEME["font_main"], 10), bg=THEME["bg_input"], fg=THEME["text_main"], bd=0)
            name_ent.pack(fill="x", padx=28, ipady=5, pady=(2, 6))

            tk.Label(win, text="Event Date (Month, Day, Year)", font=(THEME["font_main"], 8, "bold"), fg=THEME["text_muted"], bg=THEME["bg_card"], anchor="w").pack(fill="x", padx=28)
            date_frame = tk.Frame(win, bg=THEME["bg_card"])
            date_frame.pack(fill="x", padx=28, pady=(2, 6))

            months_list = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
            days_list = [f"{i:02d}" for i in range(1, 32)]

            m_combo = ttk.Combobox(date_frame, values=months_list, state="readonly", width=12)
            m_combo.set("November")
            m_combo.pack(side="left", padx=(0, 6))

            d_combo = ttk.Combobox(date_frame, values=days_list, state="readonly", width=6)
            d_combo.set("20")
            d_combo.pack(side="left", padx=(0, 6))

            y_ent = tk.Entry(date_frame, font=(THEME["font_main"], 10), bg=THEME["bg_input"], fg=THEME["text_main"], bd=0, width=8, justify="center")
            y_ent.insert(0, "2026")
            y_ent.pack(side="left", ipady=3)

            tk.Label(win, text="Event Time (HH:MM & AM/PM)", font=(THEME["font_main"], 8, "bold"), fg=THEME["text_muted"], bg=THEME["bg_card"], anchor="w").pack(fill="x", padx=28)
            time_frame = tk.Frame(win, bg=THEME["bg_card"])
            time_frame.pack(fill="x", padx=28, pady=(2, 6))

            hours_list = [f"{i:02d}" for i in range(1, 13)]
            minutes_list = [f"{i:02d}" for i in range(0, 60)]

            h_combo = ttk.Combobox(time_frame, values=hours_list, state="readonly", width=5)
            h_combo.set("08")
            h_combo.pack(side="left", padx=(0, 4))
            tk.Label(time_frame, text=":", font=(THEME["font_main"], 11, "bold"), fg=THEME["text_main"], bg=THEME["bg_card"]).pack(side="left", padx=(0, 4))
            min_combo = ttk.Combobox(time_frame, values=minutes_list, state="readonly", width=5)
            min_combo.set("00")
            min_combo.pack(side="left", padx=(0, 8))
            ampm_combo = ttk.Combobox(time_frame, values=["AM", "PM"], state="readonly", width=6)
            ampm_combo.set("PM")
            ampm_combo.pack(side="left")

            tk.Label(win, text="Normal Price (₱)", font=(THEME["font_main"], 8, "bold"), fg=THEME["text_muted"], bg=THEME["bg_card"], anchor="w").pack(fill="x", padx=28)
            normal_ent = tk.Entry(win, font=(THEME["font_main"], 10), bg=THEME["bg_input"], fg=THEME["text_main"], bd=0)
            normal_ent.pack(fill="x", padx=28, ipady=5, pady=(2, 6))

            tk.Label(win, text="VIP Price (₱)", font=(THEME["font_main"], 8, "bold"), fg=THEME["text_muted"], bg=THEME["bg_card"], anchor="w").pack(fill="x", padx=28)
            vip_ent = tk.Entry(win, font=(THEME["font_main"], 10), bg=THEME["bg_input"], fg=THEME["text_main"], bd=0)
            vip_ent.pack(fill="x", padx=28, ipady=5, pady=(2, 6))

            tk.Label(win, text="Total Seat Capacity (e.g. 150)", font=(THEME["font_main"], 8, "bold"), fg=THEME["text_muted"], bg=THEME["bg_card"], anchor="w").pack(fill="x", padx=28)
            limit_ent = tk.Entry(win, font=(THEME["font_main"], 10), bg=THEME["bg_input"], fg=THEME["text_main"], bd=0)
            limit_ent.pack(fill="x", padx=28, ipady=5, pady=(2, 6))

            def commit_event():
                eid = eid_ent.get().strip()
                name = name_ent.get().strip()
                year_val = y_ent.get().strip()
                n_price = normal_ent.get().strip()
                v_price = vip_ent.get().strip()
                limit_val = limit_ent.get().strip()

                if not all([eid, name, year_val, n_price, v_price, limit_val]):
                    messagebox.showerror("Error", "All parameters are required.", parent=win)
                    return

                try:
                    limit = int(limit_val)
                    np = float(n_price)
                    vp = float(v_price)

                    seats_map = {}
                    rows = math.ceil(limit / 10)
                    counter = 0
                    for r in range(rows):
                        row_let = chr(65 + r)
                        for c in range(1, 11):
                            if counter >= limit:
                                break
                            seat_code = f"{row_let}{c}"
                            stype = "VIP" if r < 2 else "Normal"
                            seats_map[seat_code] = {"status": "available", "type": stype}
                            counter += 1

                    sched = f"{m_combo.get()} {d_combo.get()}, {year_val} - {h_combo.get()}:{min_combo.get()} {ampm_combo.get()}"

                    db.collection("events").document(str(eid)).set({
                        "name": name,
                        "date_time": sched,
                        "normal_price": np,
                        "vip_price": vp,
                        "ticket_limit": limit,
                        "seats": seats_map
                    })
                    messagebox.showinfo("Success", f"Published event '{name}' with {limit} generated seats.", parent=win)
                    win.destroy()
                except ValueError:
                    messagebox.showerror("Error", "Prices, capacity, and year must be numerical values.", parent=win)
                except Exception as ex:
                    messagebox.showerror("Error", f"Failed to publish: {ex}", parent=win)

            ActionButton(win, text="Publish & Generate Seats", command=commit_event, width=24, height=2).pack(pady=12)

        def modal_delete_event():
            win = tk.Toplevel(self)
            win.title("Delete Event")
            win.geometry("520x420")
            win.configure(bg=THEME["bg_card"])
            win.grab_set()

            tk.Label(win, text="MANAGE & DELETE EVENTS", font=(THEME["font_main"], 12, "bold"), fg=THEME["danger"], bg=THEME["bg_card"]).pack(pady=(15, 10))

            frame = tk.Frame(win, bg=THEME["bg_card"], padx=20, pady=5)
            frame.pack(fill="both", expand=True)

            tree = ttk.Treeview(frame, columns=("ID", "Name", "Schedule"), show="headings", height=8)
            tree.heading("ID", text="Event ID")
            tree.heading("Name", text="Event Name")
            tree.heading("Schedule", text="Schedule")
            tree.column("ID", width=80)
            tree.column("Name", width=180)
            tree.column("Schedule", width=180)
            tree.pack(fill="both", expand=True, pady=(0, 10))

            def load_events_list():
                for i in tree.get_children():
                    tree.delete(i)
                try:
                    for doc in db.collection("events").stream():
                        d = doc.to_dict()
                        tree.insert("", "end", iid=str(doc.id), values=(str(doc.id), d.get("name"), d.get("date_time")))
                except Exception as ex:
                    print(f"[ERROR] Failed loading events list: {ex}")

            load_events_list()

            def delete_selected():
                selected = tree.selection()
                if not selected:
                    messagebox.showerror("Error", "Please select an event to delete.", parent=win)
                    return
                eid_str = selected[0]
                row = tree.item(selected[0])
                ename = row['values'][1]

                if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete event '{ename}' (ID: {eid_str})?", parent=win):
                    try:
                        db.collection("events").document(eid_str).delete()
                        try:
                            db.collection("events").document(str(int(eid_str))).delete()
                        except ValueError:
                            pass

                        messagebox.showinfo("Success", f"Event '{ename}' successfully deleted.", parent=win)
                        load_events_list()
                    except Exception as ex:
                        messagebox.showerror("Error", f"Failed to delete event: {ex}", parent=win)

            ActionButton(win, text="Delete Selected Event", command=delete_selected, bg_color=THEME["danger"], hover_color="#90242D", width=24, height=2).pack(pady=10)

        def modal_add_user():
            win = tk.Toplevel(self)
            win.title("Create User")
            win.geometry("380x380")
            win.configure(bg=THEME["bg_card"])
            win.grab_set()

            tk.Label(win, text="USER PROVISIONING", font=(THEME["font_main"], 12, "bold"), fg=THEME["accent"], bg=THEME["bg_card"]).pack(pady=(15, 10))

            tk.Label(win, text="Username", font=(THEME["font_main"], 8, "bold"), fg=THEME["text_muted"], bg=THEME["bg_card"], anchor="w").pack(fill="x", padx=28)
            u_ent = tk.Entry(win, font=(THEME["font_main"], 10), bg=THEME["bg_input"], fg=THEME["text_main"], bd=0)
            u_ent.pack(fill="x", padx=28, ipady=5, pady=(2, 8))

            tk.Label(win, text="Password", font=(THEME["font_main"], 8, "bold"), fg=THEME["text_muted"], bg=THEME["bg_card"], anchor="w").pack(fill="x", padx=28)
            p_ent = tk.Entry(win, show="*", font=(THEME["font_main"], 10), bg=THEME["bg_input"], fg=THEME["text_main"], bd=0)
            p_ent.pack(fill="x", padx=28, ipady=5, pady=(2, 8))

            tk.Label(win, text="Role Level", font=(THEME["font_main"], 8, "bold"), fg=THEME["text_muted"], bg=THEME["bg_card"], anchor="w").pack(fill="x", padx=28)
            r_combo = ttk.Combobox(win, values=["CUSTOMER", "STAFF", "ADMIN"], state="readonly")
            r_combo.set("CUSTOMER")
            r_combo.pack(fill="x", padx=28, ipady=3, pady=(2, 12))

            def commit_user():
                u = u_ent.get().strip()
                p = p_ent.get().strip()
                r = r_combo.get().strip()

                if not u or not p:
                    messagebox.showerror("Error", "Username and Password cannot be empty.", parent=win)
                    return

                try:
                    db.collection("users").document(u).set({"password": p, "role": r})
                    messagebox.showinfo("Success", f"Provisioned user '{u}'.", parent=win)
                    win.destroy()
                except Exception as ex:
                    messagebox.showerror("Error", f"Failed user save: {ex}", parent=win)

            ActionButton(win, text="Save User", command=commit_user, width=20, height=2).pack(pady=8)

        def fetch_analytics():
            win = tk.Toplevel(self)
            win.title("Financial Analytics & Revenue Report")
            win.geometry("860x520")
            win.configure(bg=THEME["bg_card"])
            win.grab_set()

            tk.Label(win, text="FINANCIAL ANALYTICS & REVENUE REPORT", font=(THEME["font_main"], 14, "bold"), fg=THEME["accent"], bg=THEME["bg_card"]).pack(pady=(15, 10))

            frame = tk.Frame(win, bg=THEME["bg_card"], padx=20, pady=10)
            frame.pack(fill="both", expand=True)

            tree = ttk.Treeview(frame, columns=("EventID", "EventName", "NormalPrice", "VIPPrice", "SoldTickets", "GrossRevenue"), show="headings", height=12)
            tree.heading("EventID", text="Event ID")
            tree.heading("EventName", text="Event Name")
            tree.heading("NormalPrice", text="Normal (₱)")
            tree.heading("VIPPrice", text="VIP (₱)")
            tree.heading("SoldTickets", text="Tickets Sold")
            tree.heading("GrossRevenue", text="Gross Revenue (₱)")

            tree.column("EventID", width=70)
            tree.column("EventName", width=180)
            tree.column("NormalPrice", width=95)
            tree.column("VIPPrice", width=95)
            tree.column("SoldTickets", width=90)
            tree.column("GrossRevenue", width=130)
            tree.pack(fill="both", expand=True, side="top")

            try:
                events_map = {}
                for doc in db.collection("events").stream():
                    d = doc.to_dict()
                    events_map[str(doc.id)] = {
                        "name": d.get("name"),
                        "normal_price": d.get("normal_price", 0),
                        "vip_price": d.get("vip_price", 0),
                        "sold": 0,
                        "revenue": 0.0
                    }

                bookings_stream = db.collection("bookings").stream()
                total_rev = 0.0
                total_tickets = 0

                for doc in bookings_stream:
                    b = doc.to_dict()
                    if b.get("status") == "Paid":
                        eid = str(b.get("event_id"))
                        if eid in events_map:
                            qty = b.get("seats_count", 1)
                            amt = b.get("amount", 0.0)
                            total_rev += amt
                            total_tickets += qty
                            events_map[eid]["sold"] += qty
                            events_map[eid]["revenue"] += amt

                for eid, data in events_map.items():
                    tree.insert("", "end", values=(
                        eid, data["name"], f"₱{data['normal_price']:.2f}", f"₱{data['vip_price']:.2f}", data["sold"], f"₱{data['revenue']:.2f}"
                    ))

                footer_frame = tk.Frame(win, bg=THEME["bg_panel"], padx=20, pady=12)
                footer_frame.pack(fill="x", padx=20, pady=10)

                tk.Label(footer_frame, text=f"Total Sold Tickets: {total_tickets}", font=(THEME["font_main"], 10, "bold"), fg=THEME["text_main"], bg=THEME["bg_panel"]).pack(side="left")
                tk.Label(footer_frame, text=f"Total Gross Revenue: ₱{total_rev:.2f}", font=(THEME["font_main"], 11, "bold"), fg=THEME["success"], bg=THEME["bg_panel"]).pack(side="right")

            except Exception as ex:
                messagebox.showerror("Error", f"Failed to generate analytics report: {ex}", parent=win)

            ActionButton(win, text="Close Report", command=win.destroy, width=18, height=2).pack(pady=10)

        def run_backup():
            try:
                snapshot = {"users": {}, "events": {}, "bookings": {}}
                for key in ["users", "events", "bookings"]:
                    for doc in db.collection(key).stream():
                        snapshot[key][str(doc.id)] = doc.to_dict()
                with open("system_backup.json", "w") as f:
                    json.dump(snapshot, f, indent=4)
                messagebox.showinfo("Backup Success", "Database state dumped to 'system_backup.json'.")
            except Exception as ex:
                messagebox.showerror("Error", f"Export failed: {ex}")

        ops = [
            ("Publish Events", modal_add_event),
            ("Delete Events", modal_delete_event),
            ("User Provisioning", modal_add_user),
            ("Financial Analytics", fetch_analytics),
            ("Database Backup", run_backup)
        ]

        for i, (txt, fn) in enumerate(ops):
            r, c = divmod(i, 2)
            ActionButton(panel, text=txt, command=fn, width=22, height=3).grid(row=r, column=c, padx=12, pady=12)

        ActionButton(container, text="Open Audit View", command=self.render_staff_view, bg_color=THEME["bg_panel"], hover_color=THEME["bg_input"], width=28, height=2).pack(side="bottom", pady=15)


if __name__ == "__main__":
    app = TicketBookingSystem()
    app.mainloop()