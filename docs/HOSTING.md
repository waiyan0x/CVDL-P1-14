# Host EDS Reader

The base container provides the website, OCR engines, and recognition pipeline dependencies. It includes the selected YOLO11s checkpoint, EasyOCR, both PaddleOCR models, and fine-tuned TrOCR.

## Prepare the build context

Start with a working checkout that reports all three engines in `/api/health`. The packaging script verifies the detector and TrOCR checkpoints and copies the local model files, application, route references, and curated samples into a new directory. It leaves out credentials, virtual environments, uploaded videos, and raw datasets.

```sh
python3 scripts/prepare_container_context.py .runtime/eds-deploy/context
docker build -t eds-reader .runtime/eds-deploy/context
docker run --rm -p 127.0.0.1:8080:8080 eds-reader
curl -fsS http://127.0.0.1:8080/api/health
```

Run the context preparation command with a fresh directory name after making changes. Allow time for model startup. The Docker health check verifies that all three engines are available.

## Publish on Cloud Run

Run the following from the repository root after signing in to Google Cloud and selecting a project with Cloud Run, Cloud Build, Artifact Registry, and billing enabled. Cloud Build builds the image for Linux x86-64.

```sh
gcloud run deploy eds-reader \
  --source .runtime/eds-deploy/context \
  --region asia-southeast1 \
  --port 8080 --cpu 2 --memory 8Gi \
  --concurrency 8 --min-instances 0 --max-instances 1 \
  --allow-unauthenticated
```

The deployed service has a 30 MB video upload limit. Keep one Uvicorn worker and at most one Cloud Run instance because uploaded video sessions are held in process memory. An instance restart clears uploaded sessions.

Open the HTTPS URL and check `/api/health`, then run a sample on Detect, compare all three OCR engines on Evaluation, and try a camera or short uploaded video on Live. The site uses browser speech by default. Configure ElevenLabs only through the host's secret settings when its API quota is intended for the deployment.

## Azure for Students deployment

The `eds-reader` Azure Container App in resource group `eds-reader-demo` serves the
website on HTTPS. The Express environment supports one container per replica.
That container starts TorchServe 0.12.0 and the Starlette web gateway together.
The detector is packaged as `eds-detector.mar` from the verified YOLO11s
checkpoint. TorchServe listens on the container’s loopback interface. Only the
gateway port 8080 receives Azure ingress.

Build for Linux x86-64 from the verified base image. That base already contains
the local OCR weights and frozen sample assets.

```sh
python3 -m pip install torch-model-archiver==0.12.0
python3 scripts/prepare_torchserve_context.py .runtime/eds-deploy/torchserve-next
az acr login --name edsreaderp114
docker buildx build --platform linux/amd64 --push \
  --build-arg EDS_BASE_IMAGE=YOUR_VERIFIED_BASE_IMAGE \
  --tag edsreaderp114.azurecr.io/eds-reader:YOUR_TAG \
  .runtime/eds-deploy/torchserve-next
az containerapp update --resource-group eds-reader-demo --name eds-reader \
  --image edsreaderp114.azurecr.io/eds-reader:YOUR_TAG
```

Use HTTP `/readyz` on port 8080 for the TorchServe revision’s startup and
readiness probes. The endpoint returns 200 after the detector worker and all
three OCR engines are available. Verify `/api/health` reports
`detector_runtime: torchserve`, then check Detect, Live, and Evaluation. Keep
one Uvicorn worker and zero idle to one running replica because uploaded video
sessions live in that process.

For rollback, restore both the earlier image and its probe configuration.
The earlier standalone gateway image does not implement `/readyz`. Keep the
student subscription spending limit enabled.
