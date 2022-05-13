pip install -e .

pybabel extract -F babel.cfg -k _l -o /tmp/messages.pot .
# pybabel init -i /tmp/messages.pot -d hyperbitch/translations -l pl
pybabel update -i /tmp/messages.pot -d hyperbitch/translations
pybabel compile -d hyperbitch/translations

export FLASK_APP="hyperbitch"
#export FLASK_ENV="development"
FLASK_RUN_PORT=5088 FLASK_RUN_HOST="0.0.0.0" flask run
