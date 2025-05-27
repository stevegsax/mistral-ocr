#!/usr/bin/env python
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "httpx",
#   "mistralai"
# ]
# ///

import argparse
import base64
import json
import os
import sys
from glob import glob

import httpx
from mistralai import Mistral


def get_api_key(api_key=None):
    """Get API key from parameter or environment variable."""
    if api_key is None:
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("No API key provided. Set MISTRAL_API_KEY environment variable.")
    return api_key


def encode_image_to_data_url(image_path):
    """Convert image file to base64 data URL."""
    try:
        with open(image_path, "rb") as f:
            image_data = f.read()
        encoded = base64.b64encode(image_data).decode("utf-8")
        return f"data:image/jpeg;base64,{encoded}"
    except Exception as e:
        print(f"Error encoding {image_path}: {e}")
        return None


def create_batch_file(image_paths, output_file):
    """Create JSONL batch file for OCR processing."""
    with open(output_file, "w") as f:
        for i, path in enumerate(image_paths):
            data_url = encode_image_to_data_url(path)
            if data_url:
                entry = {
                    "custom_id": str(i),
                    "body": {
                        "document": {"type": "image_url", "image_url": data_url},
                        "include_image_base64": True,
                    },
                }
                f.write(json.dumps(entry) + "\n")


def submit_batch_job(image_paths, batch_file="batch_file.jsonl", model="mistral-ocr-latest"):
    """Submit batch OCR job and return job ID."""
    api_key = get_api_key()
    client = Mistral(api_key=api_key)

    print(f"Processing {len(image_paths)} images...")
    create_batch_file(image_paths, batch_file)

    print("Uploading batch file...")
    with open(batch_file, "rb") as f:
        batch_data = client.files.upload(
            file={"file_name": batch_file, "content": f}, purpose="batch"
        )

    print("Creating batch job...")
    job = client.batch.jobs.create(
        input_files=[batch_data.id],
        model=model,
        endpoint="/v1/ocr",
        metadata={"job_type": "ocr_batch"},
    )

    print(f"Job created: {job.id}")
    return job.id


def download_results(job_id, output_file=None):
    """Download results from completed batch job."""
    api_key = get_api_key()
    client = Mistral(api_key=api_key)

    print(f"Checking job {job_id}...")
    job = client.batch.jobs.get(job_id=job_id)

    print(f"Status: {job.status}")
    print(f"Progress: {job.succeeded_requests + job.failed_requests}/{job.total_requests}")

    if job.status != "SUCCESS":
        if job.status in ["QUEUED", "IN_PROGRESS", "VALIDATING"]:
            print("Job not complete. Please wait and try again.")
        else:
            print(f"Job failed with status: {job.status}")
        sys.exit(1)

    if not job.output_file:
        print("No output file available")
        sys.exit(1)

    if not output_file:
        created_at = str(job.created_at).replace(":", "-").replace(" ", "_")
        output_file = f"results_{created_at}.jsonl"

    print("Downloading results...")
    output_stream = client.files.download(file_id=job.output_file)

    with open(output_file, "wb") as f:
        f.write(output_stream.read())

    print(f"Results saved to {output_file}")


def check_status(job_id):
    """Check job status via HTTP request."""
    api_key = get_api_key()
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    response = httpx.get(f"https://api.mistral.ai/v1/batch/jobs/{job_id}", headers=headers)
    print(json.dumps(response.json()))


def list_jobs():
    """List all batch jobs."""
    api_key = get_api_key()
    client = Mistral(api_key=api_key)

    try:
        jobs = client.batch.jobs.list()
        jobs_data = []

        for job in jobs.data:
            job_dict = {
                "id": job.id,
                "status": job.status,
                "model": job.model,
                "created_at": job.created_at,
                "total_requests": job.total_requests,
                "succeeded_requests": job.succeeded_requests,
                "failed_requests": job.failed_requests,
            }

            if hasattr(job, "metadata") and job.metadata:
                job_dict["metadata"] = job.metadata

            jobs_data.append(job_dict)

        print(json.dumps(jobs_data, indent=2))

    except Exception as e:
        print(json.dumps({"error": str(e)}, indent=2))


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Mistral OCR batch processing")
    parser.add_argument("--input", "-i", help="Input file pattern (e.g., 'images/*.jpg')")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--batch-file", "-b", default="batch_file.jsonl", help="Batch file path")
    parser.add_argument("--model", "-m", default="mistral-ocr-latest", help="OCR model")
    parser.add_argument("--list", "-l", action="store_true", help="List batch jobs")
    parser.add_argument("--download", "-d", help="Download results by job ID")
    parser.add_argument("--status", "-s", help="Check job status by ID")

    args = parser.parse_args()

    try:
        if args.list:
            list_jobs()
        elif args.download:
            download_results(args.download, args.output)
        elif args.status:
            check_status(args.status)
        elif args.input:
            image_files = sorted(glob(args.input))
            if not image_files:
                print(f"No files found: {args.input}")
                sys.exit(1)

            job_id = submit_batch_job(image_files, args.batch_file, args.model)
            print(f"\nTo check status: python {__file__} --status {job_id}")
            print(f"To download: python {__file__} --download {job_id}")
        else:
            parser.error("Specify --input, --list, --download, or --status")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
