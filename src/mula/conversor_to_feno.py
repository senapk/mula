import os
import argparse
import subprocess
import re
from pathlib import Path

project_path = Path(__file__).resolve().parent

def convert_and_rename(folder_path):
    index_html_path = os.path.join(folder_path, "q.html")
    readme_md_path = os.path.join(folder_path, "Readme.md")
    vpl_cases_path = os.path.join(folder_path, "vpl_evaluate.cases")
    q_tio_path = os.path.join(folder_path, "q.tio")
    
    if os.path.exists(index_html_path):
        try:
            subprocess.run(["pandoc", index_html_path,f"--lua-filter={project_path}/line-break.lua", "--wrap=none", "--to=markdown", "-o", readme_md_path], check=True)
            
            with open(readme_md_path, "r", encoding="utf-8") as md_file:
                markdown_content = md_file.read()
            
            # Replace ::: {.language-xxx .highlight} pattern with ```xxx and remove extra spaces
            def replace_code_block(match):
                language = match.group(1)
                content = match.group(2)
                lines = content.split('\n')
                cleaned_lines = []
                for line in lines:
                    if line.startswith('    '):
                        cleaned_lines.append(line[4:])
                    else:
                        cleaned_lines.append(line)
                cleaned_content = '\n'.join(cleaned_lines)
                return f"```{language}\n{cleaned_content}\n```"
            
            # Use regex to find and replace code blocks
            pattern = r"::: \{\.language-(\w+) \.highlight\}\n(.*?)\n:::"
            markdown_content = re.sub(pattern, replace_code_block, markdown_content, flags=re.DOTALL)
            
            with open(readme_md_path, "w", encoding="utf-8") as md_file:
                md_file.write(markdown_content)
            
            print(f"Converted {index_html_path} to {readme_md_path} using pandoc")
        except subprocess.CalledProcessError:
            print("Error: pandoc command failed. Make sure pandoc is installed.")
        except FileNotFoundError:
            print("Error: pandoc not found. Please install pandoc.")
    else:
        print(f"{index_html_path} does not exist.")

    # Check if vpl_evaluate.cases exists
    if os.path.exists(vpl_cases_path):
        # Rename vpl_evaluate.cases to q.tio
        os.rename(vpl_cases_path, q_tio_path)
        print(f"Renamed {vpl_cases_path} to {q_tio_path}")
    elif os.path.exists(q_tio_path):
        print(f"q.tio already exists.")
    else:
        print(f"{vpl_cases_path} does not exist.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert and rename files in a folder.")
    parser.add_argument("--path", required=True, help="Path to the folder containing the files.")
    args = parser.parse_args()

    convert_and_rename(args.path)
