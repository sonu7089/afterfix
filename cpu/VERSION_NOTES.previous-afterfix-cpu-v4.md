# CPU package v4 notes

This local review copy adds the confirmed author, affiliation, no-funding statement, license scope and planned repository name. The current manuscript is [review v6](paper/afterfix-review-v6.md), also provided as a [seven-page PDF](paper/afterfix-final-review-v1.pdf). It has 2,934 whitespace-delimited words and no em dashes. Numerical tables and study numbers are unchanged from v5.

All files from package v3 are unchanged except README, release status, version notes and the source map. The previous versions of those files are retained with `.previous-afterfix-cpu-v3` names. Historical pending-author/license statements are superseded by [current release status](RELEASE_STATUS.md). Every study source, raw output, expected grade, diagnostic, case card and review remains byte-identical. Original, corrected H08, matched v3, diagnostic and review outputs are separate.

Use `python -I -B reproduce.py --output rebuilt` in a new output folder. The separate `afterfix-gpu-inference-v2.zip` contains frozen inference code and instructions. No new GPU execution is claimed. Historical NF4 checkpoint access remains a public-release consideration.

The PDF uses Garamond headings, Georgia body text and a restrained black-and-white layout, following the author's reference. Fonts are not distributed as separate files. It preserves all manuscript prose and table cells.
