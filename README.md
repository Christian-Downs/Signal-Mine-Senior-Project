To get this repository on your machine, enter a new folder and run the command
```
git clone https://github.com/Christian-Downs/Signal-Mine-Senior-Project
```


To run test.py: run in the terminal
```
pip install --upgrade openai pydantic
```

Then do
```
# macOS / Linux
export OPENAI_API_KEY="sk-..."
# Windows (PowerShell)
$Env:OPENAI_API_KEY="sk-..."
```
You must run the following command in the same terminal that you set the api key in
```
python test.py
```