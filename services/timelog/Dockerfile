FROM python:3.12-slim AS builder
WORKDIR /build
RUN pip install hatchling
COPY shared/ /build/shared/
COPY services/timelog/ /build/service/
RUN pip install --prefix=/install /build/shared/ && \
    pip install --prefix=/install /build/service/

FROM python:3.12-slim AS production
WORKDIR /app
RUN groupadd -r app && useradd -r -g app app
COPY --from=builder /install /usr/local
COPY shared/ /app/shared/
COPY services/timelog/app/ /app/app/
USER app
EXPOSE 8003
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003", "--workers", "2"]

FROM builder AS development
WORKDIR /app
EXPOSE 8003
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003", "--reload"]
