"""
Load documentation articles for SmartDynamic Refilling.
Run: python manage.py load_documentation_articles
Use --replace to update existing articles with the same title.
"""
from datetime import datetime
from django.core.management.base import BaseCommand
from wrsm_app.models import Article


def article(title, date_str, body):
    """Parse 'December 26, 2025' -> datetime."""
    dt = datetime.strptime(date_str.strip(), "%B %d, %Y")
    return {"title": title, "date_published": dt, "body": body.strip()}


ARTICLES = [
    article(
        "System Overview: SmartDynamic Refilling",
        "December 26, 2025",
        """
## Core Purpose

SmartDynamic Refilling is a modern, responsive web application designed as a robust management system. It serves as a centralized platform for handling client data and operational workflows, built with a focus on reliability, offline accessibility, and seamless performance across devices.

## Key Functionalities

- **Centralized Client Management:** A data-driven backend (Django) that manages complex relationships and unique identifiers (such as client_uuid) to ensure data integrity.
 - **Centralized Client Management:** A data-driven backend (Django) that manages stations, customers, products, orders, and financial records with strong relational integrity.

- **Progressive Web App (PWA) Capabilities:** Fully optimized for mobile and desktop installation, allowing for offline access and a native-app-like experience.

- **Automated Deployment & High Availability:** Hosted on a Debian 13 environment utilizing a professional stack:
  - **Nginx:** Serving as a high-performance reverse proxy and static file handler.
  - **Gunicorn:** Managing the WSGI HTTP server for the Django application.
  - **Modern Frontend Stack:** Leveraging Tailwind CSS for responsive design and Alpine.js/jQuery for dynamic, interactive user interface elements.
  - **Secure Infrastructure:** Implementation of secure version control via Git and robust server configurations to ensure data safety and uptime.

## Technical Architecture

| Layer | Technology |
|-------|------------|
| Backend | Python / Django |
| Frontend | HTML5, Tailwind CSS, Alpine.js, JavaScript |
| Database | PostgreSQL |
| Server | Debian 13 (Trixie) |
| Web Server | Nginx & Gunicorn |
""",
    ),
    article(
        "Subscription Expiration Policy",
        "December 27, 2025",
        """
If your subscription expires, your station access is restricted until renewal. After successful renewal, your account access resumes based on your current subscription status.

## What happens when my subscription expires?

- **Feature access is limited:** The app redirects expired accounts to the subscription renewal flow.
- **Renewal is self-serve:** You can renew through the in-app payment flow and restore normal access.
- **Data handling:** This documentation does not define an automatic deletion schedule. If you need a formal retention policy, contact support/admin for the latest policy statement.

## Summary Table

| Status | Access | Action Required |
|--------|--------|-----------------|
| Active | Full access | None |
| Expired | Renewal page / restricted features | Renew subscription |
| Renewed | Access restored | Continue normal operations |
""",
    ),
    article(
        "Subscription Cancellation & Expiry",
        "December 27, 2025",
        """
If you decide to cancel your subscription, you will maintain full access to all system features until the end of your current billing cycle.

## Data Retention & Grace Period

- **Access After Cancellation:** Your service remains active until the official expiration date unless the cancellation is processed while the account is already expired.
- **Data Safety:** Once your subscription expires, your data is not immediately deleted. We provide a grace period to ensure your information remains secure while you decide on your next steps.
- **Reactivation:** To avoid data loss, please ensure you renew or export your data before the grace period ends.

For detailed information regarding expired subscriptions and recovery, please visit our **Subscription Expiration Policy**.
""",
    ),
    article(
        "Configuring the WRSMS Platform",
        "December 27, 2025",
        """
Settings are the backbone of the WRSMS platform. They allow you to define global defaults—such as order types, payment methods, and standard rates (e.g., pickup vs. delivery). Proper configuration is essential; without these foundational parameters, the system cannot function accurately.

By optimizing your settings, you can significantly reduce manual data entry. For example, when creating a new sales record, the form can auto-populate with your preferred order type. This saves time and minimizes the risk of human error during peak business hours.

Beyond transaction defaults, the Settings module enables the system to:

- **Monitor Inventory Levels:** Track gallon counts and consumables in real-time.
- **Manage Backwash Schedules:** Automate equipment maintenance alerts to ensure consistent water quality.
""",
    ),
    article(
        "Understanding Sales Recording Process",
        "January 4, 2026",
        """
Recording a sale is the core activity of your refilling station management. This guide explains how the system handles your data from the moment you enter a transaction to the automatic updates in your inventory and financial reports.

## 1. Entering Transaction Details

The process begins with gathering the essential details of the sale. You can select a **Customer** (optional) and the **Type of Order** (such as Delivery, Pickup, or Walk-in). You then build the order by choosing **Products** and entering the **Quantity**. The system automatically handles the Date and calculates the Price based on your station's specific rules.

## 2. Built-in Quality Checks

Before any data is saved, the system acts as a gatekeeper to ensure everything is accurate:

- **Subscription Verification:** It ensures your station is within its monthly transaction limits.
- **Completeness:** It prevents empty orders from being saved and ensures all numbers (like quantities) are valid.
- **Pricing Accuracy:** It double-checks that the correct rates are applied—for example, automatically applying a "Pickup" price for 20L refills if that's how your station is configured.

## 3. Automated Processing

When you click "Submit," the system performs several tasks simultaneously to save you time:

- **Permanent Recording:** The sale is logged into your station's permanent history.
- **Inventory Automation:** For water refills, the system automatically subtracts necessary supplies (like seals or caps) from your stock, keeping your inventory accurate without manual counting.
- **Financial Tracking:** A record of the balance is created in your Accounts Receivable ledger.
- **Smart Payment Handling:** If the sale is marked as Paid, the revenue is recorded immediately. If the customer has Store Credit, the system automatically applies it to the sale and updates the customer's remaining balance.
- **Offline Reliability:** If your internet connection drops, the system saves the record on your device and uploads it to the cloud automatically once you are back online.

## 4. Immediate Results

Once the sale is processed, you are returned to your list with a confirmation message. Behind the scenes, your Dashboards, Financial Reports, and Inventory Charts are updated instantly to reflect the new revenue and stock levels.

## 5. Error Prevention and Safety

If a mistake is made—such as entering an invalid quantity or forgetting a required field—the system blocks the save and highlights exactly what needs to be corrected. This ensures that your business data remains clean and reliable.
""",
    ),
    article(
        "Installation Guide",
        "January 6, 2026",
        """
This guide is designed to help users install the SmartDynamic Refilling (SDR) application. Since SDR is built as a Progressive Web App (PWA), you don't need to download it from an app store. You can install it directly from your web browser on almost any device.

The SmartDynamic Refilling app provides a seamless, app-like experience directly through your browser. Installing it allows for offline access, faster loading, and a dedicated icon on your home screen.

## 1. Installation on Android (Google Chrome)

1. Open Google Chrome on your Android device.
2. Navigate to the official URL: **https://wrsms.online**
3. Wait for a few seconds; a pop-up banner saying "Add SmartDynamic Refilling to Home Screen" may appear at the bottom.
4. If the banner doesn't appear: Tap the three vertical dots (⋮) in the top-right corner, then select **"Install app"** or **"Add to Home screen."**
5. Confirm by tapping **Install**. The app will now appear in your app drawer and on your home screen.

## 2. Installation on iOS (iPhone/iPad)

1. Open **Safari** (other browsers like Chrome on iOS do not support PWA installation).
2. Go to **https://wrsms.online**
3. Tap the **Share** button (the square icon with an upward arrow) at the bottom of the screen.
4. Scroll down and select **"Add to Home Screen."**
5. Tap **Add** in the top-right corner. The SDR icon will now appear on your iPhone home screen.

## 3. Installation on Desktop (Windows/macOS/Linux)

1. Open **Google Chrome** or **Microsoft Edge**.
2. Visit **https://wrsms.online**
3. In the address bar (URL bar), you will see a small **Install** icon (it looks like a computer screen with a downward arrow) on the right side.
4. Click the icon and select **Install**.
5. The app will now open in a standalone window without the browser tabs and can be pinned to your Taskbar or Dock.

## Why Install the SDR App?

- **Offline Capability:** Access essential management features even when your internet connection is unstable.
- **Faster Access:** Launch the system instantly from your home screen without typing the URL.
- **Full Screen:** Enjoy a clean interface without browser address bars and menus.
""",
    ),
    article(
        "Unlock More Value: Why Switching to Annual Billing is a Smart Business Move",
        "January 7, 2026",
        """
Running a water refilling station is a game of margins. Every peso saved on overhead is a peso that goes directly to your bottom line. At SmartDynamic Refilling (SDR), we are constantly looking for ways to help our subscribers grow their businesses and streamline their operations.

Today, we are excited to introduce a new payment option designed specifically for long-term partners: **Annual Billing**.

## What is the "Annual Transaction"?

Until now, SDR has operated on a flexible monthly subscription model. This is great for new businesses testing the waters. However, for established stations that rely on SDR daily to manage sales, inventory, and deliveries, monthly payments can be repetitive and, over time, more expensive.

The **Annual Transaction** allows you to pay for a full year of service upfront, in exchange for a significant discount.

## The Value Proposition: Do the Math

The core value of the annual plan is simple: You get 12 months of service for the price of roughly 10.5 months.

### Current Plan Rates (Monthly)

- **Sediment:** ₱149/month
- **Carbon:** ₱199/month
- **RO:** ₱249/month

> Note: Annual billing promos, bundled discounts, or temporary campaigns may change over time. Always check the live **Pricing** page for the latest values before payment.

## Beyond the Savings: Peace of Mind

- **Uninterrupted Service:** Never worry about forgetting to renew your plan on the 1st of the month. Your system stays online, your data stays accessible, and your operation never skips a beat.
- **Simplified Accounting:** Instead of managing 12 separate receipts and expense entries, you have just one invoice for the entire fiscal year.
- **Price Protection:** By locking in an annual rate, you are protected against any potential price adjustments that might happen during the year.

## Is the Annual Plan Right for You?

If you are just starting out and your cash flow is tight, the **Monthly Plan** remains a fantastic, flexible option with no long-term commitment.

However, if your station is up and running and you plan to be in business for the long haul, the **Annual Plan** is the financially responsible choice.

## How to Switch

1. Go to the **Pricing** page.
2. Toggle the switch at the top from "Monthly" to **"Annual"**.
3. Select your current plan (or upgrade to a higher tier).
4. Complete the secure payment transaction.

Thank you for trusting SmartDynamic Refilling to power your business.
""",
    ),
    article(
        "Getting Started with SmartDynamic Refilling (SDR)",
        "January 6, 2026",
        """
Now that you have installed the app, follow these steps to set up your account and begin managing your water refilling station efficiently.

## 1. Accessing the Dashboard

Once you open the app from your home screen, you will be greeted by the **Login Screen**.

- **Log In:** Enter your registered login email/username and your password.
- **Forgot Password?** Use the "Forgot Password" link to receive password reset instructions via email.
- **First Time?** You will be prompted to finish setting up your station settings.

## 2. Setting Up Your Station Profile

Before processing orders, ensure your business details are correct.

1. Navigate to **Settings** (gear icon) in the side menu.
2. **Verify Station Info:** Check your station name, address, and contact number. These details will appear on your digital receipts.

## 3. Registering Your Delivery Team

If your station offers delivery, you need to add your "Riders" or "Delivery Crew" to the system.

1. Go to **Station > Station Users** tab.
2. Click **Add New User** and select the role as **"driver"**.
3. Assign them a unique login so they can update the status of deliveries in real-time.

## Quick Tips for New Users

- **Sync Data:** If you've been working offline, ensure you connect to the internet at least once a day to sync your sales data to the cloud.
""",
    ),
    article(
        "Understanding Your Plan: What Counts as a \"Transaction\"?",
        "January 7, 2026",
        """
Choosing the right SmartDynamic Refilling (SDR) subscription plan (Sediment, Carbon, or RO) often comes down to one key metric: the **Transaction Limit**.

We often get asked: *"If a customer refills 10 containers, does that count as 10 transactions?"*

**The short answer is: No.** That counts as just **1 transaction**.

## The Golden Rule: 1 Record = 1 Transaction

In SDR, a "transaction" is defined by the **record of the sale**, not the number of water containers (gallons/jugs) filled.

Whether a customer walks in to refill a single 5-gallon slim container or a restaurant calls for a delivery of fifty 5-gallon round containers, as long as it is processed as a **single order entry** in the system, it counts as only **1 transaction**.

## Real-World Examples

**Scenario A: The Walk-In Customer**
- Action: Juan enters your station with 1 blue slim container.
- System Entry: You create a new sale for Juan for 1 Refill.
- **Count: 1 Transaction.**

**Scenario B: The Bulk Delivery**
- Action: "Mama's Eatery" orders a refill for 20 round containers and buys 5 new caps.
- System Entry: You create a single sale/order for "Mama's Eatery" listing 20 Refills and 5 Caps.
- **Count: Still just 1 Transaction.**

**Scenario C: The Separate Visits**
- Action: Maria refills 1 container in the morning. She comes back in the afternoon to refill another 1 container.
- System Entry: You create a sale in the morning. You create a new, separate sale in the afternoon.
- **Count: 2 Transactions** because they were entered as separate records at different times.

## Why This Matters for You

- **Sediment Plan (300 Transactions/Month):** This doesn't mean you can only refill 300 jugs. It means you can serve 300 customers (or orders). If your average customer refills 2 jugs, you're actually processing 600 jugs of water on this entry-level plan!
- **Carbon Plan (500 Transactions/Month):** Perfect for busier stations handling around 16–17 distinct orders every single day.
- **RO Plan (Unlimited):** For the powerhouses that process non-stop orders all day long.

## Tracking Your Usage

If your station reaches its plan limit, the system shows a warning/limit message during transaction processing so you can renew or upgrade as needed.

**Key Takeaway:** Focus on growing your volume per customer! Upselling more refills per visit is the smartest way to maximize your revenue without needing to upgrade your plan immediately.
""",
    ),
    article(
        "Understanding the Statement of Account: A Guide to Your Financial Overview",
        "January 8, 2026",
        """
The **Statement of Account (SOA)** is a vital tool for tracking the financial relationship between your water refilling station and your customers. It provides a chronological history of transactions, allowing both you and your customer to see exactly how much is owed at any given time.

## 1. Opening Balance

The **Opening Balance** is the starting point of your statement. It represents the total amount of unpaid debt carried over from the past, before the start of your selected date range.

- **The Logic:** It sums up every single sale made since the customer was registered and subtracts every payment they ever made, stopping exactly one day before the statement's "Start Date."
- **Significance:** This tells you the "starting debt" for the current period.

## 2. Total Debits

In accounting for a business owner, a **Debit** represents an increase in what is owed to you.

- **The Logic:** This is the sum of all new Sales and Invoices created within the selected date range.
- **Significance:** Every time you record a sale or dispatch an order that isn't immediately settled, the "Total Debits" will increase, reflecting the new value provided to the customer.

## 3. Total Credits

A **Credit** is the opposite of a debit; it represents a reduction in the customer's debt.

- **The Logic:** This is the sum of all Payments received from the customer within the selected date range.
- **Significance:** Whether they paid via Cash, GCash, or Bank Transfer, these entries reduce the customer's liability.

## 4. Closing Balance

The **Closing Balance** is the most important number on the statement. It is the final amount the customer owes you as of the "End Date" of the report.

**The Formula:**

- Opening Balance (Past Debt) + Total Debits (New Sales) − Total Credits (New Payments) = **Closing Balance (Current Owed)**

**Significance:**

- **Positive Number:** The customer has an outstanding balance to pay.
- **Zero (0):** The customer is fully cleared of all debt for this period.
- **Negative Number:** The customer has overpaid or has an advance credit on their account.

## Summary Table

| Term | Action | Effect on Debt |
|------|--------|----------------|
| Opening Balance | Carry-over from past | Initial debt |
| Total Debits | New Sales / Invoices | Increases debt |
| Total Credits | Payments Received | Decreases debt |
| Closing Balance | The Net Result | Final amount owed |
""",
    ),
    article(
        "AGREEMENT ON THE USE OF WATER JUG",
        "January 14, 2026",
        """
This agreement sets the proper use, handling, and return of the water jugs owned by the Supplier and used by the Retailer in the sale of purified water.

Download the form below by clicking the link when provided by your supplier: **KASUNDUAN SA PAGGAMIT NG WATER JUG**
""",
    ),
    article(
        "How to Login to SmartDynamic Refilling",
        "January 19, 2026",
        """
Follow these simple steps to access your account:

## Steps

1. **Open the Login Page:** Navigate to the SmartDynamic Refilling login page by clicking on the **"Login"** button in the navigation bar or by going directly to the login URL.

2. **Enter Your Credentials:**
   - **Username:** Enter your username. This is the email address you registered with.
   - **Password:** Enter your secret password.

3. **Select Your Station (if applicable):** Some accounts may require you to select a specific water station after logging in.

4. **Click Login:** Press the **"Login"** button to access your dashboard.

## Troubleshooting

- **Forgot Password?** Use the self-serve password reset. An instruction will be sent to your email.
- **Need more help?** Contact our support team on the [Contact us](/contact-us/) page.
""",
    ),
    article(
        "Subscription Renewal Flow (Manual GCash)",
        "April 22, 2026",
        """
This guide explains the current subscription renewal process using manual GCash payment proof and admin approval.

## Quick Flow

```text
Subscription expires
      ↓
User is redirected to Subscription Expired page
      ↓
User selects plan + billing cycle and pays via GCash
      ↓
User uploads payment proof + reference number
      ↓
Request status = Pending
      ↓
Admin reviews request
   ↙             ↘
Approve          Reject
  ↓                ↓
Subscription       User submits corrected/new proof
is activated
and extended
```

## Step-by-step

1. **Expiry enforcement**
   - Expired subscriptions are restricted by middleware and redirected to the renewal page.

2. **User payment submission**
   - User chooses plan and cycle (monthly/annual).
   - User sends payment to the GCash account shown on-screen.
   - User submits:
     - payment reference number
     - optional payer details
     - screenshot proof

3. **Pending request creation**
   - System creates a `pending` subscription payment request.
   - Duplicate pending requests for the same station are blocked.

4. **Admin decision**
   - Admin/staff opens the payment requests review screen.
   - Admin can approve or reject each request with optional note.

5. **If approved**
   - Subscription is updated automatically:
     - plan is set to selected plan
     - cycle extension is applied (`+30` days monthly, `+365` days annual)
     - `is_active=True`, `is_trial=False`

6. **If rejected**
   - Request is marked rejected with admin note.
   - User can submit a new proof.

## Notes

- PayMongo routes are currently disabled temporarily.
- Active renewal method is manual GCash proof submission with admin approval.
""",
    ),
]


class Command(BaseCommand):
    help = "Load documentation articles for SmartDynamic Refilling."

    def add_arguments(self, parser):
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Update existing articles with the same title.",
        )

    def handle(self, *args, **options):
        replace = options["replace"]
        created = 0
        updated = 0

        for a in ARTICLES:
            title = a["title"]
            body = a["body"]
            date_published = a["date_published"]

            existing = Article.objects.filter(title=title).first()
            if existing:
                if replace:
                    existing.body = body
                    existing.date_published = date_published
                    existing.save()
                    updated += 1
                    self.stdout.write(self.style.WARNING(f"Updated: {title}"))
                else:
                    self.stdout.write(self.style.NOTICE(f"Skipped (exists): {title}"))
            else:
                Article.objects.create(
                    title=title,
                    body=body,
                    date_published=date_published,
                )
                created += 1
                self.stdout.write(self.style.SUCCESS(f"Created: {title}"))

        self.stdout.write(
            self.style.SUCCESS(f"\nDone. Created {created}, updated {updated}.")
        )
