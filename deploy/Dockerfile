FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
COPY requirements-pi.txt /app/requirements.txt
RUN pip install -r requirements.txt
COPY . /app
ENV PORT=5000
CMD ["python","app.py"]
