# Week 1 Recap: Set up and explore

**Dates** Oct 13 to Oct 14, 2026 (finished early)
**Status** Done. CI is green.

## Week 1 in plain words
Think of the project like a restaurant before opening day.

- **Kitchen set up.** I installed Python and made a project folder with a clear place for everything (data, code, notes, tests).
- **Ingredients delivered.** I downloaded every event from the 2015/16 Premier League from StatsBomb. That is about 1.3 million moments like passes, shots and tackles from 380 matches.
- **First dish cooked.** I built a first **xG model**. xG (expected goals) gives every shot a number from 0 to 1 for how likely it was to be a goal. A tap-in might be 0.7. A shot from 30 metres might be 0.03.
- **Taste test.** I compared my model with StatsBomb's professional xG. Mine beats a simple "distance only" guess but is not as good as theirs yet. That is expected for week 1.
- **Opened the doors.** I put the code on GitHub, where anyone can see it. GitHub now runs automatic checks (CI) every time I push, like a health inspector checking the kitchen each time.

## What I finished
- [x] Installed Python 3.12 and set up a virtual environment (a private box of libraries just for this project)
- [x] Downloaded Premier League 2015/16 event data (1,313,773 events, 380 matches)
- [x] Made an exploration notebook with a shot map, a pass map and a calibration chart
- [x] Trained the first xG model and printed its report
- [x] Pushed to a public GitHub repo with green CI

## Results
| Model | Log loss (lower is better) | AUC (higher is better) |
| --- | --- | --- |
| Distance-only guess | 0.2962 | |
| My model | 0.2859 | 0.742 |
| StatsBomb xG | 0.2669 | 0.792 |

**Sanity check.** Jamie Vardy had 17.6 xG without penalties and scored 19 goals without penalties. That matches his real 24 goals minus 5 penalties, so the data is right.

## What went wrong and how we fixed it
| # | Problem | What happened | Fix | Lesson |
| --- | --- | --- | --- | --- |
| 1 | GitHub blocked the download | Downloading 380 matches too fast got "429 Too Many Requests" | 4 downloads at a time instead of 8, plus wait and retry | Be polite to free data sources and always add retries |
| 2 | Data would not save | Some columns mixed numbers, text and lists, and parquet needs one kind per column | Coordinates kept as number lists, nested data saved as JSON text, True/False kept as real booleans | Check data types before saving |
| 3 | Data file too big to move | The file was 150 MB | Compressed (zstd) and split into 10 files of about 7 MB, 66 MB total, same results | Small files sync and share more easily |
| 4 | Git did not know who I was | First commit failed with "Author identity unknown" | Set name and email once with `git config --global` | One-time setup on a new laptop |
| 5 | CI failed, lint | Newest ruff flagged the import order in the notebook | Tidied the import and pinned lint rules in `pyproject.toml` | Pin tool settings so CI is predictable |
| 6 | CI failed, tests | `python -m pytest` worked on my laptop, but GitHub runs plain `pytest`, which could not find the `pipeline` folder | Added `pythonpath = ["."]` to `pyproject.toml` and tested on a clean copy first | "Works on my machine" is not enough, that is what CI is for |

## Things I learned
- What xG is and how to check a model against a professional one
- What a virtual environment, a commit, a push and CI are
- How to read an error message and fix one thing at a time

## Interview story from this week
"My CI failed twice on day one. The first was a lint rule change, so I pinned the rules. The second was an import path that worked locally but not on GitHub, so I reproduced it in a clean environment and fixed the test config."

## Next up (Week 2, Oct 20 to Oct 26)
- [ ] Download the other four leagues
- [ ] Add freeze-frame features to xG (where defenders and the keeper are) to close the gap with StatsBomb
- [ ] Build the xT (Expected Threat) grid and draw it as a heatmap
- [ ] Build per 90 player stats (minutes, xG, xA, xT)
- [ ] Write tests for minutes played and per 90 maths
