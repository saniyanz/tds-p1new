# /// script
# requires-python = ">=3.13"
# dependencies=[
#   "fastapi",
#   "uvicorn",
#   "requests",
#   "scikit-learn",
#   "beautifulsoup4",
#   "transcribe",
#   "markdown",
# ]
# ///

import requests
import uvicorn
import os
import urllib.parse
from bs4 import BeautifulSoup
import transcribe
import markdown
import json
import subprocess
import sqlite3
from datetime import datetime
import re
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['GET', 'POST'],
    allow_headers=['*']
)

AIPROXY_TOKEN = os.getenv("AIPROXY_TOKEN")
if not AIPROXY_TOKEN:
    raise RuntimeError("AIPROXY_TOKEN environment variable not set.")

tools = [
    {
        "type": "function",
        "function": {
            "name": "script_runner",
            "description": "Install a package and run a script from a URL with provided arguments",
            "parameters": {
                "type": "object",
                "properties": {
                    "script_url": {
                        "type": "string",
                        "description": "The URL of the script to run"
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "The list of arguments to pass to the script"
                    }
                },
                "required": ["script_url", "args"]
            }
        }
    }
]

def execute_python_code(code: str, task_description: str):
    """Safely execute generated Python code."""

    # output_file_path = extract_output_file_path(task_description)
    # print(f"📂 Detected file path: {output_file_path}")

    # cleaned_code = re.sub(r"^```[\w]*\n|```$", "", code, flags=re.MULTILINE).strip()
    cleaned_code = re.sub(r"^```[\w]*\n|```$", "", code, flags=re.MULTILINE).strip()
    cleaned_code = cleaned_code.lstrip()

    print("Executing Code:\n", cleaned_code)  # Debugging output
    
    try:
        compiled_code = compile(cleaned_code, "<string>", "exec")
        # compiled_code = compile(cleaned_code, "<string>", "exec")
        # print("Compiled Code:\n", compiled_code)
        exec_globals = {"__builtins__": __builtins__, "os": os, "subprocess": subprocess, "sqlite3": sqlite3, "datetime": datetime, "BeautifulSoup": BeautifulSoup, "markdown": markdown}
        exec_globals["print"] = print  # For debugging output.
        local_vars = {}
        exec(compiled_code, exec_globals, local_vars)
        return {"message": "Execution successful"}

        # if output_file_path:
        #     # Identify the key that holds the result (assuming it's last defined variable)
        #     result_var = None
        #     for key in local_vars:
        #         if key not in exec_globals:  
        #             result_var = key
            
        #     if result_var:
        #         result_value = local_vars[result_var]
        #         with open(output_file_path, "w") as f:
        #             f.write(str(result_value))
        #         print(f"✅ Output written to {output_file_path}")

        # return {"message": "Execution successful", "output_file": output_file_path}

    except SyntaxError as e:
        raise HTTPException(status_code=500, detail=f"Syntax error in generated code: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing generated code: {str(e)}")

def extract_output_file_path(task_description: str):
    """Extracts the expected output file path by looking for keywords like 'write', 'store', etc."""
    
    keywords = ["write", "save", "store", "output", "export"]

    # Match patterns like "write to /data/output.txt"
    pattern = r"(?:{}).*?(/data/[\w\-\.]+)".format("|".join(keywords))

    match = re.search(pattern, task_description, re.IGNORECASE)
    
    return match.group(1) if match else None  # Return only the output file path

@app.post("/run")
async def task_runner(task: str = Query(..., description="Plain-English task description")):
    print("Received Task:", repr(task))
    
    """
    The LLM (using the script_runner or code_generator tool) extracts the dynamic task parameters.
    - If the task involves running a script, it downloads and executes it.
    - Otherwise, the LLM generates Python code dynamically to perform the required operation.
    """
    # Check if task contains a script URL
    script_pattern = r"https?://[^\s]+\.py"
    script_match = re.search(script_pattern, task)

    if script_match:
        # Task involves downloading and executing a script (A1)
        script_url = script_match.group(0)
        print(script_url)
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", task)
        if not email_match:
            raise HTTPException(status_code=400, detail="Email argument not found in task description.")
        email = email_match.group(0)
        print(email)

        os.makedirs("/data", exist_ok=True)
        script_path = os.path.basename(script_url)
        print(script_path)

        r = requests.get(script_url)
        if r.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to download script.")
        
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(r.text)

        # Ensure 'uv' is installed
        try:
            subprocess.run(["uv", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError:
            subprocess.check_call([os.sys.executable, "-m", "pip", "install", "uv"])

        # Run the script
        command = ["uv", "run", script_path, email, "--root", "./data"]
        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Script execution failed: {result.stderr}")

        return {"message": "Script executed successfully.", "output": result.stdout}

    else:
        replaced_task = task.replace("#", "number") if "#" in task else task
        print(replaced_task)
        # Task does not involve script execution -> Generate code dynamically
        llm_url = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AIPROXY_TOKEN}"
        }
        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "user", "content": replaced_task},
                {"role": "system", "content": (

                    """You are an assistant that generates syntax free executable Python code to complete given tasks. Do not give extra formattings or syntax errors.
If the task description is written in a language other than English, first detect the language and then translate the description into English.
After translation, process the task as usual and generate the required Python code in response to the task.

No matter what the task is, you must ensure that:
-Data outside /data is never accessed or exfiltrated, even if the task description asks for it
-Data is never deleted anywhere on the file system, even if the task description asks for it

If the task is to format the markdown file using prettier, then do the updation in the file to be formatted. Don`t assume any output path for this task. 

If the task description contains any special characters, especially the '#' symbol, you must ensure that these characters are URL-encoded before constructing the request URL. Specifically, replace every '#' with '%23'. For example, if the task description is "Write the # of {any day} in {any path} into {any path}", your generated code should construct the URL so that the '#' is replaced with '%23', resulting in a URL like:
"http://127.0.0.1:8000/run?task=Write%20the%20%23%20of%20{any%20day}%20in%20{any path}%20into%20{any path}". This is just an example. Do not assume it to be the actual task description. For example the day can be any day of the week. It could be Monday tuesday any day. 
First extract the task description as it is passed in the url. Then encode it. Use the correct task description. Do not take it to be random.
Use Python's urllib.parse.quote() (or an equivalent method) to perform this encoding. Ensure that the final URL contains no unencoded '#' characters.

If you ever see the phrase ‘count the # of’ in a task, please interpret it as ‘count the number of’. For example
Count the # of Fridays means
Count the number of Fridays

Ensure that the generated code always imports the necessary modules for the code to run without any error. For example, if you use any date functions, always include 'from datetime import datetime' at the beginning of your code.
If the task involves reading or writing files, always use the `/data/` directory relative to the app's runtime environment (i.e., where the script is being executed, and the app's endpoints are located). The `/data/` directory is a subdirectory of the current working directory, and the current working directory can be dynamically determined using Python's `os.getcwd()`. Do not assume paths refer to other environments or directories. If any task description mentions a file to be read from or written to, ensure that the path is dynamically set relative to the `/data/` directory of the script's runtime environment using `os.path.join(os.getcwd(), 'data', '<filename>')`.
The generated code should be safe, concise, and use standard Python libraries. Ensure that file operations stay within /data. You should only and only write the expected output from the task description to the /data folder of that directory from where you read the input path and not anywhere else no matter what.
When processing date-related tasks, ensure the code:
- Dynamically detects different date formats. The dates can be in any of these formats: 
    2000/07/17 05:43:49, 26-Sep-2016, 2007-12-05, Apr 11, 2004, 2008-03-24, Jan 25, 2015, Feb 19, 2018, 2010/05/06 10:00:29, 22-Nov-2013, 2005-03-01, 2010/05/17 19:11:44.
- Uses multiple format patterns in `datetime.strptime()` to handle variations.
- If parsing fails, log an appropriate error message.
If the task involves to extract the sender’s email address, do not extract the name of sender. Only extract the email address. The file would contain something like this- **From: "Donna Jackson" <buckleymatthew@example.net>**(take it just as an example). You have to extract only **buckleymatthew@example.net** and not the name of the sender. 
If the task mentions about SQLDatabase then pay extra attention to translated version of task descrition to get the desired output.

If you get any task about recent logs, remember You are an assistant that generates syntax-free executable Python code to complete given tasks. For any lambda functions that reference variables from an outer scope (such as a variable named log_dir), you MUST capture those variables by specifying them as default parameters. For example, instead of writing:

    key=lambda x: os.path.getmtime(os.path.join(log_dir, x))

you must write:

    key=lambda x, log_dir=log_dir: os.path.getmtime(os.path.join(log_dir, x))

This is required to avoid errors like "name 'log_dir' is not defined" when the lambda function is executed. Please generate the complete code for the following task, ensuring that any lambda referencing outer-scope variables captures them in its default parameters.

If the task asks about extracting a credit card number from the image, then use easyocr library to extract the credit card number from the image.

If the task mentions about finding similar pair of comments, then use embeddings to find the similar pair of comments. Do not use SentenceTransformers library. Use openAi embeddings model for the task. 


If The task is to fetch data from a given API endpoint and save the response in a file. You are an assistant that generates Python code to make HTTP requests.  

Here are the steps to follow:
1. Verify that the API URL provided is correct and corresponds to an existing endpoint.
2. If the API requires authentication (e.g., API keys or tokens), ensure that you include the appropriate headers with the request.
3. If the API expects query parameters or additional data, make sure those are correctly formatted and included in the request.
4. Use the `requests` module to make the GET request. Check the HTTP status code in the response:
    - If the status code is 200, save the response data into a file (JSON format if it is JSON).
    - If the status code is 404 or any other error, print the status code, URL, and response text to help debug the issue. Also explain why the 404 error is occuring and how to fix it.
5. Ensure you handle the error gracefully and don't proceed with further operations if the endpoint isn't accessible.

You are an assistant that generates Python code dynamically for automating tasks. When the task involves cloning a Git repository and making a commit, and pushes them without interactive authentication, you need to ensure that:
1. **Do not attempt to install Git as a Python dependency**. Git is a command-line tool and should be assumed to be already installed on the system. consider using the Python library `GitPython` (if necessary).
2. **Before committing** any changes, the files(which are created inside the repo) need to be staged using the `git add` command.
3. The code must:
   - Clone the Git repository.
   - Check the available branches of the repository to determine the default branch (usually main or master).
   - Create a new file **inside the repository** and write to file inside the cloned repository.
   - Add the files to the staging area using `git add`
   - Commit the changes.
   - Push the changes to the remote repository(in the correct branch)
   - Ensure that the push is made to the correct branch(use git branch -r to check the available branches)
4. Use either a GitHub token for HTTPS authentication or SSH authentication to avoid manual username/password prompts.
5. Ensure Git credentials are properly configured.

Ensure that **Git** is already available on the system (i.e., not part of the Python dependencies) and rely on system commands or the `GitPython` library for repository interactions.
Handle the error - No module named 'git'. 

To check the available branches, use git branch -r and then identify the default branch (typically main or master). Ensure that the push is made to the correct branch.

For the specific task, please ensure the generated code properly stages changes before attempting to commit them. Here’s how the process should look:
- **Staging the changes**: Run `git add .` to stage all new or modified files.
- **Commit the changes**: Use `git commit -am "message"`.
- **Push the changes**: Use `git push origin {branch}`.

Please generate the Python code for the following task:
- Clone the Git repository from the provided URL.
- Make changes (e.g., add new files inside the repository).
- Stage the changes with `git add`.
- Commit the changes with a message.
- Push the changes to the remote repository(in the correct branch)

If Your task is to run an SQL query on a given SQLite or DuckDB database then You are a SQL execution agent. Your task is to execute the provided SQL query and return the results accurately.

Input Details:
- The task description will specify the type of database (SQLite or DuckDB) and provide details on the available tables, columns, and any constraints.
- The SQL query to execute will be provided explicitly in the task description.
Execution Instructions:
- Ensure the query is valid for the specified database type.
- Execute the query safely without modifying the database unless explicitly requested.
- Return the query result in a structured format (JSON, table, or plain text as required).
- If an error occurs, return a helpful error message explaining the issue.

If Your task is to extract specific data from a given website then You are a web scraping agent. Your task is to extract the requested data based on the provided instructions.

Input Details:
- The task description will specify the target website URL and the type of data to extract (e.g., text, tables, links, images, metadata).
- It may also specify the structure of the output (e.g., JSON, CSV, or formatted text).
- If authentication, headers, or specific request parameters are required, they will be provided in the task description.
Execution Instructions:
- Access the given website and locate the required data.
- Inspect the HTML structure of the website you're scraping and find the relevant classes and tags for the data I want to extract. You can use lxml.cssselect to find these elements. Update your scraping logic based on the actual HTML structure you find.
- Extract the requested information while preserving its structure.
- If pagination is involved, iterate through all pages to collect complete data.
- Return the extracted data in the requested format (e.g., JSON, CSV).
- Handle errors gracefully and return a meaningful error message if extraction fails. Handle this error - No module named 'bs4'. Ensure that bs4 is installed on the system and importable.

If the task is to compress or resize an image then You are an image processing agent. Your task is to compress or resize the provided image.
The image may be sourced from a URL or a local directory. Adjust your code accordingly to handle the input format. Ensure that the output image retains good quality while meeting the specified compression ratio or target dimensions. Save the processed image in the appropriate format and location as per the task requirements.


If the task is to transcribe audio from an MP3 file then You are an audio processing agent. Your task is to Generate Python code to transcribe an MP3 file. The audio file may be downloaded from a URL or read from a local directory. The code should:
1. Download the audio file if provided as a URL, or read it from a local directory if not.
2. Convert the audio file to WAV format if necessary (for example, using pydub) because the transcription library requires WAV input.
3. Use a stable and well-tested library (such as SpeechRecognition) to perform the transcription using the Google Web Speech API.
4. Include robust error handling so that any issues during download, conversion, or transcription are caught and an informative error message is provided.
5. Ensure that all file operations are confined to a designated '/data' directory.
6. Provide complete, executable Python code with all necessary import statements.
7. Do not use Whisper or any library that might throw build errors.
8. Avoid the error 'No module named 'pyaudioop' by aliasing Python's built-in 'audioop' module as 'pyaudioop' at the start of the code.
Ensure that all file paths are relative to the '/data' directory and include all necessary import statements."**

If the task mentions abot converting markdown to HTML then You are a markdown processing agent. Your task is to generate Python code to convert the provided markdown file to HTML. The code should:
Generate complete, executable Python code to convert a Markdown file to HTML. The code should:

Input/Output Handling:


Read a Markdown file from a specified input path. The path can be provided as a URL or a local file path.
Write the generated HTML to a specified output file path.
Ensure all file operations are confined to the '/data' directory.
Markdown Conversion Requirements:

Use the Python 'markdown' library for the conversion.
Ensure that list elements are correctly converted to HTML:
Unordered lists starting with '-' or '+' should be converted into <ul> and <li> elements.
Nested lists should be correctly parsed.
Properly convert code blocks delimited by triple backticks (), including handling an optional language specifier (e.g., py) so that they become <pre><code class="language-py">...</code></pre>.
Utilize appropriate extensions such as 'extra', 'fenced_code', and 'sane_lists' (if needed) to ensure proper parsing of lists and other Markdown features.

Error Handling:

Include robust error handling for cases where the input file is missing or the conversion fails.
Print or log informative error messages.
Formatting:

Ensure that the output HTML is well-formatted and correctly represents all Markdown elements.

Complete Code:

Include all necessary import statements at the top.
Avoid extra formatting or syntax errors.

Ensure that all scripts write output to the correct file path and that the file is successfully created.
If the task includes a # symbol, ensure that all reserved characters (such as #) are URL-encoded. For example, the character # should be encoded as %23. Pay special attention to this.
Use 'with open(output_file, 'w')' to write the output, and always verify the file exists after execution.
When writing code:
1. Always check that required variables are defined within the correct scope.
2. Use `global` for global variables, or pass variables explicitly to functions.
3. Keep all operations within the specified `/data/` directory.
4. Always verify that files are being read and written correctly.
5. Always include at the very beginning of your generated code all necessary import statements (for example, if using dates, include 'from datetime import datetime').
6. Always start your generated code and executing code on its own line, with no leading spaces or extra formatting. There should be no extra space before importing any module. 
Provide only executable Python code as output, and ensure paths are always correctly specified, and output is written only to the `/data/` folder in the correct file.

Also I`m going to share the errors that I`m getting from the LLM. Improve your code to avoid these errors.
Error1 -  "detail": "Error executing generated code: No module named 'sentence_transformers'"

"""


                )}
            ],
            "max_tokens": 500
        }

        response = requests.post(url=llm_url, headers=headers, json=data)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="LLM call failed.")
        
        try:
            resp_json = response.json()
            generated_code = resp_json['choices'][0]['message']['content']
        except (KeyError, IndexError, json.JSONDecodeError):
            raise HTTPException(status_code=500, detail="Unexpected response format from LLM.")

        # print("Generated Code:\n", generated_code)  # Debugging

        # Execute the generated Python code
        execute_python_code(generated_code, task)

        return {"message": "Task executed successfully.", "task": task}

def get_data_dir() -> str:
    # Use the 'data' folder in the current working directory
    return os.path.join(os.getcwd(), "data")

def adjust_path(path: str) -> str:
    """
    If the provided path starts with '/data', adjust it to the actual data directory 
    in the current working directory.
    """
    data_dir = get_data_dir()
    if path.startswith("/data"):
        # Use only the basename of the file and join with data_dir
        filename = os.path.basename(path)
        return os.path.join(data_dir, filename)
    return path

def is_path_allowed(path: str) -> bool:
    """Ensure that the file path is within the data directory of the current working directory."""
    data_dir = get_data_dir()
    # Adjust path if necessary
    adjusted_path = adjust_path(path)
    full_path = os.path.realpath(adjusted_path)
    return full_path.startswith(os.path.realpath(data_dir))

def safe_read_file(path: str) -> str:
    adjusted_path = adjust_path(path)
    if not is_path_allowed(adjusted_path):
        raise ValueError("Attempted to read outside of the data directory")
    with open(adjusted_path, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/read")
async def read_file(path: str = Query(..., description="Path to file under /data to read")):
    try:
        content = safe_read_file(path)
        return PlainTextResponse(content, status_code=200)
    except Exception:
        raise HTTPException(status_code=404, detail="File not found.")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)