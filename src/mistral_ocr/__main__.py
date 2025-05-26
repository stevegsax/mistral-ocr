import argparse
import pathlib
import os


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mistral-ocr",
        description="Submit OCR batches to the Mistral API"
    )
    
    parser.add_argument(
        "--submit",
        type=str,
        help="Submit a file or directory for OCR processing"
    )
    
    args = parser.parse_args()
    
    if args.submit:
        # Import here to avoid circular imports
        from mistral_ocr.client import MistralOCRClient
        
        # Get API key from environment variable
        api_key = os.environ.get("MISTRAL_API_KEY", "test")
        client = MistralOCRClient(api_key=api_key)
        
        # Submit the file/directory
        file_path = pathlib.Path(args.submit)
        job_id = client.submit_documents([file_path])
        print(f"Submitted job: {job_id}")


if __name__ == "__main__":
    main()
