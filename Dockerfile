# App image — code layer only; deps come from starful-web-base
ARG BASE_IMAGE=starful-web-base:latest
FROM ${BASE_IMAGE}

WORKDIR /code
ENV PYTHONUNBUFFERED=1

COPY app/ app/
COPY scripts/build_data.py scripts/md_metadata.py scripts/slug_utils.py scripts/

RUN python scripts/build_data.py

EXPOSE 8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
