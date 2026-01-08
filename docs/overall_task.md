# Task

In this exercise, you'll design and implement a web application that allows users to upload a passport and G-28 form (in PDF or image format). The application should automatically extract relevant data from these uploaded documents and use that information to populate a provided web form. Here is the test form:

https://mendrika-alma.github.io/form-submission/

This task simulates a real-world document automation process that reduces manual data entry effort.

## Requirements

### File Upload Interface:

Build a simple interface (e.g., using Flask, FastAPI, a lightweight React front-end, etc) that allows uploading of passport and G-28 documents (example below).

- Supported formats: PDF and image (JPEG/PNG).

### Data Extraction:

Implement logic to extract structured data (e.g., full name, date of birth, country, address, attorney name, firm, etc.) using one or a combination of:

- MRZ extraction
- OCR
- LLM-based solutions

### Form Population:

Use browser automation (e.g., Playwright, Puppeteer, Selenium, or an LLM agent) to:

- Navigate to the provided form URL
- Accurately fill in the fields with extracted data
- Do not submit or digitally sign the form

### Robustness:

The system should tolerate minor variations in document formatting or field labeling without requiring code changes. It should handle missing data and passports from various countries.

## Deliverables

- A local web interface (Flask/FastAPI or similar) that runs with minimal setup and allows for document upload, extraction, and form population testing.
- Working source code, ideally in a public GitHub repository, with clear setup instructions (please provide access to shuo@tryalma.ai and alex@tryalma.ai when submitting).
- A short screen recording (e.g., Loom) showing the workflow from upload to automated form population.

Time estimate: 3–5 hours.
