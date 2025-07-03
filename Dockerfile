# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем Rust, если понадобятся зависимости с компиляцией
RUN apt update && \
    apt install -y curl gcc libpq-dev build-essential && \
    curl https://sh.rustup.rs -sSf | sh -s -- -y && \
    . "$HOME/.cargo/env"

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файлы проекта
COPY . .

# Устанавливаем зависимости
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Запуск бота
CMD ["python", "bestversion.py"]
