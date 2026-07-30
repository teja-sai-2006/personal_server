# How the Personal Server Works (System Architecture)

This document explains the internal mechanisms, data flow, and cryptographic architecture of the Personal Server.

## 1. System Topology
The application relies on four primary components running concurrently:
- **Caddy (Reverse Proxy):** Listens on port `8081`. It serves the static frontend HTML/JS/CSS files and routes all `/api/*` traffic to the FastAPI backend.
- **FastAPI (Backend):** Listens on port `8000`. Handles user authentication, database operations, and encryption routing.
- **Vaultwarden (Docker):** Listens on port `8001`. A lightweight Rust implementation of the Bitwarden API, handling password vault functionality.
- **Ollama (AI Daemon):** Runs locally on port `11434` to serve AI models for image tagging and smart search without relying on the cloud.

### Request Flow
1. User accesses `http://localhost:8081`.
2. Caddy serves `index.html`.
3. Frontend Javascript makes an asynchronous request to `http://localhost:8081/api/...`.
4. Caddy reverse-proxies this request to FastAPI on port `8000`.
5. FastAPI reads/writes to `personal_server.db` (SQLite) and returns a JSON response.

---

## 2. Zero-Knowledge Cryptography
To ensure that the server administrator cannot read users' private photos or files, the application uses a multi-tiered **Zero-Knowledge Encryption** strategy.

### The Key Hierarchy
- **Master Password:** Known only to the user. Never transmitted to the server in plaintext.
- **User Master Key (UMK):** A 32-byte secure random key generated during registration. This key encrypts all of the user's files.
- **Encrypted Master Key (EMK):** The UMK is encrypted using the user's Master Password (via Argon2 key derivation and AES-GCM). The EMK is stored in the database.

### The Registration Flow
1. An admin creates an invite link (e.g., `provision.py <username>`).
2. The user clicks the link and types their new Master Password in the browser.
3. The server generates a random 32-byte UMK.
4. The server encrypts the UMK with the Master Password to create the EMK.
5. The unencrypted UMK is discarded from memory. The EMK is saved in the database.

### The Login & Decryption Flow
1. The user logs in with their username and Master Password.
2. The server authenticates the password hash.
3. The server derives the decryption key from the provided password using Argon2.
4. The server decrypts the EMK to retrieve the UMK in memory for the duration of the session.
5. All file uploads/downloads during the session are encrypted/decrypted on-the-fly using the UMK.

---

## 3. True Data Recovery (TDR)
If a user forgets their Master Password, they would typically lose all data in a Zero-Knowledge system because the UMK cannot be decrypted. The Personal Server solves this using a **True Data Recovery** code.

### How it Works
1. During registration, the server generates a secondary, highly secure random 32-character string (The Recovery Code).
2. The server takes the original UMK and encrypts it a *second time* using the Recovery Code instead of the password.
3. This creates a Recovery Encrypted Master Key (`remk`), which is stored in the database alongside the standard `emk`.
4. The server only stores a SHA-256 hash of the Recovery Code in the database. It displays the plaintext code to the user exactly once.

### The Recovery Process
1. The user clicks "Forgot Password" and enters their Username, Recovery Code, and a New Password.
2. The server hashes the provided code and verifies it against the database.
3. If valid, the server uses the Recovery Code to decrypt the `remk` and retrieve the UMK.
4. The server then re-encrypts the UMK using the New Password (creating a new `emk`).
5. A brand new Recovery Code and `remk` are generated to rotate the keys.
6. The user regains full access to their data seamlessly.

---

## 4. Secure File Sharing (EFKs)
When a user shares a file with another family member or creates a temporary public link, the server uses **Ephemeral Folder Keys (EFKs)**.
- Instead of decrypting the file and storing it in plaintext, the server creates a unique, temporary symmetric key (the EFK).
- The file is re-encrypted using the EFK for the specific duration of the share.
- When the share expires, the EFK is deleted from the database, permanently destroying access to that specific share instance without affecting the original encrypted file.

---

## 5. Process Management

The application is bundled with two main scripts (`start.sh` and `stop.sh`) to ensure a smooth, containerized experience without leaving background processes orphaned on your host machine.

### Startup Execution
When you run `./start.sh`, the script:
1. **Verifies Dependencies:** Checks for Ollama, Caddy, and Docker.
2. **Boots Local Services:** Spawns Ollama and Caddy in the background as separate jobs.
3. **Boots Docker:** Attempts to stop and remove any stale `vaultwarden-local` containers, then spins up a fresh instance binding to port `8001`.
4. **Activates Python:** Sources the `venv` and runs the FastAPI `uvicorn` server on port `8000`.
5. **Foreground Wait:** The bash script then calls `wait`, keeping all background jobs attached to the active terminal.

### Graceful Teardown
When you press `Ctrl+C` during execution, the terminal sends a `SIGINT` interrupt. The `start.sh` script catches this using a bash `trap` and executes `bash stop.sh`. 
The `stop.sh` script works completely independently to ensure absolute shutdown:
1. It uses `pkill -f` to aggressively hunt down any running `caddy`, `ollama`, `llama-server`, or `uvicorn` processes.
2. It uses `docker rm -f` to forcefully terminate the Vaultwarden containers.
This robust teardown guarantees that network ports (8081, 8000, 11434, 8001) are perfectly freed up for your next session.

---

## 6. Cloud Backups (Rclone)

To mitigate the risk of local hardware failure, the system integrates with Rclone to securely mirror the server's state to Google Drive.

### What Gets Backed Up?
The entirety of the `data/` directory is synced. This includes:
- `data/db/personal_server.db`: The SQLite database containing user accounts, encrypted master keys (`emk`), and file metadata.
- `data/media/`: The locally encrypted ciphertexts of all user-uploaded photos and files.
- `data/db/vaultwarden/`: The Docker-mounted volume containing all of the family's encrypted password vaults.

### Security Guarantees
Because of the Zero-Knowledge Architecture (Section 2), the data pushed to Google Drive is **useless to Google or anyone who intercepts it**. The SQLite database only contains keys that are encrypted by the user's Master Password, and the media files are completely ciphered. Without the user physically typing their Master Password into the frontend, the cloud backup is mathematically inaccessible.
