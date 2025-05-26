import argparse


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mistral-ocr",
        description="Submit OCR batches to the Mistral API"
    )
    
    args = parser.parse_args()


if __name__ == "__main__":
    main()
