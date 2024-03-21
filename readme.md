# Liizzii's Meshtastic stuff

## What is meshtastic?
[Check their website](https://meshtastic.org)

## What do these scripts do?
Many things

## How do I run them?
Set up a virtualenv for python, activate it, install requirements, run script.

Note: instructions are linux/unix specific, if you're on Windows: GL;HF

```bash
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
python name_of_script.py
```

## What scripts are working?
Right now, just `mqtt_json_responder.py` is fleshed out and is final.

If you're reading this on GitHub, then know that this repo is actually a mirror from my personal GitLab instance. 
Thus there may be times when either this repo lags behind my personal one or broken code gets pushed to here. 
I offer no warranty with the code, use at your own risk.

## What's planned?
Some app to note down nodes and track stats like battery, airtime, etc.
This will be displayed either in a dedicated GUI or a web interface (whichever I find easier to code when I get to it).


## Why are you using AsyncIO? Why not [other thing]?
I'm used to using AsyncIO-based stuff in some of my other projects (namely a discord bot).
Other libraries may be faster, but I don't have the motivation to learn something new. 
Also this is my personal project, [but don't worry, I have a permit](https://www.youtube.com/watch?v=uq6nBigMnlg)


Project is licensed with Mozilla Public License v2
