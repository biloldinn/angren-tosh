FROM python:3.10-slim

# Ishchi katalogni yaratish
WORKDIR /app

# Zaruriy kutubxonalarni o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kodni nusxalash
COPY . .

# Portni ochish
EXPOSE 8080

# Botni ishga tushirish (app.py orqali)
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080", "--log-file", "-"]
