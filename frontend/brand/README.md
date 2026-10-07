# Brand: app name and icon

Everything the app calls itself lives in this folder.

**Change the name:** edit `brand.json`. `name` is the title on the top bar, the
sign-in page, the browser tab and the installed app; `shortName` is the label
under the home-screen icon (keep it under ~12 characters). `description`,
`themeColor` and `backgroundColor` go into the PWA manifest. Restart
`npm run dev` / rebuild to pick it up.

**Change the icon:** replace `icon.png` (square, at least 512 px, ideally
1024x1024, transparent or solid background), then from `frontend/` run:

```bash
python scripts/make-icons.py
```

That regenerates every size in `public/` (192/512 icons, the maskable icon,
the iOS apple-touch-icon and `favicon.ico`). Commit `icon.png` and the
regenerated files. Delete `icon.png` and rerun the script to get the
placeholder pin back.
