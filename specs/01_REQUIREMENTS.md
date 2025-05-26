# mistral-ocr Product Requirements Document

> This document describes the product requirements for `mistral-ocr`, which allows me to submit files to the Mistral OCR service, check the status of jobs, and retrieve results. The Mistral OCR service will convert documents from image formats (PNG, JPG, PDF, etc) to markdown text. The Mistral OCR service will extract non-text images and return them along with the extracted text.

## Personas

- **Document Manager** is responsible for managing the organization's documents
- **Finance Officer** is responsible for corporate spending

## 1. File Submission & Processing

### 1.1 - Submit Image Files

Story:

As a Document Manager, I want to submit image files (PNG, JPG, PDF, etc.) to the OCR service so that text and non-text images can be extracted and returned.

Acceptance Criteria:

- The system accepts fully qualified file paths.
- The API processes each image as a single page.
- Files not meeting OCR criteria are handled through the underlying Mistral API's validation.

### 1.2 - Submit Directory for Conversion

Story:

As a Document Manager, I want to submit an entire directory for conversion so that I do not have to specify each file individually.

Acceptance Criteria:

- The system allows the user to choose whether to process only top-level files or to recursively traverse subdirectories.
- Hidden files/directories (names beginning with ".") are automatically ignored.
- There are no additional restrictions on file types beyond what the API accepts.

## 2. Batch Processing & Aggregation

### 2.1 - Automatic Batch Partitioning

Story:

As a Document Manager, I want the system to automatically partition a submission into multiple batches if the number of files exceeds 100-since the Mistral API supports only 100 files per request-so that each batch is processed correctly.

Acceptance Criteria:

- The system automatically splits files into batches when the 100 file limit is exceeded.
- Each batch is tracked individually while allowing the user to view an aggregated status via a document name query.

### 2.2 - Query Conversion Job Status

Story:

As a Document Manager, I want the ability to query the status of conversion jobs either by document name or by batch ID so that I can monitor processing progress in detail.

Acceptance Criteria:

- When querying by document name, the system lists all related batches along with their individual statuses using the Mistral API status endpoints (e.g., via client.batch.jobs.list).

## 3. Job Cancellation

Story:

As a Document Manager, I want the ability to cancel an ongoing conversion request so that I can stop processing if needed.

Acceptance Criteria:

- Upon cancellation initiation, the system calls the Mistral API cancel method (for example, `canceled_job = client.batch.jobs.cancel(job_id=created_job.id)`) and immediately returns the status of that call.
- The system does not wait for the cancellation to fully propagate but notifies the user that the cancel request has been received.

## 4. Document Naming & Association

Story:

As a Document Manager, I want to assign a custom document name to a collection of image files so that related pages can be grouped into a single coherent document.

Acceptance Criteria:

- The document name is supplied at the time of submission and is stored along with an automatically generated UUID.
- When submitting pages, the user can choose to (a) append to the most recently added document with that name, (b) append to a document by specifying its UUID, or (c) create a new document record by default (if no UUID is provided).
- The system does not enforce uniqueness on the document name itself.

## 5. Error Handling & Logging

Story:

As a Document Manager, I want to receive detailed error messages if a conversion fails (e.g., due to unrecognizable or corrupted files) so that I know why an error occurred.

Acceptance Criteria:

- The system captures error details from the JSON response provided by the Mistral API, including error text.
- Error messages are both displayed on the screen and logged to a file for further investigation.

## 6. Automation of Downloading Results

Story:

As a Document Manager, I want the system to automatically download output files once processing is finished so that I have a local copy of the converted documents.

Acceptance Criteria:

- The destination directory is derived from the `XDG_DATA_HOME` environment variable with a subdirectory named after the document (converted to lowercase with all whitespace replaced by a hyphen).
- If a page is not associated with any document, the result is stored in a subdirectory named "unknown".
- If the job or document is still processing, the system informs the user that downloads cannot proceed until processing is complete.
- The user can later trigger a re-download in case of network or transient errors.

## 7. Cost Management (Finance Officer)

Story:

As a Finance Officer, I want the application to leverage the Mistral batch API in order to reduce overall costs so that the organization can benefit from cost-effective document processing.

Acceptance Criteria:

- The system utilizes batch processing as prescribed by the Mistral API, grouping up to 100 files in one request.
- There is no requirement for a detailed reporting interface; the focus is solely on ensuring batch processing is employed to minimize per-request costs.

## Non-Functional Requirements

Story:

As a Document Manager, I want each image to be processed as a single page, submissions exceeding 100 files to be automatically partitioned into multiple batches, and detailed information about batches, documents, and pages to be stored locally using an SQLite3 database with standard XDG directories for configuration, data, and cache storage. Additionally, I need the system to handle document naming with non-unique names by using an automatically generated UUID, allowing pages to be appended to the most recently added document with the same name, appended by a specified UUID, or creating a new document record by default. No realtime feedback is required. The user will check for status on demand.

Acceptance Criteria:

- Each submitted image is treated as one page of a document.
- If a submission exceeds 100 files, the system automatically splits the files into multiple batches.
- A local SQLite3 database stores information about batches, documents, and pages.
- Standard XDG directories are used for configuration, data, and cache storage.
- Document names are not enforced to be unique; filenames may be repeated. A unique identifier is generated automatically (UUID).
- When submitting pages associated with a document name:
  - The system can append pages to the most recently added document with that name.
  - The system can append pages to a document by specifying its UUID.
  - If no UUID is provided, the system creates a new document record by default.
- The system should provide command line arguments that allow the user to change behavior.


## Reference

### The Mistral OCR API

Documentation about the Mistral batch API can be found on the [Batch Inference](https://docs.mistral.ai/capabilities/batch/) page.
The Mistral API client for Python is available on GitHub in this repository: [client-python](https://github.com/mistralai/client-python).

### The XDG Base Directory Specification

Detailed information about the XDG Base Directory Specification can be found at [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/latest/).

# END OF SPECIFICATION

THIS IS THE END OF THE PRODUCT REQUIREMENT SPECIFICATION. EVERYTHING AFTER THIS LINE IS CONVERSATION TO REFINE THE REQUIREMETS ABOVE


###








<!-- Local Variables: -->
<!-- gptel-model: o3-mini -->
<!-- gptel--backend-name: "ChatGPT" -->
<!-- gptel--system-message: "You are an expert product manager. Your task is to assist in the creation and revision of product requirements. You are polite and professional. Write functional requirements in the form of User Stories." -->
<!-- gptel--bounds: ((response (6925 7017))) -->
<!-- End: -->
