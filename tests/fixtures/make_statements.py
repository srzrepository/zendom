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
def cashback(path):
    """card with a cash-back column before Amount (like Apple Card's Daily Cash)"""
    c = canvas.Canvas(path, pagesize=letter); W, H = letter; y = H - 60
    c.setFont("Helvetica-Bold", 12); c.drawString(36, y, "Example Card Statement"); c.setFont("Helvetica", 8); c.drawRightString(575, y, "Sep 1 - Sep 30, 2026"); y -= 30
    c.drawString(36, y, "Your September Balance  $73.50   Minimum Payment Due $25.00   Payment Due By Oct 31, 2026"); y -= 30
    c.setFont("Helvetica-Bold", 10); c.drawString(36, y, "Payments"); y -= 16
    c.setFont("Helvetica", 8); c.drawString(37, y, "Date"); c.drawString(106, y, "Description"); c.drawRightString(576, y, "Amount"); y -= 16
    c.drawString(36, y, "09/30/2026"); c.drawString(105, y, "ACH Deposit Internet transfer from account ending in 0000"); c.drawRightString(575, y, "-$400.00"); y -= 16
    c.drawString(36, y, "Total payments for this period"); c.drawRightString(575, y, "-$400.00"); y -= 30
    c.setFont("Helvetica-Bold", 10); c.drawString(36, y, "Transactions"); y -= 16
    c.setFont("Helvetica", 8); c.drawString(37, y, "Date"); c.drawString(106, y, "Description"); c.drawString(416, y, "Daily Cash"); c.drawRightString(576, y, "Amount"); y -= 18
    for d, desc, pct, cash, amt in (("09/02/2026", "SQ *EXAMPLE CAFE 12 MAIN ST PALO ALTO 94301 CA USA", "2%", "$0.99", "$49.50"),
                                     ("09/05/2026", "EXAMPLE HARDWARE 7 ELM ST MENLO PARK 94025 CA USA", "2%", "$0.48", "$24.00")):
        c.drawString(36, y, d); c.drawString(105, y, desc); c.drawString(415, y, pct); c.drawString(446, y, cash); c.drawRightString(575, y, amt); y -= 12
        c.drawString(105, y, "3% Daily Cash at Example"); c.drawString(416, y, "1%"); c.drawString(446, y, "$0.24"); y -= 14
    c.drawString(36, y, "Total Daily Cash this month"); c.drawString(446, y, "$1.47"); y -= 14
    c.drawString(36, y, "Total charges, credits and returns"); c.drawRightString(575, y, "$73.50")
    c.save()
cashback("card_cashback.pdf")
print("ok")
def two_line_checking(path):
    """Schwab-style checking: a generic type on the dated line, the merchant on the line below; 2 pages."""
    c = canvas.Canvas(path, pagesize=letter); W, H = letter
    rows = [("09/01", "Beginning Balance", "", "", "$1,000.00", None),
            ("09/01", "Visa Debit Card Point of Sale Purchase", "$23.26", "", "$976.74", "SQ *EXAMPLE COFFEE MENLO PAR Menlo Park, CA, US"),
            ("09/02", "Funds Transfer from Brokerage -0000", "", "$400.00", "$1,376.74", None),
            ("09/03", "Electronic Withdrawal", "$142.50", "", "$1,234.24", "EXAMPLECARD EPAYMENT ACH PMT 260903"),
            ("09/04", "Check", "$900.00", "", "$334.24", "Check Paid #101"),
            ("09/11", "Electronic Deposit", "", "$2,199.91", "$2,534.15", "EXAMPLE CO PAYROLL 260911~ Tran: ACHDD"),
            ("09/12", "Visa Debit Card Point of Sale Purchase", "$111.56", "", "$2,422.59", "SAFEWAY #0001 MENLO PARK, CA, US"),
            ("09/13", "Visa Debit Card Point of Sale Purchase", "$42.00", "", "$2,380.59", "VENMO *Example Friend Visa Direct, NY, US"),
            ("09/14", "Electronic Withdrawal", "$700.00", "", "$1,680.59", "EXAMPLE CREDIT CRD EPAY 260914~ Tran: ACHDW"),
            ("09/15", "Visa Debit Card Point of Sale Purchase", "$13.07", "", "$1,667.52", "TST* EXAMPLE TACOS Oakland, CA, US"),
            ("09/30", "Interest Paid", "", "$0.02", "$1,667.54", None),
            ("09/30", "Ending Balance", "", "", "$1,667.54", None)]
    def head(y):
        c.setFont("Helvetica", 8); c.drawString(50, y, "EXAMPLE PERSON Account Number Statement Period"); y -= 11
        c.drawString(50, y, "EXAMPLE LIVING TRUST 000000000000 September 1-30, 2026"); y -= 20
        c.setFont("Helvetica-Bold", 9); c.drawString(50, y, "Example Bank Investor Checking Account Number: 000000000000"); y -= 14
        c.setFont("Helvetica", 8); c.drawString(50, y, "Activity"); y -= 11; c.drawString(50, y, "Date"); y -= 11
        c.drawString(50, y, "Posted"); c.drawString(90, y, "Description"); c.drawRightString(420, y, "Debits"); c.drawRightString(490, y, "Credits"); c.drawRightString(560, y, "Balance")
        return y - 14
    y = head(H - 50); page_break = 6
    for i, (d, desc, deb, cred, bal, extra) in enumerate(rows):
        if i == page_break:
            c.setFont("Helvetica", 7); c.drawString(50, 40, "© 2026 Example Bank, SSB. All rights reserved. Member FDIC. Page 1 of 2"); c.showPage(); y = head(H - 50)
        c.setFont("Helvetica", 8); c.drawString(50, y, d); c.drawString(90, y, desc)
        if deb: c.drawRightString(420, y, deb)
        if cred: c.drawRightString(490, y, cred)
        c.drawRightString(560, y, bal); y -= 11
        if extra: c.drawString(90, y, extra); y -= 11
    c.setFont("Helvetica", 8); c.drawString(50, y - 10, "Checks Paid"); c.drawString(50, y - 21, "101 09/04/2026 $900.00")
    c.setFont("Helvetica", 7); c.drawString(50, 40, "© 2026 Example Bank, SSB. All rights reserved. Member FDIC. Page 2 of 2")
    c.save()
two_line_checking("checking_two_line.pdf")
