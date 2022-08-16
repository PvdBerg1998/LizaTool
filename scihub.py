# MIT License
#
# Copyright (c) 2022 Pim van den Berg
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from io import StringIO
import requests as req
from bs4 import BeautifulSoup
from sanitize_filename import sanitize
import re
import csv
from os import path
from datetime import datetime

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

            #pdf_filename = re.sub("\s", "_", f"{sanitize(title)}.pdf")
            first_author = article["authors"].split(",")[0]
            pdf_filename = f'{first_author} {article["year"]}.pdf'

            # prevent collisions
            if path.exists(pdf_filename):
                pdf_filename = f'{first_author} {article["year"]} {datetime.now().timestamp()}.pdf'

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
