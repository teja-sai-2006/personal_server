# Personal Server

Welcome to your Personal Server! This is a highly secure, zero-knowledge, self-hosted web application for families. It lets you store your passwords, photos, and files locally on your own machine, with offline AI capabilities built right in.

This guide will show you exactly how to use the server and its scripts. If you want to know how the code works under the hood (encryption, architecture, etc.), check out `WORKING.md`.

---

## 1. Setting Up (First Time Only)

Before you do anything, ensure you have Python 3, Docker, Caddy, and Ollama installed (check `requirements-user.txt`).

To prepare your server, run the setup script:
```bash
./setup.sh
```
**What happens when you run this?** It automatically creates an isolated Python virtual environment (`venv`) and installs all the required backend libraries (like FastAPI and SQLAlchemy) so they don't interfere with your computer's global packages.

---

## 2. Starting and Stopping the Server

### Start the Server
```bash
./start.sh
```
**What happens when you run this?** The script automatically launches four things in the background:
1. **Ollama:** Starts the local AI engine.
2. **Vaultwarden:** Boots up a Docker container to manage your passwords.
3. **Caddy:** Starts the reverse proxy to serve the website securely.
4. **FastAPI:** Starts the backend server that handles your data.

Once it says "SYSTEM IS RUNNING", you can access your server in two ways:
1. **Locally:** Open your web browser and go to `http://localhost:8081`
2. **Remotely (Anywhere in the world):** Using a mesh VPN like [Tailscale](https://tailscale.com), connect your phone or laptop to your Tailscale network and go to `http://<your-tailscale-ip>:8081`!

### Stop the Server
When you are done, go to the terminal running the server and press `Ctrl+C`. The system will automatically catch this and gracefully shut everything down.
If you ever need to forcefully stop the server manually, just run:
```bash
./stop.sh
```
**What happens when you run this?** It forcefully searches for and kills any lingering Caddy, Ollama, Uvicorn, or Vaultwarden processes to ensure your computer's network ports are completely freed up.

---

## 3. Creating User Accounts

Because this is a private family server, there is no public "Sign Up" button on the website. As the admin, you must create accounts for your family members.

```bash
./create_user.sh
```
**What happens when you run this?** The script will ask you for a username. It will then generate the cryptographic foundations for that user and give you a special **Recovery Code**. 

Give the username to your family member. When they log in for the first time, they will set their Master Password. **Make sure they save their Recovery Code!** Because the server uses Zero-Knowledge encryption, if they forget their password, that code is the *only* way to recover their photos and passwords.

---

## 4. Using the Web App

Once you navigate to `http://localhost:8081` and log in, you will see a clean dashboard. 

- **Media Upload:** Click the "Upload" button to encrypt and store photos on your local hard drive. 
- **AI Chat:** Navigate to the AI tab to chat completely offline with the local Ollama model.
- **Vaultwarden:** Use the built-in password manager to securely store and share passwords with your family.

---

## 5. Cloud Backups (Google Drive)

Your data is stored locally in the `data/` folder. To ensure you never lose it if your computer breaks, you can back it up to Google Drive using Rclone.

1. **Connect your Google Drive:**
   ```bash
   ./rclone_setup.sh
   ```
   *This installs Rclone and opens a browser window for you to log in to Google and authorize the app.*

2. **Run a Backup:**
   ```bash
   ./rclone_backup.sh
   ```
   *This securely uploads your encrypted database, photos, and password vaults to a folder named `personal_server_database_backup` on your Google Drive.*

3. **Restore Data:**
   ```bash
   ./rclone_restore.sh
   ```
   *If you wipe your computer or move to a new one, running this will pull all your data back down from Google Drive exactly as it was.*
