# Starful | Visual Career Grid Platform

**Starful** is a modern career grid platform designed for users to visually explore and discover various job paths. It uses a Bento UI design to provide an intuitive and attractive browsing experience.

## 🚀 Key Features

-   **Dynamic Content**: The entire site is managed through Markdown files, making it easy to add or update career categories and job descriptions without touching the code.
-   **Three-Tier Navigation**: A clear user flow from broad categories to specific job listings and then to detailed information pages.
-   **Bento UI Design**: A modern grid layout that presents information in a clean, visual manner.
-   **Responsive Web**: Optimized for all devices, including desktops, tablets, and mobile phones.
-   **Fast & Lightweight**: Built with a FastAPI backend for high performance.

## 🛠 Tech Stack

-   **Backend**: Python, FastAPI
-   **Frontend**: Jinja2 Templates, HTML5, CSS3
-   **Content Management**: Markdown with YAML Frontmatter

## 💻 Local Development

1.  **Clone the repository**
    ```bash
    git clone [your-repository-url]
    cd starful-project
    ```

2.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the Server**
    ```bash
    uvicorn app.main:app --reload
    ```
    Visit `http://127.0.0.1:8000` in your browser.

## 📂 Content Management

-   To **add or edit a main category card** on the home page, modify the `.md` files in the `app/categories/` directory.
-   To **add or edit a career detail page**, create or modify a `.md` file in the `app/contents/` directory. Make sure to set the `category` field correctly to link it to a main category.