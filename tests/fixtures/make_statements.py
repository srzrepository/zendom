"""Fictional sample statements for tests (made-up bank, made-up purchases)."""
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
def card(path, closing, start, rows, payments):
    c = canvas.Canvas(path, pagesize=letter); W, H = letter; y = H - 60
    c.setFont("Helvetica-Bold", 14); c.drawString(50, y, "Example Bank Rewards Card"); y -= 18
    c.setFont("Helvetica", 9); c.drawString(50, y, f"Statement Period {start} - {closing}"); c.drawString(350, y, "Minimum Payment Due $35.00"); y -= 14
    c.drawString(50, y, f"New Balance $1,234.56   Credit Limit $5,000.00"); y -= 30
    def table(title, items):
        nonlocal y
        c.setFont("Helvetica-Bold", 10); c.drawString(50, y, title); y -= 14
        c.setFont("Helvetica-Bold", 8); c.drawString(50, y, "Trans Date"); c.drawString(110, y, "Post Date"); c.drawString(170, y, "Description"); c.drawRightString(560, y, "Amount"); y -= 12
        c.setFont("Helvetica", 8)
        for td, pd, desc, amt in items:
            c.drawString(50, y, td); c.drawString(110, y, pd); c.drawString(170, y, desc); c.drawRightString(560, y, amt); y -= 12
        y -= 10
    table("Payments and Other Credits", payments); table("Purchases", rows)
    c.setFont("Helvetica-Bold", 8); c.drawString(170, y, "Total purchases for this period"); c.drawRightString(560, y, "$999.99")
    c.save()
def checking(path):
    c = canvas.Canvas(path, pagesize=letter); W, H = letter; y = H - 60
    c.setFont("Helvetica-Bold", 14); c.drawString(50, y, "Example Credit Union - Everyday Checking"); y -= 18
    c.setFont("Helvetica", 9); c.drawString(50, y, "Statement Period: September 15, 2026 through October 14, 2026"); y -= 30
    c.setFont("Helvetica-Bold", 8)
    for x, t in ((50, "Date"), (100, "Description")): c.drawString(x, y, t)
    for x, t in ((420, "Withdrawals"), (490, "Deposits"), (560, "Balance")): c.drawRightString(x, y, t)
    y -= 12; c.setFont("Helvetica", 8)
    rows = [("09/15", "Beginning Balance", "", "", "2,000.00"), ("09/18", "PG&E UTILITY BILL", "84.20", "", "1,915.80"),
            ("10/01", "PAYROLL DIRECT DEP EXAMPLE CO", "", "2,201.81", "4,117.61"), ("10/02", "ONLINE TRANSFER TO SAVINGS", "500.00", "", "3,617.61"),
            ("10/05", "EXAMPLE CARD AUTOPAY PAYMENT", "350.00", "", "3,267.61"), ("10/09", "FARMERS MARKET", "23.50", "", "3,244.11"),
            ("10/14", "Ending Balance", "", "", "3,244.11")]
    for d, desc, w, dep, bal in rows:
        c.drawString(50, y, d); c.drawString(100, y, desc)
        if w: c.drawRightString(420, y, w)
        if dep: c.drawRightString(490, y, dep)
        c.drawRightString(560, y, bal); y -= 12
    c.save()
card("card_oct.pdf", "10/28/2026", "09/29/2026",
     [("10/03", "10/05", "TRADER JOE'S #123 SAN JOSE CA", "184.50"), ("10/11", "10/12", "BLUE BOTTLE COFFEE", "6.75"),
      ("10/20", "10/21", "AMAZON MKTPLACE PMTS", "64.99"), ("10/22", "10/23", "AMAZON MKTPLACE RETURN", "-64.99")],
     [("10/15", "10/15", "AUTOPAY PAYMENT - THANK YOU", "-350.00")])
card("card_jan.pdf", "01/14/2027", "12/15/2026",
     [("12/20", "12/21", "HOLIDAY GIFT SHOP", "42.00"), ("01/05", "01/06", "CORNER BAKERY", "12.25")], [])
checking("checking.pdf")
print("ok")
