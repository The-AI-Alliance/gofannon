# Gofannon Quickstart

## Install
```bash
git clone https://github.com/The-AI-Alliance/gofannon.git
cd gofannon/webapp/infra/docker
```
Add `webapp/infra/docker/.env` file with these contents:
```bash
OPENAI_API_KEY=sk-proj-your-key
ANTHROPIC_API_KEY=sk-ant-your-key
# GEMINI_API_KEY if you have one
COUCHDB_USER=admin
COUCHDB_PASSWORD=password
```
```bash
docker-compose up --build
```
### Rebuild after pulling new work from `main`
```
cd gofannon/webapp/infra/docker
docker-compose down && docker-compose up -d --build
```

## Visit app
http://127.0.0.1:3000/
![Home page](images/home-page.png)

## Create agent
![Create agent](images/create-agent.png)

### Choose tools if needed
* MCP server by URL
* Swagger spec by file or URL
* Agents and tools already deployed on this Gofannon instance

### Add description (prompt)
![Add description](images/add-description.png)

## Choose compose and invokable models

### Set model
![Set models](images/set-model.png)

### Choose provider, model, params
![Model dialog](images/set-model-dialog.png)

### Optionally select built-in tool
![Choose tool](images/choose-tool.png)

### Model set
![Model set](images/model-set.png)

## Generate/re-generate code
![Generate code](images/generated-code.png)

## Run in sandbox

### Enter prompt
![Sandbox](images/sandbox.png)

### Results
![Sandbox results](images/sandbox-results.png
)
## Save/update agent
![Save/update](images/generated-code.png)

## Deploy agent
![Deploy](images/deploy.png)
