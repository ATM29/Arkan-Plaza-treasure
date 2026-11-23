# The Arkan Christmas Hunt — host review setup

Teams can upload a photo and a short explanation at each stop. Hosts approve it or send it back with feedback. A team can only move to the next clue once the host approves the current submission. The host dashboard and all teams need to use the **same running server**.

## Option 1: run locally for a test

1. Install Python 3.9 or later from python.org. No extra packages are required.
2. Unzip the website folder, open a terminal in it, and choose a long, unique host password.
3. On Mac/Linux run:
   ```sh
   export HOST_PASSWORD='choose-a-long-unique-password'
   python3 server.py
   ```
   On Windows PowerShell run:
   ```powershell
   $env:HOST_PASSWORD='choose-a-long-unique-password'
   python server.py
   ```
4. On that computer, open `http://localhost:8000`. Select a team to submit; open **Host dashboard** and enter the password to review. Do not share the host password with players.
5. For testing with phones on the **same Wi-Fi**, find the computer's local IP address and open `http://COMPUTER-IP:8000` on each phone. The computer must remain on, the Wi-Fi must allow devices to see one another, and its firewall must allow port 8000. This will not work on separate mobile-data connections. Camera support on plain HTTP varies by browser; players can take photos with their normal camera app and use **Choose photo** instead.

## Option 2: put it online for the event

Use a hosting service that runs a Python web service and provides **persistent disk**. Upload these files to a Git repository and create a web service from it. Set:

- **Start command:** `python3 server.py`
- **Environment variable:** `HOST_PASSWORD` = a strong, private password
- **Environment variable:** `DATA_DIR` = the persistent disk's mounted path, for example `/var/data`
- **Port:** the server listens on the provider's `PORT` environment variable, or 8000 if not supplied.
- Mount persistent storage at the same path used for `DATA_DIR`.

The host gives you a public HTTPS URL. Share that URL with the teams, and use the same URL yourself to open the host dashboard. HTTPS is recommended for photos and protects the password in transit. Keep the service running for the whole event. Many free hosts have temporary storage or sleep; submissions may be lost or unavailable after restarts. Confirm persistent disk and pricing with your chosen provider before the event. SQLite here requires a **single server instance** with a writable local persistent disk; do not use multiple instances or serverless hosting.

## On the day

- Set the chosen entrance and Santa's HQ in advance, and check venue signs.
- Have each team select its assigned name. At every stop, add a photo and a note explaining the challenge; for a performance, submit a representative photo and describe what the team did. This version does not upload video.
- In the **Host dashboard**, sign in and review each submission. Approve to let the team continue, or reject with a note. Teams see your decision automatically within a few seconds and can resubmit if needed. Hosts can download the current photo for each stop.
- Teams and hosts should test their connections before starting. Gallery photos on the earlier browser-only version are not automatically uploaded: choose them again to submit.
- Team names and uploaded photos are not private from anyone who has the event link. Anyone with the link can impersonate a team or view team photos. The password protects only host decisions. Use a private event link, avoid uploading sensitive images or photos of strangers without consent, and don't use this for sensitive data. Host access uses one shared password, with no account system or brute-force protection; this simple version is for a small trusted group, not a security-sensitive public service.
- Photos and notes stay in `DATA_DIR/hunt.sqlite3` until you delete that file. Stop the server first; deleting it erases all submissions and progress. Make a backup of it while the server is stopped if you need to keep the memories.
