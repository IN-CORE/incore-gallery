import os
import requests
import shutil
import yaml
import sys
from zipfile import ZipFile
from io import BytesIO
from contextlib import contextmanager
import nbformat
import json

ZENODO_API_URL = "https://zenodo.org/api/records"
VERBOSE = False  # Set to True for detailed logs


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
    """Search Zenodo for records."""
    params = {'q': query, 'communities': community, 'page': page, 'size': 10, 'sort': 'mostrecent'}
    response = requests.get(ZENODO_API_URL, params=params)
    response.raise_for_status()
    return response.json()


def download_file(url, dest_folder, filename=None):
    response = requests.get(url)
    response.raise_for_status()

    if 'zip' in url:
        with ZipFile(BytesIO(response.content)) as zip_file:
            zip_file.extractall(dest_folder)

        # Cleanup __MACOSX and .DS_Store
        macosx_folder = os.path.join(dest_folder, "__MACOSX")
        if os.path.exists(macosx_folder):
            shutil.rmtree(macosx_folder)

        for root, _, files in os.walk(dest_folder):
            for file in files:
                if file == ".DS_Store":
                    os.remove(os.path.join(root, file))

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


def add_original_url_to_notebook(notebook_path, original_url):
    """Insert a markdown cell with the original URL in a notebook."""
    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = nbformat.read(f, as_version=4)

    markdown_cell = nbformat.v4.new_markdown_cell(
        f'<a href="{original_url}" target="_blank">View Original Notebook</a>')
    nb.cells.insert(0, markdown_cell)

    with open(notebook_path, 'w', encoding='utf-8') as f:
        nbformat.write(nb, f)

    if VERBOSE:
        print(f"Added original URL to notebook: {notebook_path}")


def copy_templates(book_folder, template_folder):
    """Copy the entire content of template_folder to book_folder."""
    if not os.path.exists(template_folder):
        raise FileNotFoundError(f"Template folder '{template_folder}' does not exist.")

    shutil.copytree(template_folder, book_folder, dirs_exist_ok=True)

    if VERBOSE:
        print(f"Copied contents of {template_folder} to {book_folder}")


def copy_downloaded_notebooks(book_folder, download_folder):
    """Copy downloaded notebooks into book folder while preserving structure."""
    if not os.path.exists(download_folder):
        raise FileNotFoundError(f"Zenodo download folder '{download_folder}' does not exist.")

    shutil.copytree(download_folder, book_folder, dirs_exist_ok=True)

    if VERBOSE:
        print(f"Copied contents of {download_folder} to {book_folder}")


def create_placeholder_md(folder_path, root_files, base_path):
    """Creates a markdown file with links to each root file's first cell title."""
    folder_name = os.path.basename(folder_path)
    placeholder_md_path = os.path.join(folder_path, f"{folder_name}.md")
    links = []

    for file in root_files:
        file_path = os.path.join(base_path, file)
        if file.endswith('.ipynb'):
            title = get_ipynb_file_title(file_path)
        elif file.endswith('.md'):
            title = get_md_file_title(file_path)
        else:
            title = os.path.basename(file).replace("_", " ").title()
        links.append(f"- [{title}]({os.path.basename(file_path)})")

    with open(placeholder_md_path, 'w', encoding='utf-8') as f:
        f.write(f"# {folder_name.title()}\n\n")
        f.write("## Contents\n\n")
        f.write("\n".join(links) + "\n")

    return os.path.relpath(placeholder_md_path, base_path).replace(os.sep, '/')


def process_path(item_path, base_path):
    """Recursively process a file or folder and return a structured TOC entry."""
    if os.path.basename(item_path).startswith('.'):
        return None  # Ignore hidden files and folders

    if os.path.isfile(item_path) and (item_path.endswith('.md') or item_path.endswith('.ipynb')):
        # Return file path relative to base path
        rel_path = os.path.relpath(item_path, base_path).replace(os.sep, '/')
        return {"file": rel_path}

    elif os.path.isdir(item_path):
        # Process folder recursively
        root_files = []
        folder_sections = []

        for item in sorted(os.listdir(item_path)):
            sub_item_path = os.path.join(item_path, item)

            if os.path.isfile(sub_item_path) and (item.endswith('.md') or item.endswith('.ipynb')):
                # Collect potential root files
                root_files.append(os.path.relpath(sub_item_path, base_path).replace(os.sep, '/'))
            else:
                sub_entry = process_path(sub_item_path, base_path)
                if sub_entry:
                    folder_sections.append(sub_entry)

        # Decide how to structure the folder entry
        if len(root_files) == 1:
            # If exactly one root file, use it as the "file" and append sections
            return {"file": root_files[0], "sections": folder_sections} if folder_sections else {"file": root_files[0]}
        elif len(root_files) > 1:
            # If multiple root files, create a placeholder markdown file with links
            placeholder_md = create_placeholder_md(item_path, root_files, base_path)
            return {"file": placeholder_md, "sections": [{"file": root} for root in root_files]}
        else:
            # No root files, just return sections (if any)
            return folder_sections if folder_sections else None

    return None  # Ignore empty directories or non-md/ipynb files


def create_toc_file(book_folder, index):
    """Dynamically create a TOC by walking through index values (files/folders)."""

    toc_path = os.path.join(book_folder, "_toc.yml")

    # Load existing TOC or start fresh
    if os.path.exists(toc_path):
        with open(toc_path, 'r') as toc_file:
            toc_structure = yaml.safe_load(toc_file)
    else:
        toc_structure = {
            "format": "jb-book",
            "root": "intro",
            "parts": [
                {"caption": "Submit", "chapters": [{"file": "submission.md"}]},
                {"caption": "Published Notebooks", "chapters": []}
            ]
        }

    if toc_structure["parts"][1]["chapters"] is None:
        toc_structure["parts"][1]["chapters"] = []
    published_notebooks_section = toc_structure["parts"][1]["chapters"]

    for category, items in index.items():
        category_sections = []
        for item in items:
            item_path = os.path.join(book_folder, item)
            section_entry = process_path(item_path, book_folder)
            if section_entry:
                category_sections.append(section_entry)

        if category_sections:
            published_notebooks_section.append({"file": f"{category}.md", "sections": category_sections})

    # Write updated TOC file
    with open(toc_path, 'w') as toc_file:
        yaml.dump(toc_structure, toc_file, default_flow_style=False, sort_keys=False)

    if VERBOSE:
        print(f"Updated TOC file at: {toc_path}")


def get_ipynb_file_title(file_path):
    """Extracts the title from a Jupyter Notebook or Markdown file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            notebook_data = json.load(f)
        # Find the first markdown cell with a heading
        for cell in notebook_data.get("cells", []):
            if cell.get("cell_type") == "markdown" and cell.get("source"):
                first_line = cell["source"][0].strip()
                if first_line.startswith("#"):  # Looks like a title
                    return first_line.lstrip("#").strip()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")

    # Fallback to filename if no title is found
    return os.path.basename(file_path).replace(".ipynb", "")


def get_md_file_title(file_path):
    """Extracts the title from a Jupyter Notebook or Markdown file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith("#"):  # First heading is the title
                    return line.lstrip("#").strip()

    except Exception as e:
        print(f"Error reading file {file_path}: {e}")

    # Fallback to filename if no title is found
    return os.path.basename(file_path).replace(".md", "").replace("_", " ").title()


def update_category_md_files(book_folder, index, toc_file="_toc.yml"):
    """Reads TOC and updates workshops.md, notebooks.md, and tutorials.md with child links."""

    toc_path = os.path.join(book_folder, toc_file)

    if not os.path.exists(toc_path):
        print(f"TOC file not found: {toc_path}")
        return

    # Load TOC YAML
    with open(toc_path, 'r', encoding='utf-8') as f:
        toc_data = yaml.safe_load(f)

    # Dynamically create categories from index keys
    category_links = {category: [] for category in index.keys()}

    for part in toc_data.get("parts", []):
        for chapter in part.get("chapters", []):
            category_file = chapter.get("file", "").replace(".md", "")
            if category_file in category_links:  # Match category file
                for section in chapter.get("sections", []):
                    section_file = section["file"]
                    if section_file.endswith(".md"):
                        section_title = get_md_file_title(os.path.join(book_folder, section_file))
                    elif section_file.endswith(".ipynb"):
                        section_title = get_ipynb_file_title(os.path.join(book_folder, section_file))
                    else:
                        # fallback to just use filename
                        section_title = os.path.basename(section_file).split(".")[0]
                    category_links[category_file].append(f"- [{section_title}]({section_file})")

    # Insert links into category .md files
    for category, links in category_links.items():
        category_md_path = os.path.join(book_folder, f"{category}.md")

        if not os.path.exists(category_md_path):
            continue  # Skip if the file doesn't exist

        with open(category_md_path, 'w', encoding='utf-8') as f:
            f.write(f"# {category.title()}\n\n")
            f.write("## Contents\n\n")
            if links:
                f.write("\n".join(links) + "\n")
            else:
                f.write("_No content available._\n")

        print(f"Updated {category_md_path} with links to child sections.")


def create_jupyter_book(book_folder, index):
    """Build the Jupyter Book using the dynamically created TOC."""
    create_toc_file(book_folder, index)
    update_category_md_files(book_folder, index, toc_file="_toc.yml")

    build_cmd = f'jupyter-book build {book_folder}'
    if VERBOSE:
        os.system(build_cmd)
    else:
        with silent_stdout():
            os.system(build_cmd)

    print(f'Jupyter Book built at: {book_folder}')


def main(query, community, download_folder='downloads', book_folder='generated_book_files', template_folder="template"):
    """Main function to handle Zenodo data download and book creation."""
    os.makedirs(download_folder, exist_ok=True)

    if os.path.exists(book_folder):
        print(f"🔄 Rebuilding: Removing existing '{book_folder}'...")
        shutil.rmtree(book_folder)  # Deletes the book folder
    os.makedirs(book_folder, exist_ok=False)

    results = search_zenodo(query, community)
    index = {"workshops": [], "tutorials": [], "notebooks": []}

    for record in results['hits']['hits']:
        metadata = record.get("metadata", {})
        original_url = metadata.get("doi", metadata.get("html", "URL not available"))

        for file in record['files']:
            file_url = file['links']['self']
            file_key = file['key']
            fname = file_key[:-4] if file_key.lower().endswith('.zip') else file_key
            downloaded_fname = download_file(file_url, download_folder, filename=fname)
            keywords = metadata.get('keywords', [])

            # Determine category based on keywords
            if 'workshop' in keywords:
                index['workshops'].append(fname)
            elif 'tutorial' in keywords:
                index['tutorials'].append(fname)
            else:
                index['notebooks'].append(fname)

            # Add original URL to notebooks
            if downloaded_fname.endswith('.ipynb'):
                add_original_url_to_notebook(downloaded_fname, original_url)

    # Copy everything to book folder
    copy_templates(book_folder, template_folder)
    copy_downloaded_notebooks(book_folder, download_folder)

    # Create and build Jupyter Book
    create_jupyter_book(book_folder, index)

    # Cleanup downloads
    shutil.rmtree(download_folder)

    # print the location of the generated book
    print(f'Jupyter Book created at {book_folder}')


if __name__ == "__main__":
    query = ""  # Your search query
    community = "in-core"
    main(query, community)
