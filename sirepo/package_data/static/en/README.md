# Overview

This is the repository for the Sirepo landing pages developed by Vermilion.

The external libraries mirror what's used on the main Sirepo repository, including `Bootstrap 3.3.7`, and `jQuery 2.2.4`.

One additional library, `Showdown 1.9.0` is included for client side markdown conversion.

The CSS is compiled using Sass.

The site should run with no server dependencies besides having a server that is able to serve the files included.

## Articles JSON/Markdown format

The news articles are pulled into the landing page using a simple JSON/Markdown format. First, the page looks for the `/news/article-index.json` file for a the JSON definition of the article start date, end date, and location of the Markdown file.

Each Markdown file is then pulled from the server and parsed into HTML for display on the front end.

The format of the JSON file is as follows:

```
[
  {
    "start_date": "2019/05/01",
    "end_date": "2020/05/01",
    "markdown_file": "article1.md"
  },
  {
    "markdown_file": "article2.md"
  }
]
```

The JSON specifies an array of article objects. The articles will be displayed in the order that they are specified in the array.

The `start_date` and `end_date` are optional, and should be in `YYYY-MM-DD` format. The `markdown_file` is required, and specifies the Markdown file to be used for that article

The `start_date` indicates the first day that the article will be displayed. If `start_date` is omitted, then the article will always be shown if the `end_date` has not passed.

The `end_date` indicates the last day that the article will be displayed. If `end_date` is omitted, then the article will always be shown if the `start_date` has passed.

The `markdown_file` specifies the Markdown file containing. the article content. The Markdown files should be alongside the `/news/article-index.json` file in the `news` directory.