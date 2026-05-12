# Electronic Whiteboard

This repository is currently a starter repository for an Electronic Whiteboard project. At the moment, it does not include application source code, a package manifest, or a build script, so there is nothing to install or run yet beyond cloning the repository and preparing your Chromebook Linux environment.

## Set up on a Chromebook Linux terminal

These steps assume you are using ChromeOS with the Linux development environment enabled.

### 1. Enable Linux on ChromeOS

1. Open **Settings** on your Chromebook.
2. Search for **Linux development environment**.
3. Select **Turn on** and complete the setup wizard.
4. Open the **Terminal** app after the installation finishes.

### 2. Update Linux packages

```bash
sudo apt update
sudo apt upgrade -y
```

### 3. Install common development tools

```bash
sudo apt install -y git curl ca-certificates build-essential
```

### 4. Install Node.js for web development

If this project becomes a browser-based whiteboard app, Node.js will likely be needed for JavaScript tooling. The following installs Node.js 22 LTS from NodeSource:

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
node --version
npm --version
```

### 5. Clone this repository

```bash
git clone https://github.com/bennettabowman-ui/Electronic-Whiteboard.git
cd Electronic-Whiteboard
```

### 6. Inspect the project contents

```bash
find . -maxdepth 2 -type f | sort
```

You should currently see only repository placeholder files and documentation. There is not yet a `package.json`, `requirements.txt`, or other dependency file to install from.

## What to do next

Because the repository does not yet contain a runnable application, choose a stack before adding setup commands:

- **Static HTML/CSS/JavaScript:** add `index.html`, `style.css`, and `script.js`.
- **Vite + React:** run `npm create vite@latest . -- --template react` in the repository, then `npm install` and `npm run dev`.
- **Python backend:** add a `requirements.txt` or `pyproject.toml` before installing dependencies.

After application files are added, update this README with the exact install, run, test, and build commands.

## Basic Git workflow

```bash
git status
git add .
git commit -m "Describe your change"
git push
```
