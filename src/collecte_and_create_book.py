import os
import requests
from zipfile import ZipFile
from io import BytesIO
import shutil
import yaml

ZENODO_API_URL = "https://zenodo.org/api/records"


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


def download_file(url, dest_folder):
    response = requests.get(url)
    response.raise_for_status()

    if 'zip' in url:
        with ZipFile(BytesIO(response.content)) as zip_file:
            zip_file.extractall(dest_folder)
    else:
        file_name = os.path.join(dest_folder, url.split('/')[-1])
        with open(file_name, 'wb') as file:
            file.write(response.content)


def extract_notebooks(source_folder, dest_folder):
    for root, dirs, files in os.walk(source_folder):
        for file in files:
            if file.endswith('.ipynb'):
                source_path = os.path.join(root, file)
                relative_path = os.path.relpath(source_path, source_folder)
                dest_path = os.path.join(dest_folder, relative_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy2(source_path, dest_path)
                print(f"Copied notebook: {dest_path}")


def create_intro_file(notebooks_folder):
    intro_path = os.path.join(notebooks_folder, 'intro.md')
    with open(intro_path, 'w') as f:
        f.write("# Welcome to My Jupyter Book\n\nThis is the introduction.")
    print(f"Created intro file at: {intro_path}")


def create_config_file(book_folder):
    config_content = {
        "execute": {
            "execute_notebooks": "off"
        }
    }
    config_path = os.path.join(book_folder, '_config.yml')
    with open(config_path, 'w') as config_file:
        yaml.dump(config_content, config_file)
    print(f"Created config file at: {config_path}")


def create_jupyter_book(source_folder, book_folder):
    if not os.path.exists(book_folder):
        os.system(f'jupyter-book create {book_folder}')
    notebooks_folder = os.path.join(book_folder, 'notebooks')
    os.makedirs(notebooks_folder, exist_ok=True)

    extract_notebooks(source_folder, notebooks_folder)
    create_intro_file(notebooks_folder)
    create_config_file(book_folder)

    notebook_files = [os.path.join(dp, f) for dp, dn, fn in os.walk(notebooks_folder) for f in fn if
                      f.endswith('.ipynb')]

    if not notebook_files:
        print(f"Downloaded files: {os.listdir(source_folder)}")
        raise RuntimeError("No Jupyter notebooks found in the source folder.")

    # Create a minimal Table of Contents file
    toc_content = {
        "format": "jb-book",
        "root": "notebooks/intro",
        "chapters": [
            {"file": f"notebooks/{os.path.relpath(nb, notebooks_folder).replace(os.sep, '/')}"}
            for nb in notebook_files
        ]
    }
    toc_path = os.path.join(book_folder, '_toc.yml')
    with open(toc_path, 'w') as toc_file:
        yaml.dump(toc_content, toc_file)
    print(f"Created TOC file at: {toc_path}")

    os.system(f'jupyter-book build {book_folder}')
    print(f'Jupyter Book built at: {book_folder}')


def main(query, community, dest_folder='downloads', book_folder='generated_book_files'):
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
    if not os.path.exists(book_folder):
        os.makedirs(book_folder)

    results = search_zenodo(query, community)
    for record in results['hits']['hits']:
        files = record['files']
        for file in files:
            download_file(file['links']['self'], dest_folder)

    create_jupyter_book(dest_folder, book_folder)
    print(f'Jupyter Book created at {book_folder}')


if __name__ == "__main__":
    query = ""  # Your search query
    community = "in-core"  # Zenodo community ID
    main(query, community)
