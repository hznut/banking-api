setup_venv:
	test -d venv || python3 -m venv venv

install: setup_venv
	. venv/bin/activate && pip install -r ./requirements.txt

tests: install
	. venv/bin/activate && PYTHONPATH=./runtime/src/ pytest ./runtime/

synthesize: install
	pushd .; . venv/bin/activate && cd infrastructure && cdk synthesize; popd

deploy: swagger_json
	pushd .; . venv/bin/activate && cd infrastructure && cdk bootstrap && cdk deploy; popd

destroy_stack: install
	pushd .; . venv/bin/activate && cd infrastructure && cdk destroy; popd

swagger_json: install
	pushd .; . venv/bin/activate && cd runtime/src && chalice generate-models > ./chalicelib/swagger.json; popd