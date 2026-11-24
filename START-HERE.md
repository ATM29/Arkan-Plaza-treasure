# Arkan Christmas Hunt: free Vercel + Supabase setup

This package is the **Vercel version**. It is different from the earlier Python-server download. Vercel hosts the website and review API; Supabase stores submissions and photos in a Postgres table. You do not need to run `server.py` or configure Vercel Blob. The photo is compressed in the browser and stored directly in the database.

> **The live scoreboard:** `schema.sql` now also creates the `teams` and `score_events` tables used by `scoreboard.html` and `tiny-app.js`, and seeds the five guilds of the Golden Gelato Goblet hunt. The team self-join page (`join.html`) uses the `players` and `settings` tables — both are included in `schema.sql`, so running it once sets up everything. The phone game (`game.html`) additionally uses `stops_progress`, `game_meta` and `finishes` (run them from this repo's Supabase, or add them the same way). Make sure `scoreboard.html`, `join.html`, `game.html` and `arkan-treasure-hunt.html` are uploaded to the repository root too, so the landing page buttons work. Running `schema.sql` once sets up both systems.

> **Entry links (game day):** players → `https://arkanplaza.vercel.app/play.html` (play only — the Host tab is hidden); host → `https://arkanplaza.vercel.app/host.html` (lands on the PIN-protected Host dashboard with proof review). Both are thin redirects over `game.html?mode=play` / `game.html?mode=host`; plain `game.html` still shows all tabs.

You need a computer, internet access, and accounts on GitHub, Supabase and Vercel. Their free plans have limits; this is intended for a small, non-commercial event. Check each provider's current terms and quotas before the event.

## 1. Create a Supabase project

1. Sign up at https://supabase.com/ and create a new, dedicated project on the Free plan. Choose a project name and database password; keep that password somewhere safe. Choose a nearby region if offered. Wait for the project to finish starting.
2. In that project, open **SQL Editor**, create a new query, and paste the entire contents of `schema.sql` from this ZIP. Click **Run**. You should get a success message. Run it only in the project intended for the hunt.
3. Find your **Project URL** in the project's **Connect** dialog or API settings. It looks like `https://YOUR-PROJECT.supabase.co` (it is not a Postgres connection string). You'll add it to Vercel as `SUPABASE_URL`.
4. Open **Project Settings → API Keys** and find or create a **secret key** beginning `sb_secret_`. You'll add it to Vercel as `SUPABASE_SECRET_KEY`. The legacy `service_role` key also works, but the new secret key is recommended.
5. Keep the secret key private: it bypasses database security. Never paste it into GitHub, a client-side file, a chat, a screenshot, or the hunt website. Only put it into Vercel's environment-variable settings.

The SQL enables Row Level Security and denies direct public table access; the server function uses the secret key to access the table. Photos are stored in the database, so the database quota applies. Submissions remain after a Vercel restart or redeployment, subject to Supabase's limits and availability. On Supabase Free, inactive projects may be paused; wake and test the project ahead of the event.

## 2. Put the files on GitHub

1. Create a GitHub account at https://github.com if needed. Create a new repository (e.g. `arkan-christmas-hunt`); private is fine.
2. On the new repository page, choose **uploading an existing file**. Upload these files from the extracted ZIP to the **root** of the repository: `index.html`, `hero.png`, `vercel.json`, `requirements.txt`, `schema.sql`, and `START-HERE.md`. Commit the changes.
3. Add the Python function in the correct folder:
   - In your repository click **Add file → Create new file**.
   - Name the file `api/index.py` (including the slash).
   - Open `api/index.py` from the ZIP on your computer in a text editor, copy its whole contents, and paste it into GitHub's editor.
   - Commit the new file.
4. Check that the repository shows an `api` folder containing `index.py`, alongside the root files. Do not upload your Supabase secret or host password.

## 3. Deploy on Vercel

1. Sign up at https://vercel.com/ using GitHub. From the dashboard choose **Add New → Project** and import your GitHub repository.
2. Set **Framework Preset** to **Other**. Leave the build command and output directory blank/default. Do not select the repository's `api` folder as the root directory; use the repository root.
3. Before deploying, expand **Environment Variables** and add these three variables to the **Production** environment (and Preview if you intend to use Vercel preview deployments):
   - `SUPABASE_URL` → the project URL from step 1, without `/rest/v1` at the end.
   - `SUPABASE_SECRET_KEY` → your secret key starting with `sb_secret_`.
   - `HOST_PASSWORD` → a strong, unique password you invent for the hunt hosts. Don't use the demo password from the earlier preview.
4. Click **Deploy**. When deployment is complete, open the production URL Vercel provides. If you add/change variables after deploying, redeploy so they take effect.
5. Verify that the production URL is reachable on a second phone without signing in to Vercel; Vercel deployment protection may otherwise block players. Share only the production URL with your group, never the host password or Supabase secret.

## 4. Test the complete flow

Use the same production URL on two phones, or in two tabs. You don't have to be at Arkan to test!

1. In the player tab, choose Santa's Squad and start. Take/choose a photo, type a note and send it for approval.
2. In the host tab, scroll to **Host dashboard**, enter your `HOST_PASSWORD`, and open the dashboard. The submission should appear.
3. Write feedback and choose **Ask to retry**. The player should see the feedback within about five seconds and be able to resubmit.
4. Submit again, then click **Approve** in the host dashboard. The player should advance to the next clue automatically. Test this on mobile data as well as Wi-Fi and try multiple teams.
5. Download a photo to confirm it works. Check mobile camera/gallery permissions. Performances are represented by a photo plus a written explanation; videos are not uploaded.

Test submissions remain in Supabase. To clear ALL teams' submissions and start fresh: in the same project's SQL Editor run `truncate table public.hunt_submissions restart identity;`. This permanently deletes all submitted photos, notes, approvals and progress, so download anything you want first. Close or refresh old team and host pages after resetting. Do this only before the event, not during it.

## Troubleshooting

- **“The database has not been configured”**: check the three exact Vercel environment-variable names, their values, and that you redeployed after adding them.
- **“Database request failed”**: make sure `schema.sql` ran successfully in the same Supabase project as your URL and secret key; verify the key; check whether the project is paused. If just created, wait briefly for the API schema to refresh. Redeploy after correcting Vercel variables.
- **404 on submission or status**: check that GitHub has `api/index.py` (not `index.py` at the root), that the project root in Vercel is the repository root, and that you deployed the correct repository. Check the Vercel deployment and function logs.
- **Host password rejected**: use the exact `HOST_PASSWORD` configured in Vercel and redeploy after changing it.
- **Photo won't open**: allow camera/photos permission or take it with the phone's camera and choose it from the gallery. The browser must be able to open the photo. The website compresses photos before submission; it accepts photos, not video.
- **Team sees old status**: wait a few seconds or refresh and check both phones are using the same production URL and team.

## Privacy and security

This is a simple hunt for a trusted group, not a private photo-sharing platform. **Anyone with the event link can choose any team, submit as that team, and view team photos and notes.** Only the host decisions are protected by a shared password; there is no per-team login, rate limiting, or brute-force protection. Don't upload sensitive content or photos of people who haven't agreed. For stronger privacy, add individual authentication and access controls before use.

Use only your own dedicated Supabase project: a secret key gives the server powerful access. The server never sends the secret to the browser. Delete the data after the event if you no longer need it.
