# 📸 Instagram to Discord Forwarder

Bot otomatis berbasis **Python** yang berfungsi memantau postingan terbaru dari akun Instagram tertentu menggunakan **RapidAPI** dan meneruskannya ke channel **Discord** dalam bentuk Embed yang cantik.



---

## ✨ Fitur Utama

* **Real-time Monitoring**: Mengecek postingan baru secara otomatis setiap 10 menit.
* **Anti-Spam Persistence**: Dilengkapi sistem penyimpanan `seen_posts.json` agar bot tidak mengirim ulang konten yang sama saat bot restart.
* **Smart Sorting**: Menggunakan logika *timestamp* untuk mengabaikan "Pinned Post" sehingga hanya postingan yang benar-benar baru secara waktu yang dikirim.
* **Rich Embeds**: Menampilkan gambar, caption (dipotong otomatis jika terlalu panjang), dan link postingan asli.
* **Lightweight Deployment**: Dioptimalkan untuk dijalankan di platform cloud seperti **Railway.app**.

---

## 🚀 Teknologi yang Digunakan

* **Python 3.9+**
* **Discord.py**: Library utama untuk integrasi bot Discord.
* **Aiohttp**: Library untuk melakukan request API secara asinkron (non-blocking).
* **RapidAPI (Instagram Looter v2)**: API pihak ketiga untuk mengambil data profil Instagram.
* **Railway**: Platform Cloud untuk hosting bot secara kontinu.

---

## 🛠️ Persiapan Variabel (Environment Variables)

Sebelum melakukan deploy, pastikan kamu sudah menyiapkan variabel berikut di panel konfigurasi Railway:

| Variabel | Deskripsi |
| :--- | :--- |
| `DISCORD_TOKEN` | Token Bot kamu dari [Discord Developer Portal](https://discord.com/developers/applications). |
| `DISCORD_GUILD_ID` | ID Server Discord kamu (Aktifkan Developer Mode di Discord untuk menyalinnya). |
| `DISCORD_CHANNEL_NAME` | Nama channel tujuan (contoh: `ig-feed`). |
| `IG_USERNAME` | Username akun Instagram yang ingin dipantau (tanpa tanda @). |
| `RAPIDAPI_KEY` | API Key kamu dari [RapidAPI Dashboard](https://rapidapi.com/). |

---

## 📦 Cara Deploy ke Railway.app

Ikuti langkah-langkah berikut untuk menjalankan bot kamu secara 24/7:

### 1. Persiapkan Repositori GitHub
Pastikan folder proyek kamu berisi minimal 3 file berikut:
1.  `main.py` (Script bot yang sudah kita rapihkan).
2.  `requirements.txt` (Daftar library yang dibutuhkan).
3.  `Procfile` (Instruksi cara menjalankan script).

Isi file `requirements.txt`:
```text
discord.py
aiohttp
