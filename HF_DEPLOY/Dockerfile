FROM python:3.10-slim

# Non-root user yaratish (Hugging Face talabi)
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

# Ishchi katalogni yaratish
WORKDIR /app

# Zaruriy kutubxonalarni o'rnatish
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kodni nusxalash
COPY --chown=user . .

# Portni ochish (Hugging Face uchun 7860)
EXPOSE 7860

# Botni ishga tushirish
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:7860", "--log-file", "-"]
