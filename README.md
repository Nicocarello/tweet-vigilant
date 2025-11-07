---

# 🚨 Mentions Alert System

Automated system that monitors **Twitter (X)** mentions of **Mercado Libre**, **Mercado Pago**, and **Marcos Galperin**, generating hourly email alerts with engagement metrics and tweet details.
Developed by **PÚBLiCA Latam – Data Team**.

---

## ⚙️ Overview

* Runs **hourly (07:00–23:00 ART)** via **GitHub Actions**
* Fetches tweets from predefined users using **Apify**
* Processes and filters mentions with **pandas**
* Sends **HTML email reports** with engagement data
* Routes alerts by mention:

  * **Mercado Libre → TO_EMAILS_MELI**
  * **Mercado Pago → TO_EMAILS_MP**
  * **Galperin → TO_EMAILS_GALPERIN**
* Sends only when new mentions are detected

---

## 🧩 Tech Stack

**Python 3.11**, `apify-client`, `pandas`, `numpy`, `python-dotenv`
Automated with **GitHub Actions** and **SMTP email** delivery.

---

## 🔑 Environment Variables

| Variable                                                 | Description                       |
| -------------------------------------------------------- | --------------------------------- |
| `APIFY_API`                                              | Apify API token                   |
| `ACTOR_ID`                                               | ID of the Apify Actor             |
| `SMTP_SERVER` / `SMTP_PORT`                              | SMTP configuration                |
| `FROM_EMAIL` / `PASSWORD`                                | Sender credentials                |
| `TO_EMAILS_MELI` / `TO_EMAILS_MP` / `TO_EMAILS_GALPERIN` | Recipient lists                   |
| `USUARIOS`                                               | Comma-separated Twitter usernames |

Example `.env`:

```bash
APIFY_API=your-apify-token
ACTOR_ID=user~actor-id
SMTP_SERVER=smtp.office365.com
FROM_EMAIL=alerts@publicalatam.com
PASSWORD=********
TO_EMAILS_MELI=team@publicalatam.com
USUARIOS=user1,user2
```

---

## 🕒 GitHub Actions

Workflow `.github/workflows/alerta.yml` runs hourly between **07:00–23:00 ART**:

```yaml
on:
  schedule:
    - cron: "0 10-23 * * *"
    - cron: "0 0-2 * * *"
```

---

## 🧠 How It Works

1. The workflow triggers the Python script.
2. The script runs an Apify Actor to collect tweets.
3. Mentions are grouped by topic (Mercado Libre / Pago / Galperin).
4. An HTML summary email is sent to each corresponding list.
5. Hash-based deduplication avoids repeated alerts.

---

## 📬 Example Output

Each email includes:

* Tweet author and profile picture
* Text content and link
* Engagement metrics (views, likes, retweets, replies)

---

## 👤 Author

Developed by **PÚBLiCA Latam – Data & Insights Team**
Contact: [nicolas.carello@publicalatam.com](mailto:nicolas.carello@publicalatam.com)

---

Would you like me to add badges at the top (e.g. Python version, build passing, last run) to make it look more polished for GitHub?
