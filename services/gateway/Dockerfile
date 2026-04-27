FROM python:3.12-slim AS builder
WORKDIR /build
RUN pip install hatchling
COPY shared/ /build/shared/
COPY services/gateway/ /build/service/
RUN pip install --prefix=/install /build/shared/ && \
    pip install --prefix=/install /build/service/

FROM python:3.12-slim AS production
WORKDIR /app
RUN groupadd -r app && useradd -r -g app app
COPY --from=builder /install /usr/local
COPY shared/ /app/shared/
COPY services/gateway/app/ /app/app/
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

FROM builder AS development
WORKDIR /app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
