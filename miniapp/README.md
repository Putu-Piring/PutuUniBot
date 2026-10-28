# Putu Piring Uni - Telegram Mini App (TMA)

A dedicated, lightweight Telegram Mini App for **Putu Piring Uni** (`@putu_uni_bot`).

---

## ✨ Features

- **Exclusive to Putu Piring Uni:** Tailored specifically for Putu Piring ordering with package selection, dynamic pricing, and live subtotal calculations.
- **Dynamic Operating Schedule:** Automatically detects current day in Malaysia (MYT):
  - **Sunday (Ahad):** Pickup at Kabin UiTM (4:00 PM – 5:00 PM), Cutoff 9:30 AM.
  - **Mon, Tue, Thu (Isnin, Selasa, Khamis):** Pickup beside Warung Cik Malik, Bedong (6:30 PM – 9:00 PM), Cutoff 5:00 PM.
  - **Wed, Fri, Sat:** Informs customers that today is closed and accepts pre-orders for the next open operating day.
- **Fulfillment Selector:** Delivery (+RM 0.50 with zones) vs Self-Pickup (Free / RM 0.00 with location map).
- **Telegram WebApp SDK Integration:**
  - Auto-prefills customer name and Telegram username via `window.Telegram.WebApp.initDataUnsafe`.
  - Native Telegram `MainButton` integration (`HANTAR PESANAN • RM X.XX`).
  - Haptic feedback on selection change, errors, and submission.
  - Direct delivery back into bot chat via `Telegram.WebApp.sendData(...)`.
- **Zero-Dependency & Lightning-Fast:** Pure Vanilla HTML5, CSS3, and JavaScript.

---

## 🚀 How to Host / Deploy

Telegram requires all Mini Apps to be served over **HTTPS** with a valid SSL certificate.

### Option A: GitHub Pages (Recommended / Free & Instant)
1. Push `miniapp/` to GitHub Pages under `https://naspenang.github.io/PutuUniBot/miniapp/` or a custom domain.
2. Configure the Mini App in @BotFather or in `appsettings.json`.

### Option B: Cloudflare Pages / Vercel
Deploy the `miniapp/` folder directly to Cloudflare Pages or Vercel with free automatic HTTPS.

### Option C: Local Testing
Run a quick Python local HTTP server:
```bash
cd D:\RepoTools\Github\naspenang\PutuUniBot\miniapp
python -m http.server 8080
```
Open `http://localhost:8080` in your browser. (The app includes a browser simulation fallback for testing outside Telegram).

---

## 🤖 Registering with @BotFather

To attach the Mini App to `@putu_uni_bot`:
1. Open `@BotFather` on Telegram.
2. Send `/newapp` (or `/mybots` -> select `@putu_uni_bot` -> **Bot Settings** -> **Menu Button** -> **Configure menu button**).
3. Set the WebApp URL to your HTTPS endpoint (e.g. `https://your-domain.com/miniapp/index.html`).
4. Set the Menu Button Title: `🛒 Pesan Putu Piring`.
