<div align="center">

# Github Archive

Clone your entire Github instance or save it to an archive.

[![Build Status](https://travis-ci.org/Justintime50/github-archive.svg?branch=master)](https://travis-ci.org/Justintime50/github-archive)
[![MIT Licence](https://badges.frapsoft.com/os/mit/mit.svg?v=103)](https://opensource.org/licenses/mit-license.php)

<img src="assets/showcase.gif">

</div>

## Install

This project requires that you have Python installed. Python comes built-in on macOS and Linux.

1. Run `cp .config.example .config` and edit the values to your liking.
1. For private repos, you must have an SSH key generated on your local machine and added to Github.

### Automating SSH Passphrase Prompt (optional)

To allow the script to run continuosly without requiring your SSH passphrase, you'll need to add your passphrase to the SSH agent.

```bash
ssh-add -K ~/.ssh/id_rsa
```

## Usage

Github Archive will clone any repo that doesn't exist locally and pull those that do from the master branch of each repo that you have access to including organizations (if configured). You can run the script once or have it setup with a cron or Launch Agent and run occasionally to clone/pull any changes since it was last run.

**Merge Conflicts:** *Be aware that using Github Archive could lead to Merge Conflicts if you continually pull the same repos you work on without stashing or committing your changes. It is recommended to be used once for example on a new machine or setup as a separate archive from your development repositories. If you use Github Archive to pull in nighly changes from various repos, you should be religious about stashing or committing your changes or you will receive merge conflicts and the script may not complete running.*

### Single Use
```bash
./backup.sh
```

### Cron
```bash
crontab -e

0 1 * * * ~/github-archive/backup.sh
```

### Launch Agent (Recommended on macOS)

Edit the path in the plist file to your script and logs as well as the time to execute, then setup the Launch Agent:

```bash
cp local.githubArchive.plist ~/Library/LaunchAgents

launchctl load ~/Library/LaunchAgents/local.githubArchive.plist
```

More info on [Launch Agents](https://www.launchd.info).
