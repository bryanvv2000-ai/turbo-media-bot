# 🚀 Turbo Media Downloader Bot

Bot de Telegram para descargar videos de YouTube, TikTok, Instagram, Facebook y X/Twitter **sin marca de agua**.

## ✨ Características
- 5 descargas gratuitas por día por usuario
- Plan Premium ilimitado con Telegram Stars (⭐)
- Soporta: YouTube, TikTok, Instagram, Facebook, X/Twitter
- Base de datos SQLite integrada
- Listo para deploy en Render (gratis)

---

## 📋 Pasos para subir a Render

### 1. Sube el código a GitHub
1. Ve a [github.com/new](https://github.com/new) y crea un repo nuevo (ej: `turbo-media-bot`)
2. Sube estos 4 archivos:
   - `bot.py`
   - `requirements.txt`
   - `render.yaml`
   - `.python-version`

### 2. Crea el servicio en Render
1. Ve a [render.com](https://render.com) y crea una cuenta gratuita
2. Click en **"New +"** → **"Blueprint"**
3. Conecta tu repositorio de GitHub
4. Render detectará el `render.yaml` automáticamente
5. En la sección **Environment Variables**, agrega:
   - Key: `BOT_TOKEN`
   - Value: `TU_TOKEN_DE_BOTFATHER` (el que te dio BotFather)
6. Click en **"Apply"** — ¡listo!

### 3. Verifica que funciona
- Busca tu bot en Telegram: `@turbomediadownloader_bot`
- Envía `/start`
- Pega un link de TikTok o YouTube

---

## 💬 Comandos del bot
| Comando | Descripción |
|---------|-------------|
| `/start` | Mensaje de bienvenida |
| `/status` | Ver descargas usadas hoy |
| `/premium` | Comprar acceso ilimitado (Telegram Stars) |
| `/help` | Ayuda |

---

## ⚙️ Configuración (en bot.py)
```python
FREE_DAILY_LIMIT = 5    # descargas gratis por día
STARS_PRICE = 50        # precio en Telegram Stars (ajústalo a tu gusto)
```

---

## 🔧 Notas importantes
- **Render free plan:** el servicio "duerme" si no recibe peticiones en 15 min.
  Para evitarlo, actualiza a un plan de pago ($7/mes) o usa [UptimeRobot](https://uptimerobot.com) para hacer ping cada 5 min.
- **Base de datos:** SQLite se guarda en disco. En Render free los discos son efímeros (se resetean con cada deploy). Para persistencia usa **Render Disk** ($1/mes) o migra a PostgreSQL (Render tiene uno gratuito).
- **Videos grandes:** Telegram limita los archivos a 50 MB. Videos muy largos no se podrán enviar.
