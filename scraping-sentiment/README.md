# Selenium Scraping and Sentiment Analysis

This folder is the old workshop: wires on the table, tools everywhere, some working parts, some abandoned parts, and a clear record of how the project started.

It was the first attempt, it required a lot of manual labor, and it was effectively abandoned halfway through once it became obvious how brittle and costly the scraping-heavy approach was.

The basic idea was straightforward:

- scrape articles from Slovenian news sites with Selenium
- pull out the text
- run lightweight sentiment analysis
- see which parties the outlet seemed friendliest or coldest toward

In theory, that sounds practical. In practice, it means HTML quirks, broken selectors, dynamic pages, translation noise, and a lot of manual intervention.

## What Is In Here

- [`24ur`](24ur/): the most developed subfolder in this approach, with URL lists and output plots
- [`nova24tv`](nova24tv/): early scraping files for Nova24
- [`all.py`](all.py): older orchestration script
- [`mediji.txt`](mediji.txt), [`neki.txt`](neki.txt): working notes and source lists
- [`geckodriver`](geckodriver): Firefox driver binary kept with the project

## What Was Actually Analyzed

This part of the repo never became a clean broad study of all outlets.

The main concrete work appears to be around `24ur`, where the folder includes output images such as:

- [`24ur_sent1.png`](24ur/24ur_sent1.png)
- [`24ur_sent1_300.png`](24ur/24ur_sent1_300.png)
- [`24ur_sent1_outliers.png`](24ur/24ur_sent1_outliers.png)
- [`24ur_sub2.png`](24ur/24ur_sub2.png)

There is also early groundwork for `nova24tv`, but this approach mostly remained a prototype rather than a finished comparative dataset.

## Running It

The code expects Selenium and `geckodriver`.

The old note in this folder still applies: `geckodriver` needs to be on `PATH`.

Example:

```console
export PATH=$PATH:/path/to/repository/unbalanced-media/
```

Realistically, if you try to run this today, expect to patch selectors, paths, and maybe the whole workflow. This is not a polished package. It is a working notebook in code form.

## What This Approach Was Good At

- getting raw article text directly from the sites
- showing very early sentiment plots
- forcing the project to confront the data-collection problem first

## What It Was Bad At

- reliability
- scale
- portability
- keeping the scraping logic alive across site changes

That is why this folder is still valuable mainly as evidence of the project’s first phase: before the LLM prompt engineering, before EventRegistry, when the problem was still being attacked with a browser driver and stubbornness.
