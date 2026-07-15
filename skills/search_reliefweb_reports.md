# search_reliefweb_reports

Search ReliefWeb reports — situation updates, assessments, and downloadable documents.

## Parameters

- `country_code`: single ISO alpha-3 (`"PHL"`)
- `country_codes`: list of ISO alpha-3 for regional queries
- `disaster_id`: ReliefWeb disaster ID (from `search_reliefweb_disasters`)
- `disaster_name`: disaster name to filter by (if ID not available)
- `query`: free-text search
- `date_from` / `date_to`: `"YYYY-MM-DD"` (filters by publication date)
- `limit`: default 20

## Returns

```python
{
  "items": [
    {
      "id": 4200000,
      "title": "Bangladesh: Monsoon Floods - Situation Report No. 3",
      "body_snippet": "<p>First 500 chars of HTML body...</p>",
      "date_original": "2024-06-20T00:00:00+00:00",
      "countries": ["Bangladesh"],
      "country_iso3": ["BGD"],
      "disasters": [
        {"id": 12345, "name": "Bangladesh: Floods - Jun 2024", "glide": "FL-2024-000123-BGD"}
      ],
      "source": ["IFRC"],
      "format": ["Situation Report"],
      "language": ["English"],
      "url": "https://reliefweb.int/report/...",
      "files": [
        {
          "filename": "situation-report-3.pdf",
          "mimetype": "application/pdf",
          "url": "https://reliefweb.int/attachments/...",
          "description": "Full situation report"
        }
      ],
      "file_count": 1
    }
  ],
  "total_count": 85,
  "count": 20
}
```

## When to use

- After finding a Montandon event, to get situation reports and documents
- When the user needs downloadable PDFs, assessments, or appeal documents
- To track reporting over time for a disaster (all sitreps across weeks/months)
- When the user asks for more context beyond what Montandon's event record provides

## Notes

- File URLs in the `files` array are direct download links — no scraping needed
- One report may have multiple files (e.g. PDF + Excel appeal summary)
- `body_snippet` is truncated to 500 chars — use the `url` to read the full report
- Date filtering uses the report's publication date, not the disaster date
