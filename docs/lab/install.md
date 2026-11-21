# Install on your computer

The Stress Lab runs entirely on your own computer. You install it once, start it from a terminal,
and use it in your web browser at `http://127.0.0.1:8765`. Nothing is uploaded: your banks and runs
stay in a folder on your computer. Only two things use the internet: installing, and importing a
bank's Call Report from the FDIC.

It works on Windows, macOS and Linux. A run needs about 200 MB of memory and one processor core.

## The easy way: with uv

[uv](https://docs.astral.sh/uv/) is a small installer for Python programs. It downloads a suitable
version of Python for the lab, so you do not need to install Python yourself, and it keeps the lab
separate from anything else on your computer.

**1. Open a terminal.**

- **Windows:** press ++windows++, type `PowerShell` and open **Windows PowerShell**.
- **macOS:** press ++cmd+space++, type `Terminal` and open it.
- **Linux:** open your terminal application.

**2. Install uv.** Copy the line for your system, paste it into the terminal and press ++enter++.

=== "Windows"

    ```powershell
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

=== "macOS and Linux"

    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

Then **close the terminal and open a new one**, so that it finds the `uv` command.

**3. Install the lab.**

```bash
uv tool install "brms[web]>=0.2"
```

This takes a minute the first time.

**4. Start it.**

```bash
brms-web
```

The terminal shows:

```text
BRMS Stress Lab running at http://127.0.0.1:8765/
Your banks and runs are saved in C:\Users\you\.brms-web
Keep this window open while you use the lab. To stop it, click Quit in the lab or press Ctrl+C here.
```

and your browser opens the lab. If it does not, open <http://127.0.0.1:8765> yourself. The first
start takes up to half a minute while the demo banks are prepared.

Now follow the [quick start](quickstart.md).

!!! tip "Just trying it?"
    `uvx --from "brms[web]>=0.2" brms-web` starts the lab without installing it.

## With pip

If you already use Python 3.11 or later, install the lab into a virtual environment:

=== "Windows"

    ```powershell
    py -3.12 -m venv brms-env
    brms-env\Scripts\activate
    python -m pip install "brms[web]>=0.2"
    brms-web
    ```

=== "macOS and Linux"

    ```bash
    python3 -m venv brms-env
    source brms-env/bin/activate
    python -m pip install "brms[web]>=0.2"
    brms-web
    ```

Activate the environment again (the second line) each time you open a new terminal.

`pip install brms`, without `[web]`, installs the Python library and the command line only.

## Every day

| To | Do this |
|---|---|
| start the lab | open a terminal and run `brms-web` |
| stop it | click **Quit** at the top right of the lab, or press ++ctrl+c++ in its terminal |
| open it again in the browser | run `brms-web` again: if the lab is already running, it opens the browser at it |
| update to the latest version | `uv tool upgrade brms` (with pip: `python -m pip install -U "brms[web]"`) |
| uninstall | `uv tool uninstall brms`, then delete the data folder if you no longer need it |

Closing the browser tab does not stop the lab. Stopping it stops any run still in progress (the run is
marked failed; start it again later). Your banks and finished runs are kept.

## Your data

Banks you import and runs you make are saved in a folder in your home directory:
`C:\Users\<you>\.brms-web` on Windows, `~/.brms-web` on macOS and Linux. They are still there the
next time you start the lab. To keep them somewhere else, start the lab with
`brms-web --data-dir <folder>`, or set the environment variable `BRMS_WEB_HOME`.

Each run takes a few MB. Delete runs you no longer need on the **Runs** page. The demo banks come
with the lab and cannot be deleted.

## Options

```bash
brms-web [--port 8765] [--data-dir FOLDER] [--workers N] [--no-browser]
```

| Option | Meaning |
|---|---|
| `--port` | the port in the address (default 8765) |
| `--data-dir` | where banks and runs are saved (default `$BRMS_WEB_HOME` or `~/.brms-web`) |
| `--workers` | how many runs execute at the same time (default: one per processor core, leaving one free, at most four) |
| `--no-browser` | do not open the browser |

The lab listens only to your own computer (`127.0.0.1`): other computers on your network cannot
reach it.

The browser app talks to the lab through a JSON API, documented at <http://127.0.0.1:8765/docs>
while the lab is running.

## If something goes wrong

**`brms-web` or `uv`: command not found.**
Close the terminal and open a new one. If it still fails after installing uv, run
`uv tool update-shell`, then open a new terminal.

**"Port 8765 is used by another program".**
Start the lab on another port, `brms-web --port 8800`, and open <http://127.0.0.1:8800>.

**The browser shows an old page after an update.**
Reload the page (++ctrl+shift+r++, or ++cmd+shift+r++ on a Mac).

**pip says Python is too old, or installs version 0.1.**
The lab needs Python 3.11 or later. Use the uv method above, which brings its own Python.

**Importing a Call Report fails behind a company proxy.**
The import downloads the filing from `api.fdic.gov`. Set the proxy before starting the lab, for
example `set HTTPS_PROXY=http://proxy.example.com:8080` (Windows) or
`export HTTPS_PROXY=http://proxy.example.com:8080` (macOS and Linux). Or download the filing on
another machine with `python -m brms.lab call-report --cert N --date D --out bank.json` and import
the bank file instead.

**A run fails.**
The run's page shows the error. Runs never change the bank, so you can start another one. If the
lab itself stops, start it again: runs that were in progress are marked failed.
