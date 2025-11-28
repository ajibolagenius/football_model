# Football Predictive Model - Data Pipeline

## Project Overview

This project implements an Extract, Transform, Load (ETL) pipeline designed to collect football (soccer) data from an external API, process it, and store it in a PostgreSQL database. The ultimate goal is to build a robust dataset that can be used for developing predictive models for football match outcomes. This README provides instructions on how to set up and run the data pipeline.

## 1. Get Your API Key

To access the necessary football data, you need an API key from RapidAPI.

-   **Step 1: Navigate to RapidAPI - API-Football.**
    Open your web browser and go to [https://rapidapi.com/api-sports/api/api-football](https://rapidapi.com/api-sports/api/api-football). This is the primary data source for our pipeline.

-   **Step 2: Sign Up for a RapidAPI Account.**
    If you don't already have one, create a new account. The sign-up process is free.

-   **Step 3: Subscribe to the Basic (Free) Plan.**
    Once logged in, find the pricing plans for the API-Football service and subscribe to the "Basic" plan. This plan typically offers a sufficient number of requests for development and testing purposes without incurring costs.

-   **Step 4: Copy Your `X-RapidAPI-Key`.**
    After subscribing, your unique API key will be displayed on the API-Football dashboard. Locate and copy the `X-RapidAPI-Key`. This key is essential for authenticating your requests to the API.

-   **Step 5: Paste the API Key into `etl_pipeline.py`.**
    Open the `etl_pipeline.py` file in your preferred code editor. Locate line 16 (or the designated placeholder for the API key) and paste your copied `X-RapidAPI-Key` there. Ensure it is correctly formatted, typically as a string variable.

## 2. Prepare the Database

This pipeline utilizes PostgreSQL for data storage. Follow these steps to set up your database.

-   **Step 1: Ensure PostgreSQL is Running.**
    Before proceeding, ensure your PostgreSQL server is actively running. The method to start or check its status varies depending on your operating system and how PostgreSQL was installed.

    -   **macOS (Homebrew):**
        ```bash
        brew services start postgresql@14
        ```
        (Note: Replace `postgresql@14` with your installed version if different, e.g., `postgresql@15`).

    -   **Linux (systemd-based distributions like Ubuntu/Debian, Fedora, CentOS):**
        ```bash
        sudo systemctl start postgresql
        # Or check status:
        # sudo systemctl status postgresql
        ```
        (Note: Service name might vary, e.g., `postgresql-14`).

    -   **Windows:**
        PostgreSQL is often installed as a service and starts automatically. You can verify its status or start it manually via the "Services" application (search for "Services" in the Start menu). Look for a service named "postgresql-x64-14" or similar.

    For other installation methods or operating systems, please consult your PostgreSQL documentation.

-   **Step 2: Create the Database.**
    Open your terminal or command prompt and create a new database named `football_prediction_db`. This database will house all the tables and data collected by the ETL pipeline. Ensure that the PostgreSQL client tools (like `createdb` and `psql`) are accessible in your system's PATH.

    ```bash
    createdb football_prediction_db
    ```

-   **Step 3: Run the Schema Script.**
    Execute the `schema.sql` file against the newly created database. This script contains the SQL commands to define the necessary tables and their structures.

    ```bash
    psql -d football_prediction_db -f schema.sql
    ```
    This command connects to `football_prediction_db` and executes the SQL statements from `schema.sql`, setting up your database schema.

## 3. Run the Pipeline

Once the API key is configured and the database is prepared, you can execute the ETL pipeline.

-   **Step 1: Execute the Python Script.**
    Navigate to the project's root directory in your terminal or command prompt and run the `etl_pipeline.py` script using Python 3.

    ```bash
    python3 etl_pipeline.py
    ```
    The script will connect to the API, fetch data, process it, and load it into your `football_prediction_db` database. Monitor the terminal output for any logs or error messages.

## Challenges and Future Work

### Name Matching Discrepancies

One of the significant challenges in integrating sports data from various sources is the inconsistency in naming conventions. For instance, an API might refer to a team as "Manchester United," while a scraping site uses "Man Utd."

-   **Current Solution:** The current version of the script relies on exact string matching for team and player names. This means that any slight variation will prevent a successful match, potentially leading to incomplete or mismatched data.

-   **Future Upgrade:** To address this, we plan to implement a fuzzy string matching logic, likely using libraries such as `fuzzywuzzy`. This will allow the pipeline to identify and reconcile similar but not identical names, significantly improving data accuracy and completeness. This upgrade will involve developing a robust matching algorithm and potentially a manual review process for highly ambiguous cases.