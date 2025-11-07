This repo contains the Assignment 2 of Devops



## Run
cd flask
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=aceest_fitness.app:create_app
flask run --reload

## Tests
cd flask && pytest -q

