# eBird-readme-card

> Turn your birding activity into a beautiful GitHub profile card.

Generate a clean and stylish SVG stats card from your eBird data, built specifically for GitHub Profile READMEs.

---

## 🚀 Demo & Preview

<p align="center">
  <img src="ebird-card.svg" alt="eBird README Card" width="450">
</p>

A simple way to showcase your recent eBird activity, total species, and latest sighting directly on your GitHub profile.

---

## ✨ Features

- **Key Statistics**: Display your total species, checklists, and observations at a glance.
- **Latest Birding Session**: Automatically tracks your last birding date, location, and the last bird you sighted.
- **Custom Location Formats**: Choose how your location is displayed (`location`, `state`, `country`, or hidden with `none`).
- **Custom Card Titles**: Personalize your card title (defaults to `🪶 My Feathered Log`).
- **Automated Workflow**: Powered by GitHub Actions for easy manual generation using your eBird export data.

---

## 🛠️ How to Use

1. **Download your eBird data**: Go to eBird, request your data download, and get your export ZIP link.
2. **Run the GitHub Action**: 
   - Go to your repository's **Actions** tab.
   - Select **Update README cards**.
   - Click **Run workflow**.
   - Paste your eBird ZIP download URL and optionally choose your preferred **Location Display Mode** and **Custom Title**.
3. **Add to your README**:
   ```markdown
   ![eBird Card](ebird-card.svg)
