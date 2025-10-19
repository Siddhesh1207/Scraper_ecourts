# New Delhi District Court Cause List Scraper

This project is a Python-based web application with a Streamlit UI designed to fetch and download cause lists from the New Delhi District Court website. It automates the entire process of form filling and data extraction, generating clean, multi-column PDF reports that include case numbers and advocate names.

[cite_start]While the initial task PDF mentioned the national eCourts portal[cite: 6], this project focuses on the specific New Delhi District Court site as per subsequent instructions. A key finding during development was the website's use of a one-time-use CAPTCHA for every request. This security feature makes fully automated batch processing impossible. Therefore, the application was intelligently designed as a powerful "Batch Helper" to provide the most efficient workflow possible within these constraints.

## Features

-   [cite_start]**Interactive Web Interface:** Built with Streamlit for a user-friendly experience, fulfilling the bonus requirement for a web interface. [cite: 18]
-   **Real-Time Data Fetching:** Dynamically fetches the latest list of Court Complexes and individual Courts directly from the server—no stored data is used.
-   **Single Court PDF Generation:** Allows users to download a formatted PDF cause list for any specific judge by selecting from the dropdowns.
-   **Intelligent Batch Processing:** A "Batch Helper" mode that queues all courts in a selected complex. The user can efficiently process the entire list by simply solving the new CAPTCHA for each court, while the script handles all other repetitive tasks.
-   **Formatted PDF Output:** Generates clean, readable PDF files that include columns for Serial Number, Case Details, and Advocate Name.

## Setup and Installation

Follow these steps to set up and run the project locally.

### Prerequisites

-   Python 3.8 or higher
-   Git

### Installation Steps

1.  **Clone the repository:**
    ```bash
    git clone <your-github-repository-url>
    cd <repository-folder-name>
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install the required dependencies:**
    A `requirements.txt` file should be included. Install it using pip.
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: If a `requirements.txt` file is not present, create one with `pip freeze > requirements.txt` after installing the necessary packages: `streamlit`, `selenium`, `undetected-chromedriver`, `reportlab`, `beautifulsoup4`, `requests`)*

## How to Use

1.  **Run the Streamlit application:**
    Open your terminal in the project directory and run the following command:
    ```bash
    streamlit run main.py
    ```
    This will open the web interface in your browser.

2.  **Using the Interface:**
    -   **Court Selection:** Choose to search by "Court Complex" and select the desired complex from the dropdown. The list of specific courts will load automatically.
    -   **Details & CAPTCHA:** Select the cause list date and case type. A CAPTCHA image will be displayed. Enter the characters from the image into the input box.
    -   **For a Single Download:** Select a specific court from the second dropdown and click the **"Generate PDF for Selected Court"** button.
    -   **For Batch Downloads:**
        1.  Click **"Start New Batch for All Courts in Complex"**. This will queue up all courts.
        2.  The UI will show you which court is next.
        3.  Enter the CAPTCHA for the current request.
        4.  Click **"Process Next Court"**.
        5.  The script will download the PDF, and the page will refresh, showing you the *new* CAPTCHA for the *next* court in the queue.
        6.  Repeat the process of entering the CAPTCHA and clicking "Process Next Court" until the batch is complete.

## Project Structure

```
.
├── core.py             # Main logic for Selenium, scraping, and PDF generation
├── main.py             # Streamlit UI and application flow
├── output/             # Directory where generated PDFs are saved
├── requirements.txt    # Project dependencies
└── README.md           # This file
```

## Technical Finding: CAPTCHA Handling

A significant challenge identified was the website's security mechanism. It employs a **one-time-use CAPTCHA** that is invalidated immediately after a single form submission.

This makes a fully automated, one-click "Download All" feature technically impossible, as the script cannot programmatically solve the new CAPTCHA required for each subsequent court.

The "Batch Helper" workflow was implemented as the most effective and robust solution. It maximizes automation by handling all data entry and processing, leaving only the non-automatable CAPTCHA-solving step to the user, thus fulfilling the spirit of the project requirements within the website's technical constraints.
