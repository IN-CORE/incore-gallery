import os
import requests
from zipfile import ZipFile
from io import BytesIO
import shutil
import yaml
import sys
from contextlib import contextmanager

ZENODO_API_URL = "https://zenodo.org/api/records"
VERBOSE = False  # Set to True to enable detailed print statements


@contextmanager
def silent_stdout():
    """Context manager to suppress stdout and stderr output."""
    with open(os.devnull, 'w') as fnull:
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = fnull
        sys.stderr = fnull
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
    else:
        if filename is None:
            filename = url.split('/')[-1]
        file_path = os.path.join(dest_folder, filename)
        with open(file_path, 'wb') as file:
            file.write(response.content)
        if VERBOSE:
            print(f"Downloaded file from {url} to {file_path}")
        return file_path


def extract_notebooks(source_folder, dest_folder, template_folder=None):
    for root, dirs, files in os.walk(source_folder):
        for file in files:
            if file.endswith('.ipynb') or file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                source_path = os.path.join(root, file)
                relative_path = os.path.relpath(source_path, source_folder)
                dest_path = os.path.join(dest_folder, relative_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy2(source_path, dest_path)
                if VERBOSE:
                    print(f"Copied file: {dest_path}")

    # TODO: setup a volume.md file for each volume; currently copying existing volume1.md file
    src = os.path.join(template_folder, "volumes", "volume1", "volume1.md")
    dst = os.path.join(dest_folder, "volume1.md")
    shutil.copyfile(src, dst)

def create_intro_file(book_folder, template_folder):
    intro_path = os.path.join(book_folder, "intro.md")
    intro_template = os.path.join(template_folder, "intro.md")
    
    shutil.copyfile(intro_template, intro_path)

    if VERBOSE:
        print(f"Created intro file at: {intro_path}")

"""
copies images folder from template to 'generated_book_files/'
These images are just the incore logo, incore gallery logo, etc.
Images that appear in main jupyter book
"""
def copy_images_folder(book_folder, template_folder):
    template_images_path = os.path.join(template_folder, "images")
    book_images_path = os.path.join(book_folder, "images")
    shutil.copytree(template_images_path, book_images_path, dirs_exist_ok=True)

"""
copies the submission guidelines and process markdown files to 'generated_book_files/'
"""
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

def create_toc_file(notebook_files, notebooks_folder, book_folder, template_folder, volume_num):
    toc_template_path = os.path.join(template_folder, "_toc.yml")
    with open(toc_template_path, 'r') as toc_file:
        toc_content = yaml.safe_load(toc_file)

    # TODO: clean this up; need to figure out how to organize volumes in submissions
    toc_content["parts"][1]["chapters"][0]["sections"] = [
            {"file": f"volumes/volume{volume_num}/{os.path.relpath(nb, notebooks_folder).replace(os.sep, '/')}"}
            for nb in notebook_files
        ]

    toc_path = os.path.join(book_folder, '_toc.yml')
    with open(toc_path, 'w') as toc_file:
        yaml.dump(toc_content, toc_file)
    if VERBOSE:
        print(f"Created TOC file at: {toc_path}")

def create_jupyter_book(source_folder, book_folder, template_folder, volume_num=1):
    if not os.path.exists(book_folder):
        os.system(f'jupyter-book create {book_folder}')
    notebooks_folder = os.path.join(book_folder, 'volumes', 'volume{}' .format(volume_num))      # TODO need to figure out how to hand different volumes
    os.makedirs(notebooks_folder, exist_ok=True)

    extract_notebooks(source_folder, notebooks_folder, template_folder)
    create_intro_file(book_folder, template_folder)         # TODO: need to revisit this
    copy_images_folder(book_folder, template_folder)
    copy_submission_guidelines(book_folder, template_folder)
    create_config_file(book_folder, template_folder)

    notebook_files = [os.path.join(dp, f) for dp, dn, fn in os.walk(notebooks_folder) for f in fn if
                      f.endswith('.ipynb')]

    if not notebook_files:
        print(f"Downloaded files: {os.listdir(source_folder)}")
        raise RuntimeError("No Jupyter notebooks found in the source folder.")

    create_toc_file(notebook_files, notebooks_folder, book_folder, template_folder, volume_num=1)

    build_cmd = f'jupyter-book build {book_folder}'
    if VERBOSE:
        os.system(build_cmd)
    else:
        with silent_stdout():
            os.system(build_cmd)

    print(f'Jupyter Book built at: {book_folder}')


def main(query, community, dest_folder='downloads', book_folder='generated_book_files', template_folder="template", volume_num=1):
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
    if not os.path.exists(book_folder):
        os.makedirs(book_folder)

    results = search_zenodo(query, community)
    if VERBOSE:
        print("Zenodo API Response:")
        print(results)

    for record in results['hits']['hits']:
        files = record['files']
        for file in files:
            file_key = file['key']
            file_url = file['links']['self']
            if VERBOSE:
                print(f"Processing file: {file_url}")
                print(f"File size: {file.get('size', 'N/A')}, File key: {file_key}")
            downloaded_file = download_file(file_url, dest_folder, filename=file_key)
            if downloaded_file and downloaded_file.endswith('.ipynb'):
                notebook_dest_path = os.path.join(book_folder, 'volumes', "volume{}" .format(volume_num), os.path.basename(downloaded_file))
                os.makedirs(os.path.dirname(notebook_dest_path), exist_ok=True)  # Ensure directory exists
                shutil.copy2(downloaded_file, notebook_dest_path)
                if VERBOSE:
                    print(f"Copied notebook to: {notebook_dest_path}")

    create_jupyter_book(dest_folder, book_folder, template_folder)
    print(f'Jupyter Book created at {book_folder}')


if __name__ == "__main__":
    query = ""  # Your search query
    community = "in-core"  # Zenodo community ID
    main(query, community, volume_num=1)
