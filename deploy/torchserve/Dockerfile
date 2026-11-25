ARG EDS_BASE_IMAGE
FROM pytorch/torchserve:0.12.0-cpu AS torchserve
FROM eclipse-temurin:17-jre-jammy AS java
FROM ${EDS_BASE_IMAGE}

# TorchServe 0.12 distributes its Python server and Java archive in a pure Python wheel.
COPY --from=torchserve /home/venv/lib/python3.9/site-packages/ts /usr/local/lib/python3.12/site-packages/ts
COPY --from=java /opt/java/openjdk /opt/java/openjdk
COPY backend/app/ /app/backend/app/
COPY config.properties /app/torchserve/config.properties
COPY eds-detector.mar /app/torchserve/model-store/eds-detector.mar

ENV JAVA_HOME=/opt/java/openjdk \
    EDS_TORCHSERVE_PORT=8180 \
    YOLO_AUTOINSTALL=false
HEALTHCHECK --start-period=120s --interval=30s --timeout=5s \
    CMD python -c 'import os, urllib.request; url = "http://127.0.0.1:" + os.environ.get("PORT", "8080") + "/readyz"; urllib.request.urlopen(url, timeout=4).close()'
ENTRYPOINT ["python", "-m", "backend.app.hosted"]
