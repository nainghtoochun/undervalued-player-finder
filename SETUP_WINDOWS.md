# Week 1 setup on your Windows laptop

Do these in order. It takes about 45 minutes, mostly waiting for downloads.

## 1. Install the tools
Open **PowerShell** and run

```powershell
winget install -e --id Python.Python.3.12
winget install -e --id Git.Git
winget install -e --id Microsoft.VisualStudioCode
winget install -e --id Docker.DockerDesktop
```

Close and reopen PowerShell, then check

```powershell
python --version    # Python 3.12.x
git --version
code --version
```

Docker Desktop needs a restart and asks to enable WSL 2 the first time. You only need Docker in week 3, so skip it for now if it gives trouble.

## 2. Tell Git who you are (once)

```powershell
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

## 3. Python environment

```powershell
cd $HOME\OneDrive\Desktop\Co-op\undervalued-player-finder
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks `Activate.ps1`, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and try again.

## 4. Train xG

The Premier League 2015/16 data is already in `data\raw\statsbomb\2_27_events`, so you can skip the download. To get another league later, run `python -m pipeline.ingest_statsbomb --league "La Liga"` (about 3 to 5 minutes each).

```powershell
python -m pipeline.xg_model
python -m pytest -q
```

You should see log loss around 0.286 for our model and 0.267 for StatsBomb.

## 5. Open the notebook
In VS Code, open the project folder, install the **Python** and **Jupyter** extensions, open `notebooks\01_explore_premier_league.ipynb`, choose the `.venv` kernel, and click **Run All**.

## 6. Put it on GitHub
1. Move `setup\ci.yml` to `.github\workflows\ci.yml` (create the folders).
2. Create an empty **public** repo on github.com called `undervalued-player-finder` (no README).
3. Then

```powershell
git init
git add .
git commit -m "Week 1: project setup, StatsBomb ingest, first xG model"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/undervalued-player-finder.git
git push -u origin main
```

4. Open the **Actions** tab on GitHub and check the CI run is green.

The data folder is in `.gitignore`, so the data never goes to GitHub.

OneDrive tip. The data folder will grow to a few hundred MB once all five leagues are in. If OneDrive syncing slows things down, right-click the `data` folder and choose **Always keep on this device**.
