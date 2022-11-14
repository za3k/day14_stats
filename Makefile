run-debug:
	flask --debug run
run-demo:
	gunicorn3 -e SCRIPT_NAME=/hackaday/stats --bind 0.0.0.0:8014 app:app
