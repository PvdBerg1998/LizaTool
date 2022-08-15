from io import StringIO
import requests as req
from bs4 import BeautifulSoup
from sanitize_filename import sanitize
import re
import csv

# Fix some of the data formatting
with open("artikelen.csv") as f:
    raw = f.read()
    # Remove " at line start
    raw = re.sub("(?m)^\"", "", raw)
    # Replace "" with "
    raw = re.sub("\"\"", "\"", raw)
with open("artikelen_clean.csv", 'w') as f:
    f.write(raw)

# Extract the most important columns
articles = []
with open("artikelen_clean.csv") as f:
    lines = iter(f.readlines())

    #headers = next(lines).strip().rstrip(";").split(",")
    next(lines)
    headers = ["key", "title", "year", "month", "day", "journal", "issn", "volume",
               "issue", "pages", "authors", "url", "language", "publisher", "location"]
    # the rest of the columns are quite a mess so just ignore them
    # print(headers)

    for line in lines:
        pieces = next(csv.reader(StringIO(line),
                      delimiter=",", quotechar="\""))

        article = {}
        for header, piece in zip(headers, pieces):
            piece = piece.rstrip(";")
            subpieces = piece.split("     ")

            subpieces = list(filter(lambda subpiece: len(subpiece) > 0, map(
                lambda subpiece: subpiece.strip().rstrip(";"), subpieces)))

            if len(subpieces) == 1:
                article[header] = subpieces[0]
            elif len(subpieces) > 1:
                article[header] = subpieces
            else:
                article[header] = None

        articles.append(article)

failed = []

for i, article in enumerate(articles):
    print(f"=== {i}/{len(articles)}")

    if len(article["url"]) == 2:
        print(f"""Downloading paper:
            {article["title"]}
            {article["year"]}
            {article["authors"]}
            {article["journal"]}
            {article["url"][1]}
        """)

        doi = article["url"][1]

        try:
            url = f"https://sci-hub.se/{doi}"
            print(f"Loading {url}")

            reply = req.get(url)
            reply.raise_for_status()
            soup = BeautifulSoup(reply.content, 'html.parser')

            if "article not found" in soup.title.string:
                raise Exception("Paper not available")

            title = soup.title.string.split("Sci-Hub | ")[1]
            print(f"Found paper: {title}")

            # print(reply.content)

            download = soup.find(id="article").find(
                id="pdf")["src"].split("#")[0]
            print(f"Extracted PDF location: {download}")

            if download.startswith("/download"):
                pdf_url = f"https://sci-hub.se{download}"
            elif download.startswith("//"):
                pdf_url = f"https:{download}"

            print(f"Downloading {pdf_url}")

            pdf = req.get(pdf_url)
            pdf.raise_for_status()

            pdf_filename = re.sub("\s", "_", f"{sanitize(title)}.pdf")
            with open(pdf_filename, 'wb') as f:
                f.write(pdf.content)

            print(f"Saved as {pdf_filename}")
        except Exception as e:
            print(f"Failed to download paper: {e}")
            failed.append(article)

    else:
        print(f"""Paper is missing the DOI:
            {article["title"]}
            {article["year"]}
            {article["authors"]}
            {article["journal"]}""")
        failed.append(article)

print("===")

with open("artikelen_todo.txt", 'w') as f:
    for fail in failed:
        f.write(f"""{fail["title"]}
            {fail["year"]}
            {fail["authors"]}
            {fail["journal"]}
            {fail["url"]}\n\n""")
