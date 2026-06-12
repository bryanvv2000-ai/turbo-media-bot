FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV BOT_TOKEN=8921737314:AAFMI-GMqtVgXAQN2_vRVviKTNM3aygRbII
CMD ["python", "-u", "bot.py"]
