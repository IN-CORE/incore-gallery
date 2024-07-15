# INCORE-Gallery

This repository contains a Python script that uses the Zenodo API to search for Jupyter Notebooks or ZIP files, download them, and create a Jupyter Book.

## Prerequisites

- Python 3.x
- `virtualenv` package

## Setup

### 1. Clone the Repository and Set Up the Virtual Environment

#### On Windows

```sh
git clone https://github.com/IN-CORE/incore-gallery/incore-gallery.git
cd incore-gallery
python -m venv \path\to\incore-gallery\venv
\path\to\incore-gallery\venv\Scripts\activate
pip install -r requirements.txt
```

#### On macOS and Linux

```sh
git clone https://github.com/IN-CORE/incore-gallery/incore-gallery.git
cd incore-gallery
python -m venv /path/to/incore-gallery/venv
source /path/to/incore-gallery/venv/activate
pip install -r requirements.txt
```

## How to Use the Script

### Prerequisites

- Python 3.7 or higher
- All the required dependencies listed in the `requirements.txt` file.

Ensure you have these dependencies installed in your virtual environment. You can install them using:

```sh
pip install requests pyyaml jupyter-book
```

### `collecte_and_create_book.py` Script Usage

1. **Navigate to the Script Directory**: Change directory to the location of the script.

    ```sh
    cd path/to/your/script
    ```

2. **Configure the Script**: Open the script file `collecte_and_create_book.py` and set the following variables at the top of the script:
    - `ZENODO_API_URL`: The base URL for Zenodo API.
    - `VERBOSE`: Set to `True` if you want detailed logs, otherwise set to `False`.

3. **Run the Script**:
    Execute the script with your desired query and community. By default, it will download files to the `downloads` folder and generate the Jupyter Book files in the `generated_book_files` folder. You can run the script using:

    ```sh
    python collecte_and_create_book.py <query> <community>
    ```

    - Replace `<query>` with your search term.
    - Replace `<community>` with the Zenodo community ID.
    - If the `<query>` is empty, the script will scrape all available files in the specified community.

    Example of running the script with a specific query:

    ```sh
    python collecte_and_create_book.py Seaside in-core
    ```

    Example of running the script with an empty query:

    ```sh
    python collecte_and_create_book.py "" in-core
    ```

4. **Open the Generated Book**:
    After the script runs, open the generated book by navigating to the `generated_book_files/_build/html` directory and opening `index.html` in your web browser.

    ```sh
    open generated_book_files/_build/html/index.html
    ```

#### Example Usage

To search for notebooks related to "Seaside" in the "in-core" community and build a Jupyter Book:

```sh
python collecte_and_create_book.py Seaside in-core
```

To scrape all available files in the "in-core" community and build a Jupyter Book:

```sh
python collecte_and_create_book.py "" in-core
```

This will search Zenodo for files, download them, and create a Jupyter Book in the `generated_book_files` directory.

#### Additional Notes

- Ensure you have an active internet connection while running the script as it fetches data from Zenodo.
- Adjust the `VERBOSE` variable as needed to control the amount of log output.

---

This completes the instructions for using the `collecte_and_create_book.py` script. For any issues or contributions, please refer to the repository's issue tracker and contribution guidelines.
