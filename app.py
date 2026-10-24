"""Streamlit image captioning with Prometheus instrumentation."""

import csv
import logging
import time
import uuid
from io import StringIO

import streamlit as st
from prometheus_client import start_http_server

from captioner import CPUCaptioner
from metrics import METRICS, session_bucket
from uploads import UploadError, load_image, read_zip

logger = logging.getLogger(__name__)

st.set_page_config(page_title="Image Captioning", page_icon="📷", layout="wide")


@st.cache_resource
def start_metrics():
    return start_http_server(8001, addr="127.0.0.1")


@st.cache_resource
def get_captioner():
    return CPUCaptioner()


def run_job(upload, mode, client_bucket):
    started = time.perf_counter()
    job_status = "failed"
    results = []

    with METRICS.active_jobs.labels(mode).track_inprogress():
        try:
            data = upload.getvalue()
            try:
                items = (
                    [(upload.name, data)]
                    if mode == "single"
                    else read_zip(data)
                )
            except UploadError as exc:
                job_status = "rejected"
                st.error(str(exc))
                return []

            with st.spinner("Preparing the captioning model..."):
                captioner = get_captioner()

            progress = st.progress(0.0)
            message = st.empty()

            for index, (name, content) in enumerate(items, start=1):
                message.write(f"Processing {index}/{len(items)}: {name}")
                image_start = time.perf_counter()
                image_status = "failed"
                caption = ""
                error = ""

                try:
                    image = load_image(content)
                    if mode == "single":
                        st.image(image, caption=name, width=400)
                    caption = captioner.caption(image, mode=mode)
                    image_status = "success"
                except UploadError as exc:
                    error = str(exc)
                except Exception:
                    logger.exception("Caption generation failed")
                    error = "Caption generation failed. See the terminal."
                finally:
                    elapsed = time.perf_counter() - image_start
                    METRICS.images.labels(mode, image_status).inc()
                    METRICS.image_duration.labels(
                        mode, image_status
                    ).observe(elapsed)

                results.append({
                    "image": name,
                    "status": image_status,
                    "caption": caption,
                    "seconds": round(elapsed, 3),
                    "error": error,
                })
                progress.progress(index / len(items))

            succeeded = sum(row["status"] == "success" for row in results)
            if succeeded == len(results):
                job_status = "success"
            elif succeeded:
                job_status = "partial"
            else:
                job_status = "failed"

            message.write("Processing finished.")
            return results

        except Exception:
            logger.exception("Upload job failed")
            st.error("Could not complete the job. Check the terminal for details.")
            return results

        finally:
            METRICS.jobs.labels(mode, job_status, client_bucket).inc()
            METRICS.job_duration.labels(mode).observe(
                time.perf_counter() - started
            )


try:
    start_metrics()
except OSError:
    logger.exception("Could not start the metrics endpoint")
    st.error("The monitoring endpoint could not start. Check port 8001.")
    st.stop()

if "client_session" not in st.session_state:
    st.session_state.client_session = uuid.uuid4().hex
if "results" not in st.session_state:
    st.session_state.results = {}

bucket = session_bucket(st.session_state.client_session)

st.title("Image Captioning")
st.write("Upload a photograph or a ZIP of images to generate captions.")
st.caption("Runs on CPU. Bulk images are processed one at a time.")

label = st.radio("Upload mode", ["Single image", "Bulk ZIP"], horizontal=True)
mode = "single" if label == "Single image" else "bulk"

if mode == "single":
    st.caption("JPEG, PNG, WebP, or AVIF · Maximum 10 MiB and 16 megapixels.")
else:
    st.caption(
        "Maximum 30 images · ZIP up to 50 MiB · Expanded size up to 100 MiB. "
        "Files with unsupported extensions are skipped."
    )

upload = st.file_uploader(
    "Choose an image" if mode == "single" else "Choose a ZIP",
    type=["jpg", "jpeg", "png", "webp", "avif"] if mode == "single" else ["zip"],
    key=f"upload_{mode}",
)

if st.button("Generate captions", type="primary", disabled=upload is None):
    st.session_state.results[mode] = []
    st.session_state.results[mode] = run_job(upload, mode, bucket)

results = st.session_state.results.get(mode, [])

if results:
    succeeded = sum(row["status"] == "success" for row in results)
    left, right = st.columns(2)
    left.metric("Successful images", succeeded)
    right.metric("Failed images", len(results) - succeeded)

    st.dataframe(results, hide_index=True, width="stretch")

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=list(results[0]))
    writer.writeheader()
    writer.writerows(results)

    st.download_button(
        "Download results CSV",
        data=output.getvalue(),
        file_name="captions.csv",
        mime="text/csv",
        key=f"download_{mode}",
    )
