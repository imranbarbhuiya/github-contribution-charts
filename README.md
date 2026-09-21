# GitHub Contribution Charts

Turn the GitHub contribution calendar into a real X/Y line chart or bar chart.

The CLI reads your contribution data through the official GitHub GraphQL API and your existing [`gh`](https://cli.github.com/) authentication. It has no Python runtime dependencies and does not store or transmit a GitHub token.

## Requirements

- Python 3.10+
- GitHub CLI, authenticated with `gh auth login`
- The `read:user` OAuth scope to include private and internal contribution counts:

```sh
gh auth refresh -h github.com -s read:user
```

Private repository names and activity details are not added to the chart. The tool uses only the aggregate daily counts returned by GitHub's contribution calendar API.

## Run from the repository

Without installing, set the source directory on `PYTHONPATH`:

```sh
PYTHONPATH=src python3 -m github_contribution_charts --type line --group day
```

## Install as a CLI

With `pipx`:

```sh
pipx install .
gh-contrib-chart --type line --group day
```

Or with `uv`:

```sh
uv tool install .
gh-contrib-chart --type bar --group month
```

## Examples

Daily line chart:

```sh
gh-contrib-chart --type line --group day --output daily.svg
```

Monthly bar chart with the values exported to CSV:

```sh
gh-contrib-chart \
  --type bar \
  --group month \
  --output monthly.svg \
  --csv monthly.csv
```

Specific date range (maximum one year per request):

```sh
gh-contrib-chart \
  --from 2026-01-01 \
  --to 2026-09-21 \
  --type line \
  --group week
```

Run `gh-contrib-chart --help` for all options.

## What GitHub counts

This visualizes GitHub's contribution-calendar count, not raw commits. Depending on GitHub's contribution rules, the total can include qualifying commits, issues, pull requests, reviews, and repositories created. GitHub calculates contribution dates in UTC.

## Privacy

Generated `.svg`, `.csv`, and API response `.json` files are ignored by Git. Review any generated artifact before sharing it—the chart reveals your contribution totals and activity pattern even though it contains no repository names.

## License

MIT
