# Используем образ с уже установленным Python и Rust
FROM rustlang/rust:nightly

# Устанавливаем Python и pip
RUN apt update && apt install -y python3 python3-pip

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем всё в контейнер
COPY . .

# Устанавливаем зависимости
RUN pip3 install --upgrade pip && pip3 install -r requirements.txt

# Запуск бота
CMD ["python3", "bestversion.py"]
