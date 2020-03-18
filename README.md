# OpenTDB Quiz Bot

A telegram quiz bot fed with opentdb.com data.

## Dependencies

- `python-venv` or [pipenv](https://pipenv.kennethreitz.org/en/latest/)
- [requests](https://requests.readthedocs.io/en/master/)
- [python-telegram-bot](https://python-telegram-bot.readthedocs.io/en/stable/)

## Running
1. Clone the repo & cd into it.
```
# if using pipenv
pipenv install
pipenv shell
python bot.py

# ============

# if using python-venv / virtualenv
python3 -m venv env/
source env/bin/activate
pip install -r requirements.txt
QB_BOT_TOKEN="YOUR TELEGRAM BOT TOKEN" python bot.py
```

## Credits

- [requests](https://requests.readthedocs.io/en/master/)
- [python-telegram-bot](https://python-telegram-bot.readthedocs.io/en/stable/)
- [opentdb.com](https://opentdb.com/)