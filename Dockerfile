FROM python:3.12-slim


ENV PYTHONUNBUFFERED = 1
ENV PYTHONDONTWRITEBYTECODE=1


WORKDIR  money_transfer/

RUN apt-get update &&  \
    apt-get install -y build-essential libpq-dev &&  \
    apt-get install -y postgresql-client && \
    rm -rf /var/lib/apt/lists/*


COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

#CMD ["fastapi","run", "src"]