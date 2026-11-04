# The Travaux DB API: api/server.py (standard library, and numpy for Ask) over a read-only SQLite file mounted at /data.
# Built from the bundle that deploy/build_bundle.py assembles; the scans, the pipeline and the site stay out.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
# numpy for Ask's vector search (api/server.py ask()); everything else is the standard library
RUN pip install --no-cache-dir numpy==2.3.1
COPY api/server.py api/server.py
COPY mcp/travaux_mcp.py mcp/travaux_mcp.py
COPY data/concordance data/concordance
COPY data/gold data/gold
COPY eval eval

# The database is mounted by docker-compose at /data (read-only); the server also opens it with mode=ro.
ENV TRAVAUX_ROOT=/app \
    TRAVAUX_DB=/data/travaux.sqlite3 \
    TRAVAUX_SCANS=/nonexistent \
    HOST=0.0.0.0 \
    PORT=8003

RUN useradd --system --no-create-home travaux
USER travaux

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8003/health',timeout=3).status==200 else 1)"

EXPOSE 8003
CMD ["python", "api/server.py"]
