# ContactScraper

> IMPORTANT: requires `selenium` and `requests`
> IMPORTANT: requires `Firefox` (selenium runs on ff)


## Running the script locally

I've added instructions for Linux/MacOS machines primarily 

### Using `uv` (Recommended)

`uv` is a blazing-fast python package manager written in Rust. Using `uv` should be the norm! *(i love `uv`)*

#### Linux/macOS

##### `uv` installation

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh     # install uv
```
> You may need to restart your shell for `uv` to start working properly

##### Local setup

```bash
git clone https://github.com/suynep/ContactScraper.git
cd ContactScraper/
uv sync
```

For extracting contact info from a URL:
`uv run scraper.py -u "<URL>"`
> Example: `uv run scraper.py -u "https://ku.edu.np"`

For extracting contact info from keywords:
`uv run scraper.py -k "<KEYWORDS>"`
> Example: `uv run scraper.py -k "Software Companies in Kathmandu"`

#### Windows

#### `uv` installation

In PowerShell, run:
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Now, clone and run `interactor.py` after running `uv sync` in the cloned local repo.


### Using `pip`


#### Linux/macOS

##### Local setup + running

```bash
git clone https://github.com/suynep/ContactScraper.git
cd ContactScraper/
python3 -m virtualenv .venv    # BEFORE RUNNING: ensure that virtualenv package is installed
source ./.venv/bin/activate
pip3 install -r requirements.txt     # or pip instead of pip3, whatever it's called
```

For extracting contact info from a URL:
`python3 scraper.py -u "<URL>"`
> Example: `python3 scraper.py -u "https://ku.edu.np"`

For extracting contact info from keywords:
`python3 scraper.py -k "<KEYWORDS>"`
> Example: `python3 scraper.py -k "Software Companies in Kathmandu"`


# Saving the extracted Contact Info
Append the above scripts with a `-l` flag and the info is saved at `<current_dir>/contact__<time>.json`