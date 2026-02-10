from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.datatables import MDDataTable
from kivymd.uix.pickers import MDDatePicker
from kivy.metrics import dp
from kivy.uix.screenmanager import Screen
from datetime import datetime
import sqlite3

KV = '''
ScreenManager:
    MenuScreen:
    IncomeScreen:
    ExpenseScreen:
    ViewScreen:

<MenuScreen>:
    name: "menu"
    MDBoxLayout:
        orientation: "vertical"
        padding: 20
        spacing: 15

        MDLabel:
            text: "VB's Personal Exp Note"
            halign: "center"
            font_style: "H5"

        MDRaisedButton:
            text: "Income"
            on_release: app.root.current = "income"

        MDRaisedButton:
            text: "Expenses"
            on_release: app.root.current = "expense"

        MDRaisedButton:
            text: "View Transaction (Current Month)"
            on_release: app.open_view("month")

        MDRaisedButton:
            text: "Monthly Statement (All)"
            on_release: app.open_view("all")

        MDRaisedButton:
            text: "Exit"
            md_bg_color: 1,0,0,1
            on_release: app.stop()

<IncomeScreen>:
    name: "income"
    MDBoxLayout:
        orientation: "vertical"
        padding: 20
        spacing: 10

        MDTopAppBar:
            title: "Income"
            left_action_items: [["arrow-left", lambda x: app.go_home()]]

        MDTextField:
            id: amount
            hint_text: "Add Amount"
            input_filter: "float"

        MDTextField:
            id: desc
            hint_text: "Description"

        MDTextField:
            id: date
            hint_text: "Select Date"
            readonly: True
            on_focus: if self.focus: app.open_date_picker(self)

        MDRaisedButton:
            text: "Save"
            on_release: app.save_transaction("CR")

<ExpenseScreen>:
    name: "expense"
    MDBoxLayout:
        orientation: "vertical"
        padding: 20
        spacing: 10

        MDTopAppBar:
            title: "Expenses"
            left_action_items: [["arrow-left", lambda x: app.go_home()]]

        MDTextField:
            id: amount
            hint_text: "Less Amount"
            input_filter: "float"

        MDTextField:
            id: desc
            hint_text: "Description"

        MDTextField:
            id: date
            hint_text: "Select Date"
            readonly: True
            on_focus: if self.focus: app.open_date_picker(self)

        MDRaisedButton:
            text: "Save"
            on_release: app.save_transaction("DR")

<ViewScreen>:
    name: "view"
    MDBoxLayout:
        orientation: "vertical"

        MDTopAppBar:
            id: bar
            title: ""
            left_action_items: [["arrow-left", lambda x: app.go_home()]]

        MDBoxLayout:
            id: table_box
            orientation: "vertical"
'''

class MenuScreen(Screen): pass
class IncomeScreen(Screen): pass
class ExpenseScreen(Screen): pass
class ViewScreen(Screen): pass

class ExpenseApp(MDApp):

    def build(self):
        self.db = sqlite3.connect("expense.db")
        self.cur = self.db.cursor()
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS txn (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                date_sort TEXT,
                description TEXT,
                cr REAL,
                dr REAL
            )
        """)
        self.db.commit()
        return Builder.load_string(KV)

    # ---------- NAV ----------
    def go_home(self):
        self.root.current = "menu"

    # ---------- DATE PICKER ----------
    def open_date_picker(self, field):
        self.active_date_field = field
        picker = MDDatePicker()
        picker.bind(on_save=self.on_date_selected)
        picker.open()

    def on_date_selected(self, instance, value, date_range):
        display = value.strftime("%d-%m-%Y")
        self.active_date_field.text = display

    # ---------- SAVE ----------
    def save_transaction(self, ttype):
        scr = self.root.get_screen("income" if ttype == "CR" else "expense")

        if not scr.ids.amount.text or not scr.ids.date.text:
            return

        amount = float(scr.ids.amount.text)
        desc = scr.ids.desc.text
        raw_date = scr.ids.date.text

        # SAFE date parsing (supports DD-MM-YYYY & DD:MM:YYYY)
        raw_date = raw_date.replace(":", "-")
        d = datetime.strptime(raw_date, "%d-%m-%Y")

        sort_date = d.strftime("%Y-%m-%d")
        show_date = d.strftime("%d:%m:%Y")

        cr = amount if ttype == "CR" else 0
        dr = amount if ttype == "DR" else 0

        self.cur.execute(
            "INSERT INTO txn(date, date_sort, description, cr, dr) VALUES (?,?,?,?,?)",
            (show_date, sort_date, desc, cr, dr)
        )
        self.db.commit()

        scr.ids.amount.text = ""
        scr.ids.desc.text = ""
        scr.ids.date.text = ""
        self.root.current = "menu"

    # ---------- VIEW ----------
    def open_view(self, mode):
        self.root.current = "view"
        self.load_table(mode)

    def load_table(self, mode):
        view = self.root.get_screen("view")
        box = view.ids.table_box
        box.clear_widgets()

        now = datetime.now().strftime("%Y-%m")

        if mode == "month":
            view.ids.bar.title = "View Transaction (Current Month)"

            self.cur.execute(
                "SELECT IFNULL(SUM(cr-dr),0) FROM txn WHERE substr(date_sort,1,7) < ?",
                (now,)
            )
            opening = self.cur.fetchone()[0]

            self.cur.execute(
                "SELECT date, description, cr, dr FROM txn WHERE substr(date_sort,1,7)=? ORDER BY date_sort",
                (now,)
            )
        else:
            view.ids.bar.title = "Monthly Statement (All)"
            opening = 0
            self.cur.execute(
                "SELECT date, description, cr, dr FROM txn ORDER BY date_sort"
            )

        rows = self.cur.fetchall()
        balance = opening
        data = []

        data.append(("[b]OPEN[/b]", "-", "-", "-", f"[b]{balance:.2f}[/b]"))

        for date, desc, cr, dr in rows:
            balance += cr - dr
            cr_t = f"[color=0000ff]{cr:.2f}[/color]" if cr else "-"
            dr_t = f"[color=ff0000]{dr:.2f}[/color]" if dr else "-"
            bal_c = "0000ff" if balance >= 0 else "ff0000"

            data.append((date, desc, cr_t, dr_t, f"[color={bal_c}]{balance:.2f}[/color]"))

        table = MDDataTable(
            size_hint=(1,1),
            rows_num=8,
            use_pagination=True,
            column_data=[
                ("Date", dp(25)),
                ("Description", dp(40)),
                ("Income", dp(20)),
                ("Expense", dp(20)),
                ("Balance", dp(25)),
            ],
            row_data=data
        )

        box.add_widget(table)

if __name__ == "__main__":
    ExpenseApp().run()
