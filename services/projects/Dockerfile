FROM python:3.12-slim AS builder
WORKDIR /build
RUN pip install hatchling
COPY shared/ /build/shared/
COPY services/projects/ /build/service/
RUN pip install --prefix=/install /build/shared/ && \
    pip install --prefix=/install /build/service/

FROM python:3.12-slim AS production
WORKDIR /app
RUN groupadd -r app && useradd -r -g app app
COPY --from=builder /install /usr/local
COPY shared/ /app/shared/
COPY services/projects/app/ /app/app/
COPY services/projects/alembic/ /app/alembic/
COPY services/projects/alembic.ini /app/alembic.ini
USER app
EXPOSE 8002
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "2"]

FROM builder AS development
WORKDIR /app
EXPOSE 8002
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002", "--reload"]
