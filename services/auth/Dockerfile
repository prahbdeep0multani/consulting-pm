FROM python:3.12-slim AS builder
WORKDIR /build
RUN pip install hatchling
COPY shared/ /build/shared/
COPY services/auth/ /build/service/
RUN pip install --prefix=/install /build/shared/ && \
    pip install --prefix=/install /build/service/

FROM python:3.12-slim AS production
WORKDIR /app
RUN groupadd -r app && useradd -r -g app app
COPY --from=builder /install /usr/local
COPY shared/ /app/shared/
COPY services/auth/app/ /app/app/
COPY services/auth/alembic/ /app/alembic/
COPY services/auth/alembic.ini /app/alembic.ini
USER app
EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]

FROM builder AS development
WORKDIR /app
RUN pip install --prefix=/install watchfiles
COPY --from=builder /install /usr/local
EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]
