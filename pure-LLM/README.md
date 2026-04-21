# Author-Party Sentiment Analysis with LLMs

This folder contains the second version of the project: the stage after LLMs became popular and easy enough to use directly for this kind of qualitative analysis. Before that, during the scraping phase, transformer models were not yet capable enough in practice to be the obvious tool for this job.

So this version still has no pipeline, no event matching, and no automation worth bragging about. Just manually collected article text, a prompt, and the question:

what does this outlet sound like when it talks about a party?

It was messy, manual, and surprisingly revealing.

## How It Worked

For each outlet and each party:

- copy a batch of articles by hand
- paste them into ChatGPT
- ask for a sentiment score from `-5` to `+5`
- save the response

The prompt was simple:

> Please analyze the sentiment of the writer towards the Slovenian political party `<party>` and its president `<president>` based on the provided news articles. Focus on the writer's tone, choice of words, and overall portrayal of the party and its members. At the end of your analysis, provide a sentiment score ranging from -5 to +5.

Files:

- [`website-text`](website-text/): manually collected article text
- [`prompt-results.txt`](prompt-results.txt): prompt text and summary table
- [`chatgpt-response.txt`](chatgpt-response.txt): saved model responses

## Results

These are the saved summary scores from [`prompt-results.txt`](prompt-results.txt:18):

| Outlet | SDS | NSi | Svoboda | Levica |
|---|---:|---:|---:|---:|
| `24ur` | `-4` | `+3` | `+4` | `+1` |
| `nova24` | `+4` | `+1` | `-4` | `-4` |
| `rtvslo` | `+4` | `+1` | `-2` | `+2` |

The results are fun because they are bold. They are also a little reckless for exactly the same reason.

### What Jumps Out

- `24ur` comes out strongly negative on `SDS` and strongly positive on `Svoboda`
- `nova24` comes out as the mirror image: positive on `SDS`, negative on `Svoboda` and `Levica`
- `rtvslo` gets the strangest result here, looking positive on `SDS`, which is part of why the later event-based approach became necessary

This experiment was good at catching the big obvious contrasts. It was much weaker at separating outlet tone from article selection effects, because the article batches were assembled manually and each outlet was judged in isolation.

## Why This Folder Is Still Worth Keeping

Because this is the part where the repo first became interesting.

You can open the raw article bundles in [`website-text`](website-text/) and compare them with the saved ChatGPT writeups. It is a compact record of the original intuition behind the project:

if you give a model enough politically charged writing, it will usually notice who the outlet seems to like and who it seems to enjoy kicking.

That does not make these results rigorous. But it does make them worth reading.
