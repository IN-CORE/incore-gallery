import os
import requests
from zipfile import ZipFile
from io import BytesIO
import shutil
import yaml
import sys
from contextlib import contextmanager
import nbformat

ZENODO_API_URL = "https://zenodo.org/api/records"
VERBOSE = False  # Set to True to enable detailed print statements


@contextmanager
def silent_stdout():
    """Context manager to suppress stdout and stderr output."""
    with open(os.devnull, 'w') as fnull, open(os.devnull, 'w') as enull:
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = fnull
        sys.stderr = enull
        try:
            yield
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr


def search_zenodo(query, community, page=1):
    params = {
        'q': query,
        'communities': community,
        'page': page,
        'size': 10,
        'sort': 'mostrecent'
    }
    response = requests.get(ZENODO_API_URL, params=params)
    response.raise_for_status()
    return response.json()


def download_file(url, dest_folder, filename=None):
    response = requests.get(url)
    response.raise_for_status()

    if 'zip' in url:
        with ZipFile(BytesIO(response.content)) as zip_file:
            zip_file.extractall(dest_folder)
        if VERBOSE:
            print(f"Extracted ZIP file from {url} to {dest_folder}")
        return dest_folder
    else:
        if filename is None:
            filename = url.split('/')[-1]
        file_path = os.path.join(dest_folder, filename)
        with open(file_path, 'wb') as file:
            file.write(response.content)
        if VERBOSE:
            print(f"Downloaded file from {url} to {file_path}")
        return file_path


def extract_notebooks(source_folder, dest_folder):
    for root, dirs, files in os.walk(source_folder):
        for file in files:
            if file.endswith('.ipynb') or file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                source_path = os.path.join(root, file)
                relative_path = os.path.relpath(source_path, source_folder)
                dest_path = os.path.join(dest_folder, relative_path)
                if os.path.abspath(source_path) != os.path.abspath(dest_path):
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    shutil.copy2(source_path, dest_path)
                    if VERBOSE:
                        print(f"Copied file: {dest_path}")


def add_original_url_to_notebook(notebook_path, original_url):
    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = nbformat.read(f, as_version=4)

    # Add a markdown cell with the original URL at the beginning
    markdown_cell = nbformat.v4.new_markdown_cell(
        f'<a href="{original_url}" target="_blank">View Original Notebook</a>')
    nb.cells.insert(0, markdown_cell)

    with open(notebook_path, 'w', encoding='utf-8') as f:
        nbformat.write(nb, f)

    if VERBOSE:
        print(f"Added original URL to notebook: {notebook_path}")


def create_intro_file(book_folder, template_folder):
    intro_path = os.path.join(book_folder, "intro.md")
    intro_template = os.path.join(template_folder, "intro.md")

    shutil.copyfile(intro_template, intro_path)

    if VERBOSE:
        print(f"Created intro file at: {intro_path}")


def copy_images_folder(book_folder, template_folder):
    template_images_path = os.path.join(template_folder, "images")
    book_images_path = os.path.join(book_folder, "images")
    shutil.copytree(template_images_path, book_images_path, dirs_exist_ok=True)


def copy_submission_guidelines(book_folder, template_folder):
    template_submission_path = os.path.join(template_folder, "submission.md")
    book_submission_path = os.path.join(book_folder, "submission.md")
    shutil.copy(template_submission_path, book_submission_path)


def create_config_file(book_folder, template_folder):
    config_template_path = os.path.join(template_folder, "_config.yml")
    with open(config_template_path, 'r') as config_file:
        config_content = yaml.safe_load(config_file)

    config_path = os.path.join(book_folder, '_config.yml')
    with open(config_path, 'w') as config_file:
        yaml.dump(config_content, config_file)
    if VERBOSE:
        print(f"Created config file at: {config_path}")


def create_toc_file(notebook_files, notebooks_folder, book_folder, template_folder):
    toc_template_path = os.path.join(template_folder, "_toc.yml")
    with open(toc_template_path, 'r') as toc_file:
        toc_content = yaml.safe_load(toc_file)

    toc_content["parts"][1]["chapters"] = [
        {"file": f"notebooks/{os.path.relpath(nb, notebooks_folder).replace(os.sep, '/')}"}
        for nb in notebook_files
    ]

    toc_path = os.path.join(book_folder, '_toc.yml')
    with open(toc_path, 'w') as toc_file:
        yaml.dump(toc_content, toc_file)
    if VERBOSE:
        print(f"Created TOC file at: {toc_path}")


def create_jupyter_book(source_folder, book_folder, template_folder):
    if not os.path.exists(book_folder):
        os.system(f'jupyter-book create {book_folder}')
    notebooks_folder = os.path.join(book_folder, 'notebooks')
    os.makedirs(notebooks_folder, exist_ok=True)

    # extract_notebooks(source_folder, notebooks_folder)
    create_intro_file(book_folder, template_folder)
    copy_images_folder(book_folder, template_folder)
    copy_submission_guidelines(book_folder, template_folder)
    create_config_file(book_folder, template_folder)

    notebook_files = [os.path.join(dp, f) for dp, dn, fn in os.walk(notebooks_folder) for f in fn if
                      f.endswith('.ipynb')]

    if not notebook_files:
        raise RuntimeError("No Jupyter notebooks found in the source folder.")

    create_toc_file(notebook_files, notebooks_folder, book_folder, template_folder)

    build_cmd = f'jupyter-book build {book_folder}'
    if VERBOSE:
        os.system(build_cmd)
    else:
        with silent_stdout():
            os.system(build_cmd)

    print(f'Jupyter Book built at: {book_folder}')


def main(query, community, dest_folder='downloads', book_folder='generated_book_files', template_folder="template"):
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
    if not os.path.exists(book_folder):
        os.makedirs(book_folder)

    results = search_zenodo(query, community)
    if VERBOSE:
        print("Zenodo API Response:")
        print(results)

    processed_notebooks = set()

    for record in results['hits']['hits']:
        files = record['files']
        original_url = record['links'].get('doi', record['links'].get('html', 'URL not available'))
        for file in files:
            file_key = file['key']
            file_url = file['links']['self']
            if VERBOSE:
                print(f"Processing file: {file_url}")
                print(f"File size: {file.get('size', 'N/A')}, File key: {file_key}")
            downloaded_file = download_file(file_url, dest_folder, filename=file_key)
            if downloaded_file and downloaded_file.endswith('.ipynb'):
                notebook_dest_path = os.path.join(book_folder, 'notebooks', file_key)
                os.makedirs(os.path.dirname(notebook_dest_path), exist_ok=True)  # Ensure directory exists
                if notebook_dest_path not in processed_notebooks:
                    shutil.copy2(downloaded_file, notebook_dest_path)
                    add_original_url_to_notebook(notebook_dest_path, original_url)
                    processed_notebooks.add(notebook_dest_path)
            elif 'zip' in file_url:
                zip_folder = os.path.join(dest_folder, file_key.replace('.zip', ''))
                # extract_notebooks(downloaded_file, zip_folder)
                for root, dirs, files in os.walk(zip_folder):
                    for file in files:
                        if file.endswith('.ipynb'):
                            notebook_dest_path = os.path.join(book_folder, 'notebooks', file)
                            extracted_notebook_path = os.path.join(zip_folder, file)
                            os.makedirs(os.path.dirname(notebook_dest_path), exist_ok=True)  # Ensure directory exists
                            if notebook_dest_path not in processed_notebooks:
                                shutil.copy2(extracted_notebook_path, notebook_dest_path)
                                add_original_url_to_notebook(notebook_dest_path, original_url)
                                processed_notebooks.add(notebook_dest_path)

    create_jupyter_book(book_folder, book_folder, template_folder)

    # Clean up downloads folder
    shutil.rmtree(dest_folder)
    os.makedirs(dest_folder)

    print(f'Jupyter Book created at {book_folder}')


if __name__ == "__main__":
    query = ""  # Your search query
    community = "in-core"  # Zenodo community ID
    main(query, community)
