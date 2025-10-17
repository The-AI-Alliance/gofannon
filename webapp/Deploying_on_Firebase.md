# Deploying to Firebase

This guide provides step-by-step instructions for deploying the Gofannon web application to a Firebase project. This includes deploying the React frontend to Firebase Hosting and the Python backend to Cloud Functions.

## Prerequisites

Before you begin, ensure you have the following installed and configured:

1.  **Google Cloud & Firebase Account**:
    *   A Google account.
    *   A Firebase project created on the [Firebase Console](https://console.firebase.google.com/).
    *   Your Firebase project must be on the **Blaze (Pay-as-you-go)** plan to use Cloud Functions.

2.  **Local Development Tools**:
    *   [Node.js](https://nodejs.org/) (v18+)
    *   [pnpm](https://pnpm.io/installation) (v8+)
    *   [Python](https://www.python.org/downloads/) (v3.10+)

3.  **Command-Line Tools**:
    *   **Firebase CLI**: Install it globally.
        ```bash
        npm install -g firebase-tools
        ```
    *   **Google Cloud CLI**: Follow the instructions to [install the gcloud CLI](https://cloud.google.com/sdk/docs/install).

## 1. One-Time Project Setup

These steps only need to be done once per Firebase project.

### 1.1. Log in and Link Project

First, authenticate the CLIs with your Google account and link your local repository to your Firebase project.

1.  **Log in to Firebase:**
    ```bash
    firebase login
    ```

2.  **Log in to Google Cloud:**
    ```bash
    gcloud auth login
    ```

3.  **Link your Firebase Project:**
    Run the following command in the `infra/firebase` root directory. Select your Firebase project from the list when prompted.
    ```bash
    firebase use --add
    ```
    This will create a `.firebaserc` file.

### 1.2. Enable Google Cloud APIs

The Python backend requires several Google Cloud services. Enable them for your project:

```bash
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  cloudfunctions.googleapis.com \
  artifactregistry.googleapis.com \
  iam.googleapis.com \
  firestore.googleapis.com \
  storage.googleapis.com
```

### 1.3. Configure Firebase Services

1.  **Authentication**:
    *   Go to your Firebase project in the console.
    *   Navigate to **Authentication** -> **Sign-in method**.
    *   Enable the **Email/Password** provider.
    *   Enable the **Google** provider, provide a project support email when prompted.

2.  **Firestore Database**:
    *   Navigate to **Firestore Database**.
    *   Click **Create database**.
    *   Choose default options.
    *   Select a location (e.g., `nam5`).
    *   Click **Create**. The provided `firestore.rules` will secure it on deployment.

3.  **Storage**:
    *   Navigate to **Storage**.
    *   Click **Get started** and follow the prompts to create a default storage bucket. The `storage.rules` will be applied on deployment.

## 2. Environment Configuration

The Python API (Cloud Function) requires environment variables for API keys.

1.  **Create an Environment File**:
    In the `webapp/infra/firebase` directory, create a file named `.env`. This file will store your secrets. **Do not commit this file to Git.**

    ```ini
    # webapp/infra/firebase/.env

    
    OPENAI_API_KEY="sk-..."
    GEMINI_API_KEY="..."

    ANTHROPIC_API_KEY="..."
    ```

2.  **Set the Google Cloud Project**:
    Ensure your `gcloud` CLI is pointing to the correct project.
    ```bash
    gcloud config set project YOUR_FIREBASE_PROJECT_ID
    ```

3. **Create the Cloud Functions Virtual Environment**:
    To create the virtual environment:
    ```bash
    cd packages/api/user-service
    python3.11 -m venv venv
    ```

    Then activate it and install relevant packages:
    ```bash
    source venv/bin/activate
    pip install -r requirements.txt
    ```

4. **Configure `.env` files**:

    Copy `webapp/packages/webui/.env.firebase.example` to `.env`
    - In `.env`, fill in the blank values. To get these values, you must first create a new Firebase app under the existing Firebase project:
      - `firebase apps:create web <web app name> --project <project id>`
    - Get the value for the new app by executing
      - `firebase apps:sdkconfig web <app id returned in the previous step>`
      
    In `webapp/packages/api/user-service/.env` set
    - `FRONTEND_URL` to `https://<your-project-id>.web.app`
    - `DATABASE_PROVIDER` to `firestore`
    - `APP_ENV` to `firebase`
    
## 3. Manual Deployment

To deploy the application manually from your local machine:

1.  **Install All Dependencies**:
    From the `webapp` root directory, run:
    ```bash
    pnpm install
    ```

2.  **Build the Web App**:
    This command bundles the React frontend for production.
    ```bash
    pnpm --filter webui build
    ```

3.  **Deploy to Firebase**:
    This single command deploys Firebase Hosting (your web app), Cloud Functions (your API), and all security rules.
    ```bash
    firebase deploy
    ```

    The deployment process will:
    *   Read the `.env.firebase` file and set the environment variables for the Python Cloud Function.
    *   Deploy the built React app from `packages/webui/dist` to Firebase Hosting.
    *   Deploy the Python API from the `functions` directory to Cloud Functions.
    *   Apply the security rules in `firestore.rules` and `storage.rules`.

After deployment, the command will output the URL for your live web application.

## 4. CI/CD with GitHub Actions

A workflow is included to automate deployment when you push to the `main` branch.

### 4.1. GitHub Secrets Setup

1.  **Create a Google Cloud Service Account**:
    *   Go to the [Service Accounts page](https://console.cloud.google.com/iam-admin/serviceaccounts) in your Google Cloud project.
    *   Click **Create Service Account**.
    *   Give it a name (e.g., `github-actions-deployer`).
    *   Grant it the following roles:
        *   `Firebase Admin`
        *   `Cloud Functions Admin`
        *   `Service Account User`
        *   `Storage Admin`
    *   Click **Done**.

2.  **Generate a Service Account Key**:
    *   Find your new service account in the list, click the three-dot menu, and select **Manage keys**.
    *   Click **Add Key** -> **Create new key**.
    *   Choose **JSON** and click **Create**. A JSON key file will be downloaded.

3.  **Add Secrets to your GitHub Repository**:
    *   In your GitHub repository, go to **Settings** > **Secrets and variables** > **Actions**.
    *   Create the following repository secrets:
        *   `GCP_SA_KEY`: Copy the entire content of the downloaded JSON key file and paste it here.
        *   `FIREBASE_PROJECT_ID`: Your Firebase Project ID.
        *   `OPENAI_API_KEY`: Your OpenAI API key.
        *   `GEMINI_API_KEY`: Your Gemini API key.

### 4.2. Triggering the Workflow

The workflow at `.github/workflows/deploy-firebase.yml` is configured to run automatically on every push to the `main` branch. You can also trigger it manually from the **Actions** tab in your GitHub repository.